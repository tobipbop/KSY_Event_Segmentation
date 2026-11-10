# 3.5 Event segmentation in video

Tereza Navrátilová, Tobias Lemeer

Tento projekt se zabývá segmentací událostí ve videu (Event Segmentation) a zkoumá, jak lidští pozorovatelé přirozeně dělí spojitý vizuální děj na menší, smysluplné celky.

**Hypotézy:**

1. U videí s pomalým tempem očekáváme menší rozptyl segmentačních hranic mezi respondenty.   
2. Předpokládáme, že AI se při segmentaci videí zaměřuje primárně na fyzické pohyby v obraze, zatímco lidští respondenti vycházejí více z kontextu a logické návaznosti scény. 

**Co budeme měřit?**

- Timestamps respondentů u jednotlivých videí
- Textový popis (pojmenování) vyznačených segmentů u některých videí.

**Co použijeme za videa? Jak dlouhá budou?**
 
- Strukturovaná videa: Například příprava kávy nebo čaje. Video kde je evidentní kdy nějaký segment začíná a končí.   
- Méně strukturovaná videa: Například video teamového sportu nebo sešlost v klubu, kde není zcela jednoznačné, kdy začíná a kdy končí určitý segment.

**Jaké budou úvodní instrukce pro člověka a jaký bude prompt pro AI?**

* Člověk:   
  “Budete sledovat sérii krátkých videí. Ve dvou různých fázích experimentu budete mít za úkol rozdělit souvislý děj na konkrétní události (pomocí časových značek) a následně tyto segmenty také pojmenovat.

  **1. část**
  
  Vaším prvním úkolem je segmentovat video (rozdělit souvislý děj) do menších smysluplných akcí. Zaznamenejte čas vždy ve chvíli, kdy jedna akce skončí a začne další.
  
  Příklad: Vaření
  Děj rozdělujeme na jednotlivé akce:
    - Oddělání poklice
    - Zamíchání jídla
    - Vypnutí budíku
    - Ochutnání jídla
    - Zamíchání jídla
    - Vypnutí sporáku
    - Přemístění pánve

  ➔ Značku vložíte vždy přesně na přechodu mezi těmito fázemi.

  **2. část**
  
  Nyní je Váš úkol rozšířen o pojmenování Vámi zaznamenaných úseků ve videu.
  Kromě přesného rozdělení děje pomocí časových značek musíte jednotlivé úseky také stručně pojmenovat.
  Ve chvíli kdy stisknete záznam času (Enter), aplikace vytvoří pro tento úsek textové pole pro název segmentu.
  Do něj stručně zapište, jaký děj segment reprezentuje (např. "Nalévá vodu").
  "  
* AI:
  “
  **1. část**
  
  Watch the provided video. Your task is to divide the video into specific events. Identify the exact moments where one meaningful unit of activity ends and another begins. Output only a comma-separated list of timestamps in seconds (e.g., 12.5, 34.0, 89.2). Do not provide any descriptions or additional text.

  **2. část**
  Watch the provided video. Your task is to divide the video into specific events and name those events. Identify the exact moments where one meaningful unit of activity ends and another begins. Output only a comma-separated list of timestamps in seconds and a string next to each timestamp containing a brief description of the segment (e. g. "Pouring water").
  ”

**Na jakou věkovou skupinu / kategorii se zaměříme.**  
Zaměříme se na studenty. 

**V jakém prostředí budeme experiment s lidmi provádět**  
Libovolné prostředí s přístupem k počítači. 

**Jak přesně bude test vypadat:**  
Webová aplikace s těmito částmi:
* Identifikace: Účastník si zvolí unikátní přezdívku pro zachování anonymity.
* Tutoriál: Před samotným měřením projde uživatel interaktivním průvodcem a ukázkovým videem, kde si vyzkouší mechaniku segmentace (stisk mezerníku při změně děje) a pochopí princip rozdělování.
* Měření: Účastník projde sérií testovacích videí. Aplikace poskytuje okamžitou vizuální odezvu při záznamu času a umožňuje případné smazání omylem vytvořených značek.
* Export dat: Na závěr aplikace vygeneruje souhrnný report (časové značky a popisky), který lze automaticky stáhnout jako CSV/JSON, případně je odeslán do sdílené databáze.

![][image1]  


[image1]: <data:image/png;base64,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>
