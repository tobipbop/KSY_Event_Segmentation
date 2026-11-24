import unicodedata
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.signal import find_peaks

# ---------------------------------------------------------------------------
# 1. Konfigurace a mapování názvů videí
# ---------------------------------------------------------------------------
DATA_PATH = Path("KSY_data.xlsx")
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

VIDEO_NAMES = {
    1: "Uvaření obědu",
    2: "Objednávka v kavárně",
    3: "Fotbal",
    4: "Drinky v baru",
    5: "Trouba",
    6: "Objednávka v čajovně",
    7: "Intimní konverzace",
}

plt.rcParams["figure.dpi"] = 150
sns.set_theme(style="whitegrid", context="notebook")


def strip_accents(text: str) -> str:
    """Převede český text na malá písmena bez diakritiky pro klasifikaci klíčových slov."""
    return "".join(
        c for c in unicodedata.normalize("NFD", str(text))
        if unicodedata.category(c) != "Mn"
    ).lower().strip()


def load_and_clean_data(filepath: Path) -> pd.DataFrame:
    """Načte KSY_data.xlsx (bez hlavičky), očistí časy a přiřadí názvy videí."""
    df = pd.read_excel(filepath, sheet_name="List 1", header=None)
    df.columns = [
        "log_time",
        "participant",
        "video_task",
        "event_type",
        "timestamp_sec",
        "timestamp_fmt",
        "label",
        "unused_col",
        "notes",
    ]

    # Převod časových značek na čísla a odstranění neplatných řádků (např. '-')
    df["ts_num"] = pd.to_numeric(df["timestamp_sec"], errors="coerce")
    clean_df = df[df["ts_num"].notna()].copy()
    clean_df["video_num"] = (
        clean_df["video_task"].str.extract(r"Video (\d+)").astype(int)
    )
    clean_df["video_name"] = clean_df["video_num"].map(VIDEO_NAMES)
    return clean_df


# ---------------------------------------------------------------------------
# 2. Hypotéza 1: Shlukování časových značek a individuální počty zastavení
# ---------------------------------------------------------------------------
def compute_kde_and_peaks(clean_df: pd.DataFrame, sigma: float = 1.0):
    """
    Vypočítá jádrový odhad hustoty (KDE se šířkou pásma sigma v sekundách)
    a detekuje konsenzuální vrcholy segmentace pro každé video.
    """
    kde_results = {}
    summary_rows = []
    participants = clean_df["participant"].unique()

    for v in range(1, 8):
        sub = clean_df[clean_df["video_num"] == v]
        ts = sub["ts_num"].values
        n_participants = sub["participant"].nunique()
        max_t = ts.max()

        grid = np.linspace(0, max_t + 2, 1000)
        density = (
            np.sum(np.exp(-0.5 * ((grid[:, None] - ts[None, :]) / sigma) ** 2), axis=1)
            / n_participants
        )

        # Detekce konsenzuálních vrcholů (min. hustota 25 %, rozestup >= 2.0 s)
        min_dist_idx = int(2.0 / (grid[1] - grid[0]))
        peaks, _ = find_peaks(density, height=0.25, distance=min_dist_idx)
        peak_times = grid[peaks]
        peak_heights = density[peaks]

        kde_results[v] = (grid, density, peak_times, peak_heights, ts)
        summary_rows.append({
            "Video": VIDEO_NAMES[v],
            "Úloha": "Značkování" if v <= 4 else "Značkování + pojmenování",
            "Celkem zastavení": len(ts),
            "Průměr zastavení / osoba": round(len(ts) / len(participants), 2),
            "Konsenzuální vrcholy": len(peak_times),
        })

    return kde_results, pd.DataFrame(summary_rows)


