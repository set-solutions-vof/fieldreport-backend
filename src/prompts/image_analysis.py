IMAGE_ANALYSIS_PROMPT = """
Analyseer deze inspectiefoto in het Nederlands.

Beschrijf in 1 tot 3 zinnen wat zichtbaar aanwezig is op de foto, zoals schade, vochtsporen,
apparatuur, bouwkundige onderdelen en relevante locatiecontext.

Beschrijf uitsluitend wat zichtbaar is. Verzin geen bevindingen, trek geen conclusies over oorzaken
en neem geen aannames op. Gebruik een professionele en bondige toon.
""".strip()

THERMAL_IMAGE_ANALYSIS_PROMPT = """
Analyseer deze thermische inspectiefoto van een zonnepaneel in het Nederlands.

Beschrijf in 2 tot 4 zinnen de locatie van het hotspot binnen het paneel, het patroon van de
thermische anomalie en een schatting van het relatieve temperatuurverschil ten opzichte van de
omgeving.

Beschrijf uitsluitend wat zichtbaar is in het thermische beeld. Verzin geen oorzaken en neem
geen aannames op. Gebruik een professionele en bondige toon.
""".strip()
