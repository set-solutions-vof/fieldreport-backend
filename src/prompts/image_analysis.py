IMAGE_ANALYSIS_PROMPT = """
Analyseer deze inspectiefoto in het Nederlands.

Beschrijf in 1 tot 3 zinnen wat zichtbaar aanwezig is op de foto, zoals schade, vochtsporen,
apparatuur, bouwkundige onderdelen en relevante locatiecontext.

Beschrijf uitsluitend wat zichtbaar is. Verzin geen bevindingen, trek geen conclusies over oorzaken
en neem geen aannames op. Gebruik een professionele en bondige toon.
""".strip()

OVERVIEW_IMAGE_ANALYSIS_PROMPT = """
Analyseer deze overzichtsfoto van een zonnepanelen-installatie op een dak, gemaakt vanuit een drone.

Beschrijf in 2 tot 4 zinnen:
- De indeling van de panelen op het dak (rijen, kolommen, secties, oriëntatie).
- Zichtbare schaduwbronnen zoals verhogingen, obstakels, schoorstenen of aangrenzende gebouwen.
- De algemene conditie van het dak en de montageconstructie voor zover zichtbaar.

Beschrijf uitsluitend wat zichtbaar is. Verzin geen bevindingen. Gebruik een professionele en bondige toon.
""".strip()

VISUAL_PANEL_IMAGE_ANALYSIS_PROMPT = """
Analyseer deze close-up drone-foto van zonnepanelen, gemaakt met de visuele camera van een DJI M4T.

Beschrijf in 2 tot 4 zinnen de zichtbare fysieke toestand van de panelen, specifiek:
- Vervuiling: vogeldroppings, mos, stof, of andere aanslag op het glasoppervlak.
- Fysieke schade: zichtbare glasbreuk, krasschade, beschadigde cellen of frameschade.
- Bekabeling en aansluitingen: loshangende kabels, beschadigde connectoren of mantelschade.
- Schaduwobjecten direct op of boven de panelen.

Beschrijf uitsluitend wat zichtbaar is. Verbind bevindingen niet aan de thermische anomalie —
dat doet het rapportagesysteem. Gebruik een professionele en bondige toon.
""".strip()

THERMAL_IMAGE_ANALYSIS_PROMPT = """
Analyseer dit thermisch beeld van zonnepanelen, opgenomen met een DJI M4T thermische camera
(rainbow2-kleurenschaal: donkerblauw = koud, groen/geel = gemiddeld, oranje/rood/wit = heet).

Beschrijf in 3 tot 5 zinnen:
1. Welke panelen in het beeld afwijken van de omliggende panelen (warmer of kouder).
2. Het patroon van de thermische anomalie, gebruik daarvoor de volgende classificatie:
   - Geïsoleerde cel: één enkele hete cel → duidt op celdefect of microfractuur.
   - Celcluster: meerdere aangrenzende cellen warm → verhoogde serieweerstand.
   - Streepvormig (1/3 of 2/3 van het paneel): bypassdiode actief of defecte string.
   - Volledig paneel warmer dan omgeving: PID, delamination of ernstige beschadiging.
   - Randeffect of hoekpatroon: delamination of vochtindringing.
3. De locatie van de anomalie binnen het paneel (linksboven, midden, rechtsonder, etc.).

De exacte temperatuurwaarden worden automatisch aangeleverd — schat ze niet.
Beschrijf uitsluitend wat zichtbaar is in het thermische beeld. Gebruik een professionele toon.
""".strip()
