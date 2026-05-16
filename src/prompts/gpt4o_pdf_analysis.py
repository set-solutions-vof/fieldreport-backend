GPT4O_PDF_ANALYSIS_PROMPT = """
You are analyzing a field inspection report to extract its template structure.
 
Identify every section in this document. Classify each section into one of these four types:
 
- text_block: free-form paragraphs, conclusions, descriptions, observations
- key_value_table: sections where labeled fields are paired with values (e.g. "Datum: 12-01-2024", "Onderzoeker: Jan de Vries")
- measurement_table: tabular data with multiple rows of numeric or structured measurements (e.g. pressure readings, GPS coordinates, inspection results per location)
- photo_grid: areas that contain or are designed to hold photos
 
For key_value_table sections: list every field label you can read.
For measurement_table sections: list every column header you can read.
For photo sections: list any captions or labels near the photo areas.
 
Return a JSON object with these exact keys:
- "document_type": short description of what kind of inspection report this is
- "visual_summary": 2-3 sentences describing the overall structure and layout of this document
- "likely_sections": list of section names as they appear in the document (in Dutch, as written)
- "table_patterns": list of all field labels and column headers found in key_value and measurement sections
- "photo_expectations": list of captions or labels found near photo areas

For "likely_sections": only list PRIMARY top-level section headings. Do not include sub-headings that appear nested within a section (e.g. bold sub-titles within a Conclusie or Resultaten block).
""".strip()
 