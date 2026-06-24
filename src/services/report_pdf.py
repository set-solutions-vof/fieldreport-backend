import asyncio
import os
import shutil
import subprocess
import tempfile
import uuid
from io import BytesIO

import sqlalchemy as sa
from docx.shared import Cm
from PIL import Image
from docxtpl import DocxTemplate, InlineImage

from src.db.connection import get_database
from src.db.schema.tables import (
    company,
    image_analyses,
    inspections,
    report_sections,
    reports,
    templates,
)
from src.storage.blob import download_file

_PANEL_FIELDS = [
    "paneelnummer", "string", "type_paneel", "orientatie", "hellingshoek",
    "positie_op_dak", "gem_paneeltemp", "max_temperatuur", "min_temperatuur",
    "temperatuurverschil", "bevindingen", "conclusie", "advies",
]

_METADATA_FIELDS = [
    "projectnummer", "opdrachtgever", "locatie", "datum_inspectie",
    "tijdstip_inspectie", "inspecteur", "weersomstandigheden",
    "buitentemperatuur", "windsnelheid", "instraling", "drone_camera",
]


async def render_report_to_pdf(report_id: str, company_id: str) -> bytes:
    stmt = (
        sa.select(templates.c.docx_storage_key)
        .select_from(company.join(templates, templates.c.id == company.c.current_template_id))
        .where(company.c.id == company_id)
    )
    async with get_database().acquire() as conn:
        row = (await conn.execute(stmt)).mappings().one()
    docx_key = row["docx_storage_key"]

    docx_bytes, _ = await download_file("templates", docx_key)

    stmt = (
        sa.select(inspections.c["metadata"])
        .select_from(reports.join(inspections, inspections.c.id == reports.c.inspection_id))
        .where(reports.c.id == report_id, reports.c.company_id == company_id)
    )
    async with get_database().acquire() as conn:
        row = (await conn.execute(stmt)).mappings().one()
    metadata = row["metadata"] or {}

    stmt = (
        sa.select(
            report_sections.c.section_id,
            report_sections.c.reviewed_content,
            report_sections.c.generated_content,
        )
        .where(
            report_sections.c.report_id == report_id,
            report_sections.c.company_id == company_id,
        )
        .order_by(report_sections.c.section_order.asc())
    )
    async with get_database().acquire() as conn:
        section_rows = (await conn.execute(stmt)).mappings().all()

    panel_data: dict[tuple[int, str], str] = {}
    for row in section_rows:
        sid = row["section_id"]
        if sid.startswith("panel_"):
            panel_data[(1, sid[len("panel_"):])] = _content(row)

    panel_count = max((n for (n, _) in panel_data), default=0)

    stmt = (
        sa.select(image_analyses.c.storage_key)
        .select_from(
            image_analyses.join(inspections, inspections.c.id == image_analyses.c.inspection_id)
            .join(reports, reports.c.inspection_id == inspections.c.id)
        )
        .where(reports.c.id == report_id, reports.c.company_id == company_id)
        .order_by(image_analyses.c.created_at.asc())
    )
    async with get_database().acquire() as conn:
        photo_rows = (await conn.execute(stmt)).mappings().all()

    photo_keys = [r["storage_key"] for r in photo_rows if r["storage_key"]]
    photo_bytes: list[BytesIO | None] = list(
        await asyncio.gather(*[_fetch_image_bytes(k) for k in photo_keys])
    )

    tpl = DocxTemplate(BytesIO(docx_bytes))

    panels = []
    for n in range(1, panel_count + 1):
        panel = {field: metadata.get(field, "") for field in _METADATA_FIELDS}

        for field in _PANEL_FIELDS:
            panel[field] = panel_data.get((n, field), "")

        normaal_idx = (n - 1) * 2
        thermisch_idx = normaal_idx + 1

        normaal_io = photo_bytes[normaal_idx] if normaal_idx < len(photo_bytes) else None
        thermisch_io = photo_bytes[thermisch_idx] if thermisch_idx < len(photo_bytes) else None

        panel["normaal_foto"] = InlineImage(tpl, normaal_io, width=Cm(8)) if normaal_io else ""
        panel["thermisch_foto"] = InlineImage(tpl, thermisch_io, width=Cm(8)) if thermisch_io else ""

        panels.append(panel)

    tpl.render({"panels": panels})

    tmp_dir = tempfile.mkdtemp()
    try:
        docx_path = os.path.join(tmp_dir, "report.docx")
        tpl.save(docx_path)

        lo_profile = os.path.join(tmp_dir, f"lo_profile_{uuid.uuid4().hex}")
        result = subprocess.run(
            [
                "soffice",
                "--headless",
                f"-env:UserInstallation=file://{lo_profile}",
                "--convert-to", "pdf",
                "--outdir", tmp_dir,
                docx_path,
            ],
            capture_output=True,
            timeout=60,
        )

        if result.returncode != 0:
            raise RuntimeError(f"LibreOffice conversion failed: {result.stderr.decode()}")

        pdf_path = docx_path.replace(".docx", ".pdf")
        with open(pdf_path, "rb") as f:
            return f.read()
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _content(row) -> str:
    rc = row["reviewed_content"]
    gc = row["generated_content"]
    if rc and len(rc) > 0 and rc[0]:
        return rc[0]
    if gc and len(gc) > 0:
        return gc[0]
    return ""


async def _fetch_image_bytes(key: str) -> BytesIO | None:
    try:
        data, _ = await download_file("inspections", key)
        img = Image.open(BytesIO(data)).convert("RGB")
        out = BytesIO()
        img.save(out, format="JPEG")
        out.seek(0)
        return out
    except Exception:
        return None
