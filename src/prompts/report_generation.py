REPORT_GENERATION_PROMPT = """
Je genereert Nederlandstalige conceptrapportsecties voor een inspectierapport.

Template secties:
{sections_text}

Transcriptie:
{combined_transcription}

Fotoanalyses:
{image_text}
{context_text}
Geef uitsluitend een JSON-object terug met deze structuur:
{{
  "sections": [
    {{
      "id": "<section.id uit het template>",
      "generated_content": "<Nederlandse concepttekst voor deze sectie>",
      "confidence_level": "high" | "medium" | "low",
      "confidence_score": 0.0
    }}
  ]
}}

Regels:
- Gebruik alleen informatie die aanwezig is in de transcriptie en fotoanalyses.
- Verzin geen bevindingen, oorzaken, metingen, datums, namen of conclusies.
- Als een sectie geen relevante broninformatie heeft, zet generated_content op "" en
  confidence_level op "low".
- Aanbevelingen mogen alleen worden opgenomen als de inspecteur ze expliciet in de
  transcriptie noemt.
- Genereer voor elke template sectie precies een object met dezelfde id.
- Alle tekst in generated_content moet Nederlands zijn.
""".strip()