def plot_timestamp_clustering(kde_results: dict, summary_df: pd.DataFrame):
    """Vykreslí křivky hustoty shody, konsenzuální vrcholy a jednotlivé kliky respondentů."""
    fig, axes = plt.subplots(7, 1, figsize=(13, 15.5))
    palette = sns.color_palette("viridis", 7)
    rng = np.random.RandomState(42)

    for idx, v in enumerate(range(1, 8)):
        ax = axes[idx]
        grid, density, peak_times, peak_heights, ts = kde_results[v]

        ax.plot(grid, density * 100, color=palette[idx], lw=2.2)
        ax.fill_between(grid, 0, density * 100, color=palette[idx], alpha=0.22)

        # Jednotlivé kliky respondentů pod osou x
        y_jitter = rng.uniform(-12, -2, size=len(ts))
        ax.scatter(ts, y_jitter, color="#2c3e50", alpha=0.45, s=14, marker="|", linewidths=1.5)

        for pt, ph in zip(peak_times, peak_heights):
            ax.axvline(pt, color="#d62728", linestyle="--", alpha=0.5, lw=1)
            ax.plot(pt, ph * 100, "o", color="#d62728", markersize=5)
            ax.annotate(
                f"{pt:.1f}s",
                (pt, ph * 100),
                textcoords="offset points",
                xytext=(0, 5),
                ha="center",
                fontsize=8,
                fontweight="bold",
                color="#b01e1e",
            )

        row = summary_df.iloc[idx]
        ax.set_title(
            f"{row['Video']} ({row['Úloha']}) — n={row['Celkem zastavení']} zastavení | "
            f"{row['Konsenzuální vrcholy']} konsenzuálních vrcholů",
            fontsize=10.5,
            fontweight="bold",
            loc="left",
            pad=4,
        )
        ax.set_ylabel("Hustota (%)", fontsize=9)
        ax.set_ylim(-15, max(115, np.max(density * 100) + 18))
        ax.set_xlim(0, max(ts) + 2)
        ax.axhline(0, color="gray", lw=0.8)

    axes[-1].set_xlabel("Čas ve videu (sekundy)", fontsize=11, fontweight="bold")
    fig.suptitle(
        "Shlukování segmentačních hranic napříč videi (Hypotéza 1)",
        fontsize=14,
        fontweight="bold",
        y=0.995,
    )
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "chart1_timestamp_clustering.png", bbox_inches="tight")
    plt.close()


def plot_individual_stops(clean_df: pd.DataFrame):
    """Vykreslí rozdělení počtu zastavení na respondenta pro všechna videa."""
    participants = clean_df["participant"].unique()
    all_grid = pd.MultiIndex.from_product(
        [range(1, 8), participants], names=["video_num", "participant"]
    ).to_frame(index=False)

    p_counts = all_grid.merge(
        clean_df.groupby(["video_num", "participant"]).size().reset_index(name="stops"),
        on=["video_num", "participant"],
        how="left",
    ).fillna({"stops": 0})

    fig, ax = plt.subplots(figsize=(10.5, 5.5))
    sns.boxplot(
        data=p_counts,
        x="video_num",
        y="stops",
        ax=ax,
        palette="Set2",
        width=0.48,
        fliersize=0,
    )
    sns.stripplot(
        data=p_counts,
        x="video_num",
        y="stops",
        ax=ax,
        color="#1f2937",
        size=6.5,
        jitter=0.16,
        alpha=0.75,
    )

    ax.set_title("Počet zastavení na respondenta podle videa", fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("Video (1–4: Pouze značkování | 5–7: Značkování + pojmenování)", fontsize=10.5)
    ax.set_ylabel("Počet zastavení na osobu", fontsize=10.5)
    ax.set_xticks(range(7))
    ax.set_xticklabels([VIDEO_NAMES[i] for i in range(1, 8)], rotation=18, ha="right", fontsize=9.5)

    means = p_counts.groupby("video_num")["stops"].mean()
    for i, m in enumerate(means):
        max_y = p_counts[p_counts["video_num"] == i + 1]["stops"].max()
        ax.text(i, max_y + 0.9, f"μ = {m:.1f}", ha="center", fontsize=9.5, fontweight="bold", color="#111827")

    ax.set_ylim(-1, 30.5)
    sns.despine(left=True)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "chart2_individual_stops.png", bbox_inches="tight")
    plt.close()


# ---------------------------------------------------------------------------
# 3. Hypotéza 2: Fyzický pohyb vs. kontextuální / komunikační popisky
# ---------------------------------------------------------------------------
CONTEXT_KEYWORDS = [
    "mluv", "hovor", "konverzac", "odmit", "zamit", "nesouhlas", "odpor", "vysvetl",
    "odpovid", "povid", "komunik", "reag", "utne", "popich", "naznac", "signaliz",
    "zakaznik", "servir", "vymen", "prehoz", "donastav", "pokrac", "dalsi", "kontext",
    "rozlouc", "pozdrav", "souhlas", "otazk", "zept", "diskus", "debat", "hadk", "styk",
    "konec", "zacatek", "priprav", "hotov",
]


def classify_label(text: str) -> str:
    clean = strip_accents(text)
    for kw in CONTEXT_KEYWORDS:
        if kw in clean:
            return "Kontextuální / komunikační / cíl"
    return "Fyzický / motorický pohyb"


