DEEPSEEK_TEMPLATE_EXTRACTION_SYSTEM_PROMPT = """
You are extracting a REUSABLE TEMPLATE from example field inspection reports.

Your output must describe the canonical structure for ALL reports of this type, not the
specific content of the provided example(s).

GENERALIZATION — apply strictly:
- Remove all instance-specific details from labels: addresses, client names, project numbers.
  "Conclusie Kruisweg 6" → "Conclusie",
  "Bijlage A - Fotopagina Kruisweg 6" → "Fotopagina"
- Merge all photo annexes (Bijlage A, Bijlage B, etc.) into ONE single photo_grid
  section. Only one photo_grid section is ever allowed.
- Labels must be generic and apply to every future report
- Only extract TOP-LEVEL sections. Sub-headings that appear within a section are NOT
  separate sections. They are part of their parent section's text_block content.
- If a heading could logically be content within the preceding section, it is NOT a separate
  section. Example: "Controle (overig) leidingwerk" belongs inside Conclusie.

RENDER TYPES:

key_value_table
  Use for: administrative project metadata: fields that describe WHO, WHEN, and WHERE.
  fields: list of field label strings as they appear in the document

measurement_table
  Use for: technical inspection activities and findings — what was TESTED and what was FOUND.
  fields: list of row label strings as they appear in the document — MUST NOT be null

text_block
  Use for: free-form paragraphs: conclusions, descriptions, work orders, statements,
  recommendations
  fields: null

photo_grid
  Use for: all photo pages combined into one section — maximum one per template
  fields: null

GROUPS (optional, any section with fields):
- groups: when field labels are organized under sub-headings, each group has id, label, and fields
- omit groups when fields are a single flat list

OUTPUT FORMAT — each section must have:
- id: Dutch snake_case derived from the label ("Meetresultaten" → "meetresultaten")
- label: generic Dutch label, no addresses or instance-specific details
- order: zero-based section order
- render_type: one of the four types above
- fields: as defined per render type
- found_in: number of input reports where this section was found
- groups: only when sub-headings organize the fields

Return valid JSON only with a top-level "sections" array.

Example:
{
  "sections": [
    {
      "id": "projectgegevens",
      "label": "Projectgegevens",
      "order": 0,
      "render_type": "key_value_table",
      "fields": ["DATUM RAPPORTAGE", "NAAM ONDERZOEKER", "PROJECTNUMMER", "TYPE ONDERZOEK"],
      "found_in": 3
    },
    {
      "id": "werkomschrijving_opdracht",
      "label": "Werkomschrijving/opdracht",
      "order": 1,
      "render_type": "text_block",
      "fields": null,
      "found_in": 3
    },
    {
      "id": "meetresultaten",
      "label": "Meetresultaten",
      "order": 2,
      "render_type": "measurement_table",
      "fields": [
        "Visuele inspectie",
        "Thermografie",
        "Vochtmetingen",
        "Druktest",
        "Leidinglokalisatie",
        "Traceergas"
      ],
      "found_in": 3,
      "groups": [
        {
          "id": "algemene_inspectie_schadebeeld_leidingwerk",
          "label": "Algemene inspectie schadebeeld/ leidingwerk",
          "fields": ["Visuele inspectie", "Thermografie", "Vochtmetingen"]
        },
        {
          "id": "waterleidingen",
          "label": "Waterleidingen",
          "fields": ["Druktest", "Leidinglokalisatie", "Traceergas"]
        }
      ]
    },
    {
      "id": "fotopagina",
      "label": "Fotopagina",
      "order": 3,
      "render_type": "photo_grid",
      "fields": null,
      "found_in": 3
    }
  ]
}
""".strip()

DEEPSEEK_TEMPLATE_EXTRACTION_PROMPT = """
Below are field inspection report examples from the same company. Each includes extracted
text and a visual analysis summary produced by a vision model.

Your task: identify the canonical template structure: the sections that consistently appear
across these examples. Where examples differ, prefer the common pattern.

For each section:
- id: Dutch snake_case derived from the label
- label: generic Dutch label (no addresses or instance-specific details)
- order: zero-based section order
- render_type: one of text_block, key_value_table, measurement_table, photo_grid
- fields: actual field names or column headers from the documents, or null
- found_in: number of input reports where this section was found
- groups: sub-headings that organize fields, with id, label, and fields — omit when not needed

Documents:
{documents_json}
""".strip()
