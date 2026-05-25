from src.models.templates.configuration import TemplateSection


def build_report_generation_prompt(
    template_sections: list[TemplateSection],
    combined_transcription: str,
    image_analysis_texts: list[str],
    extra_context: str = "",
) -> str:
    sections_text = "\n".join(
        f"- id: {section.id}, label: {section.label}" for section in template_sections
    )
    image_text = "\n".join(
        f"{image_index}. {analysis_text}"
        for image_index, analysis_text in enumerate(image_analysis_texts, start=1)
    )
    context_text = f"\nExtra context:\n{extra_context}\n" if extra_context else ""

    return f"""
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
      "ai_draft": "<Nederlandse concepttekst voor deze sectie>",
      "confidence_level": "high" | "medium" | "low",
      "confidence_score": 0.0
    }}
  ]
}}

Regels:
- Gebruik alleen informatie die aanwezig is in de transcriptie en fotoanalyses.
- Verzin geen bevindingen, oorzaken, metingen, datums, namen of conclusies.
- Als een sectie geen relevante broninformatie heeft, zet ai_draft op "" en
  confidence_level op "low".
- Aanbevelingen mogen alleen worden opgenomen als de inspecteur ze expliciet in de
  transcriptie noemt.
- Genereer voor elke template sectie precies een object met dezelfde id.
- Alle tekst in ai_draft moet Nederlands zijn.
""".strip()
