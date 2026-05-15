DEEPSEEK_TEMPLATE_EXTRACTION_SYSTEM_PROMPT = """
Return valid json only.

Example json output:
{
  "sections": [
    {
      "id": "project_details",
      "label": "Projectgegevens",
      "render_type": "key_value_table",
      "fields": ["DATUM RAPPORTAGE", "NAAM ONDERZOEKER"]
    },
    {
      "id": "conclusion",
      "label": "Conclusie",
      "render_type": "text_block"
    }
  ]
}
""".strip()

DEEPSEEK_TEMPLATE_EXTRACTION_PROMPT = """
You analyze field report template documents.
Return a json object with a top-level "sections" array.
Each section must include "id", "label", "render_type", and optional "fields".
Allowed render_type values are "text_block", "key_value_table", "measurement_table", and "photo_grid".
Use snake_case ids.
Infer the canonical report sections from the combined text and visual analysis.

Documents:
{documents_json}
""".strip()
