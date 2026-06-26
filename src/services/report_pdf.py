import asyncio
from io import BytesIO

import aiohttp
import sqlalchemy as sa
from docx.shared import Cm
from PIL import Image
from docxtpl import DocxTemplate, InlineImage

from src.config import settings
from src.db.connection import get_database
from src.db.schema.tables import (
    company,
    image_analyses,
    inspections,
    report_sections,
    reports,
    templates,
)
from src.storage.blob import download_file, file_exists, upload_file

_PANEL_FIELDS = [
    "paneelnummer",
    "string",
    "type_paneel",
    "orientatie",
    "hellingshoek",
    "positie_op_dak",
    "gem_paneeltemp",
    "max_temperatuur",
    "min_temperatuur",
    "temperatuurverschil",
    "bevindingen",
    "conclusie",
    "advies",
]

_METADATA_FIELDS = [
    "projectnummer",
    "opdrachtgever",
    "locatie",
    "datum_inspectie",
    "tijdstip_inspectie",
    "inspecteur",
    "weersomstandigheden",
    "buitentemperatuur",
    "windsnelheid",
    "instraling",
    "drone_camera",
]

_PREVIEW_PHOTO_SLOTS = (
    ("normaal_foto", "Normaal foto", (220, 220, 220)),
    ("thermisch_foto", "Thermisch foto", (255, 210, 170)),
    ("locatie_foto", "Locatie foto", (200, 220, 245)),
)
_PREVIEW_PHOTO_SIZE = (800, 600)
_PREVIEW_PHOTO_WIDTH = Cm(8)


async def render_template_preview_to_pdf(company_id: str) -> bytes:
    stmt = (
        sa.select(templates.c.docx_storage_key)
        .select_from(company.join(templates, templates.c.id == company.c.current_template_id))
        .where(company.c.id == company_id)
    )
    async with get_database().acquire() as conn:
        row = (await conn.execute(stmt)).mappings().first()

    if row is None or not row["docx_storage_key"]:
        raise ValueError("Template preview not found")

    docx_key = row["docx_storage_key"]
    preview_key = f"{docx_key}.preview.pdf"

    if await file_exists("templates", preview_key):
        cached, _ = await download_file("templates", preview_key)
        return cached

    docx_bytes, _ = await download_file("templates", docx_key)
    tpl = DocxTemplate(BytesIO(docx_bytes))
    tpl.render({"panels": [_build_preview_panel(tpl)]})
    pdf_bytes = await _docx_template_to_pdf(tpl)
    await upload_file("templates", preview_key, pdf_bytes, "application/pdf")
    return pdf_bytes


def _build_preview_panel(tpl: DocxTemplate) -> dict:
    panel = {
        **{field: f"[{field}]" for field in _METADATA_FIELDS},
        **{field: f"[{field}]" for field in _PANEL_FIELDS},
    }

    for field, label, color in _PREVIEW_PHOTO_SLOTS:
        panel[field] = InlineImage(
            tpl,
            _preview_photo_placeholder(label, color),
            width=_PREVIEW_PHOTO_WIDTH,
        )

    return panel


def _preview_photo_placeholder(label: str, color: tuple[int, int, int]) -> BytesIO:
    from PIL import ImageDraw, ImageFont

    image = Image.new("RGB", _PREVIEW_PHOTO_SIZE, color=color)
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    text_bbox = draw.textbbox((0, 0), label, font=font)
    text_position = (
        (_PREVIEW_PHOTO_SIZE[0] - text_bbox[2]) // 2,
        (_PREVIEW_PHOTO_SIZE[1] - text_bbox[3]) // 2,
    )
    draw.text(text_position, label, fill=(80, 80, 80), font=font)

    output = BytesIO()
    image.save(output, format="JPEG")
    output.seek(0)
    return output



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
            panel_data[(1, sid[len("panel_") :])] = _content(row)

    panel_count = max((n for (n, _) in panel_data), default=0)

    stmt = (
        sa.select(image_analyses.c.storage_key)
        .select_from(
            image_analyses.join(
                inspections, inspections.c.id == image_analyses.c.inspection_id
            ).join(reports, reports.c.inspection_id == inspections.c.id)
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

        normaal_idx = (n - 1) * 3
        thermisch_idx = normaal_idx + 1
        locatie_idx = normaal_idx + 2

        normaal_io = photo_bytes[normaal_idx] if normaal_idx < len(photo_bytes) else None
        thermisch_io = photo_bytes[thermisch_idx] if thermisch_idx < len(photo_bytes) else None
        locatie_io = photo_bytes[locatie_idx] if locatie_idx < len(photo_bytes) else None

        panel["normaal_foto"] = InlineImage(tpl, normaal_io, width=Cm(8)) if normaal_io else ""
        panel["thermisch_foto"] = (
            InlineImage(tpl, thermisch_io, width=Cm(8)) if thermisch_io else ""
        )
        panel["locatie_foto"] = InlineImage(tpl, locatie_io, width=Cm(8)) if locatie_io else ""

        panels.append(panel)

    tpl.render({"panels": panels})
    return await _docx_template_to_pdf(tpl)


async def _docx_template_to_pdf(tpl: DocxTemplate) -> bytes:
    buf = BytesIO()
    tpl.save(buf)

    form = aiohttp.FormData()
    form.add_field("files", buf.getvalue(), filename="report.docx", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

    async with aiohttp.ClientSession() as session:
        async with session.post(f"http://{settings.gotenberg_host}:3000/forms/libreoffice/convert", data=form) as resp:
            resp.raise_for_status()
            return await resp.read()


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
