from src.models.templates.domain import TemplateSection
from src.prompts.report_generation import build_report_generation_prompt


def test_build_report_generation_prompt_contains_template_sources_and_rules() -> None:
    prompt = build_report_generation_prompt(
        [
            TemplateSection(
                id="conclusie",
                label="Conclusie",
                order=1,
                render_type="text_block",
            )
        ],
        "Inspecteur noemt vocht bij de waterleiding.",
        ["Vochtplek zichtbaar op de wand."],
        "Type onderzoek: Lekdetectie",
    )

    assert "id: conclusie, label: Conclusie" in prompt
    assert "Inspecteur noemt vocht bij de waterleiding." in prompt
    assert "1. Vochtplek zichtbaar op de wand." in prompt
    assert "Type onderzoek: Lekdetectie" in prompt
    assert '"sections"' in prompt
    assert "Aanbevelingen mogen alleen" in prompt