def plot_semantic_analysis(clean_df: pd.DataFrame):
    """Porovná podíl fyzických a kontextuálních popisků (videa 5–7) a vykreslí časovou osu videa 7."""
    naming_df = clean_df[clean_df["event_type"] == "naming"].copy()
    naming_df["category"] = naming_df["label"].apply(classify_label)

    cat_summary = naming_df.groupby(["video_num", "category"]).size().unstack(fill_value=0)
    cat_summary["Celkem"] = cat_summary.sum(axis=1)
    cat_summary["Fyzický %"] = cat_summary["Fyzický / motorický pohyb"] / cat_summary["Celkem"] * 100
    cat_summary["Kontextuální %"] = cat_summary["Kontextuální / komunikační / cíl"] / cat_summary["Celkem"] * 100
    cat_summary.index = [VIDEO_NAMES[v] for v in cat_summary.index]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.5, 5.5), gridspec_kw={"width_ratios": [1, 1.5]})

    # Levý panel: Skládaný sloupcový graf
    pct_df = cat_summary[["Fyzický %", "Kontextuální %"]]
    pct_df.plot(
        kind="bar",
        stacked=True,
        ax=ax1,
        color=["#3b82f6", "#ef4444"],
        edgecolor="black",
        width=0.55,
    )
    ax1.set_title("Fyzické vs. kontextuální popisky\n(Úloha: Značkování + pojmenování)", fontsize=11.5, fontweight="bold")
    ax1.set_xlabel("")
    ax1.set_ylabel("Podíl popisků (%)", fontsize=10)
    ax1.set_xticklabels(
        [f"{name}\n(n={cat_summary.loc[name, 'Celkem']})" for name in cat_summary.index],
        rotation=12,
    )
    ax1.legend(["Fyzický / motorický pohyb", "Kontextuální / komunikační / cíl"], loc="lower right", fontsize=8.5)

    for idx, name in enumerate(cat_summary.index):
        phys = pct_df.loc[name, "Fyzický %"]
        ctx = pct_df.loc[name, "Kontextuální %"]
        ax1.text(idx, phys / 2, f"{phys:.1f}%", ha="center", va="center", color="white", fontweight="bold", fontsize=10)
        if ctx > 5:
            ax1.text(idx, phys + ctx / 2, f"{ctx:.1f}%", ha="center", va="center", color="white", fontweight="bold", fontsize=10)

    # Pravý panel: Časová osa pro Intimní konverzaci (Video 7)
    v7_df = naming_df[naming_df["video_num"] == 7].copy()
    v7_df["y_pos"] = v7_df["participant"].astype("category").cat.codes

    for cat, color, marker in [
        ("Fyzický / motorický pohyb", "#3b82f6", "o"),
        ("Kontextuální / komunikační / cíl", "#ef4444", "D"),
    ]:
        sub_c = v7_df[v7_df["category"] == cat]
        ax2.scatter(
            sub_c["ts_num"],
            sub_c["y_pos"],
            c=color,
            label=cat,
            s=48,
            marker=marker,
            alpha=0.88,
            edgecolors="black",
            linewidths=0.5,
        )

    ax2.set_yticks(range(v7_df["participant"].nunique()))
    ax2.set_yticklabels(v7_df["participant"].astype("category").cat.categories, fontsize=8.5)
    ax2.set_xlabel("Čas ve videu: Intimní konverzace (sekundy)", fontsize=10)
    ax2.set_title("Intimní konverzace: Fyzická gesta vs. sociální/kontextuální interpretace", fontsize=11.5, fontweight="bold")
    ax2.legend(loc="upper center", bbox_to_anchor=(0.5, 1.01), ncol=2, fontsize=8.5, frameon=True)

    annotations = [
        (4.5, "Sahání na vlasy\n(fyzické)"),
        (11.5, "Pití ze sklenice\n(fyzické)"),
        (18.0, "Konverzace / odmítnutí\n(kontextuální)"),
        (28.5, "Dotek ramene / odpor\n(fyzické + sociální)"),
    ]
    for t_ann, label_ann in annotations:
        ax2.axvline(t_ann, color="gray", linestyle=":", alpha=0.6)
        ax2.text(t_ann, v7_df["y_pos"].max() + 0.55, label_ann, fontsize=7.5, ha="center", color="#374151", fontweight="bold")

    ax2.set_ylim(-0.8, v7_df["y_pos"].max() + 3.2)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "chart3_hypothesis2_semantics.png", bbox_inches="tight")
    plt.close()

    return cat_summary


# ---------------------------------------------------------------------------
# 4. Spuštění analýzy
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    df_clean = load_and_clean_data(DATA_PATH)
    kde_res, summary_table = compute_kde_and_peaks(df_clean, sigma=1.0)

    print("=== Souhrnné metriky podle videa ===")
    print(summary_table.to_string(index=False))

    plot_timestamp_clustering(kde_res, summary_table)
    plot_individual_stops(df_clean)
    semantic_table = plot_semantic_analysis(df_clean)

    print("\n=== Hypotéza 2: Rozdělení popisků ===")
    print(semantic_table.round(1).to_string())
    print(f"\nGrafy uloženy do složky: {OUTPUT_DIR.resolve()}")