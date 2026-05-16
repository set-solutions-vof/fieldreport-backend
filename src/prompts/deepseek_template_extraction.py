DEEPSEEK_TEMPLATE_EXTRACTION_SYSTEM_PROMPT = """
You are extracting a REUSABLE TEMPLATE from example field inspection reports.

Your output must describe the canonical structure for ALL reports of this type — not the specific content of the provided example(s).

GENERALIZATION — apply strictly:
- Remove all instance-specific details from labels: addresses, client names, project numbers. "Conclusie Kruisweg 6" → "Conclusie", "Bijlage A - Fotopagina Kruisweg 6" → "Fotopagina"
- Merge all photo annexes (Bijlage A, Bijlage B, etc.) into ONE single photo_grid section. Only one photo_grid section is ever allowed.
- Labels must be generic and apply to every future report
- Only extract TOP-LEVEL sections. Sub-headings that appear within a section (e.g. bold sub-titles inside a Conclusie block like "Lekkage warmwaterleiding" or "Controle (overig) leidingwerk") are NOT separate sections — they are part of their parent section's text_block content.
- For measurement_table fields: only include actual measurement and inspection method names (e.g. "Druktest", "Thermografie", "Rioolinspectie"). Exclude category/group headers that organize rows — these can be identified by a trailing colon (":") or by the fact that they contain no measurement data themselves.
- If a heading could logically be content within the preceding section (e.g. a sub-finding within a Conclusie, or a sub-category within Meetresultaten), it is NOT a separate section. Example: "Controle (overig) leidingwerk" belongs inside Conclusie, not as its own section.

RENDER TYPES:

key_value_table
  Use for: administrative project metadata — fields that describe WHO, WHEN, and WHERE about the job.
  These are form fields filled in per inspection: dates, names, addresses, contact details, project numbers.
  fields: list of field label strings as they appear in the document (e.g. ["DATUM RAPPORTAGE", "NAAM ONDERZOEKER"])

measurement_table
  Use for: technical inspection activities and findings — what was TESTED and what was FOUND.
  These are rows describing a method (Druktest, Thermografie, Rioolinspectie) and its result or observation.
  This is NOT a key_value_table even if it visually looks like two columns.
  fields: list of the row label strings as they appear in the document — MUST NOT be null

text_block
  Use for: free-form paragraphs — conclusions, descriptions, work orders, statements, recommendations
  fields: null

photo_grid
  Use for: all photo pages combined into one section — maximum one per template
  fields: null

OUTPUT FORMAT — each section must have:
- id: Dutch snake_case derived from the label ("Meetresultaten" → "meetresultaten")
- label: generic Dutch label, no addresses or instance-specific details
- render_type: one of the four types above
- fields: as defined per render type

Return valid JSON only. The top-level key is "sections".

Example:
{
  "sections": [
    {
      "id": "projectgegevens",
      "label": "Projectgegevens",
      "render_type": "key_value_table",
      "fields": ["DATUM RAPPORTAGE", "NAAM ONDERZOEKER", "PROJECTNUMMER", "TYPE ONDERZOEK"]
    },
    {
      "id": "werkomschrijving_opdracht",
      "label": "Werkomschrijving/opdracht",
      "render_type": "text_block",
      "fields": null
    },
    {
      "id": "meetresultaten",
      "label": "Meetresultaten",
      "render_type": "measurement_table",
      "fields": ["Visuele inspectie", "Thermografie", "Druktest", "Traceergas", "Rioolinspectie"]
    },
    {
      "id": "fotopagina",
      "label": "Fotopagina",
      "render_type": "photo_grid",
      "fields": null
    }
  ]
}
""".strip()

DEEPSEEK_TEMPLATE_EXTRACTION_PROMPT = """
Below are field inspection report examples from the same company. Each includes extracted text and a visual analysis summary produced by a vision model.

Your task: identify the canonical template structure — the sections that consistently appear across these examples. Where examples differ, prefer the common pattern.

For each section:
- id: Dutch snake_case derived from the label
- label: generic Dutch label (no addresses or instance-specific details)
- render_type: one of text_block, key_value_table, measurement_table, photo_grid
- fields: actual field names or column headers from the documents (key_value_table and measurement_table only), or null

Documents:
{documents_json}
""".strip()