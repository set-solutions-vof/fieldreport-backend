from src.prompts.report_generation import REPORT_GENERATION_PROMPT


def test_report_generation_prompt_contains_template_sources_and_rules() -> None:
    sections_text = "- id: conclusie, label: Conclusie"
    image_text = "1. Vochtplek zichtbaar op de wand."
    context_text = "\nExtra context:\nType onderzoek: Lekdetectie\n"

    prompt = REPORT_GENERATION_PROMPT.format(
        sections_text=sections_text,
        combined_transcription="Inspecteur noemt vocht bij de waterleiding.",
        image_text=image_text,
        context_text=context_text,
    )

    assert sections_text in prompt
    assert "Inspecteur noemt vocht bij de waterleiding." in prompt
    assert image_text in prompt
    assert "Type onderzoek: Lekdetectie" in prompt
    assert '"sections"' in prompt
    assert "Aanbevelingen mogen alleen" in prompt
