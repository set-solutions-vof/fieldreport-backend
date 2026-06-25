import tempfile
from pathlib import Path

from loguru import logger

from src.adapters.thermofly.panel_locator import generate_panel_location_image
from src.db.inspection.queries import fetch_inspection_photo_files
from src.db.report.pipeline_repository import ReportPipelineRepository
from src.llm import gpt4o_client
from src.models.reports.pipeline import InspectionMediaFile, ReportPipelineContext
from src.prompts.image_analysis import (
    IMAGE_ANALYSIS_PROMPT,
    OVERVIEW_IMAGE_ANALYSIS_PROMPT,
    THERMAL_IMAGE_ANALYSIS_PROMPT,
    VISUAL_PANEL_IMAGE_ANALYSIS_PROMPT,
)
from src.services.thermal_extraction import extract_thermal_metrics
from src.storage import blob
from src.utils.dji_xmp import extract_dji_xmp

_OVERVIEW_ALTITUDE_M = 30.0


async def analyze_inspection_photo_files(
    report: ReportPipelineContext,
    repository: ReportPipelineRepository,
) -> None:
    photo_files = await fetch_inspection_photo_files(str(report.inspection_id))

    # Download all files once — needed for both the overview lookup and per-photo analysis
    downloaded: dict[str, tuple[bytes, object]] = {}
    for pf in photo_files:
        content = (await blob.download_file("inspections", pf.storage_key))[0]
        dji_meta = extract_dji_xmp(content)
        downloaded[pf.storage_key] = (content, dji_meta)

    overview_bytes, overview_key = _find_overview(downloaded)

    # Sort non-overview files: visual (_V) first, thermal (_T) second, others last.
    # The PDF service expects groups of 3 per panel: [visual, thermal, location].
    def _sort_key(pf: InspectionMediaFile) -> int:
        stem = Path(pf.storage_key).stem.upper()
        if _is_overview_key(pf.storage_key, downloaded):
            return 99  # overview last so we can skip it cleanly
        if stem.endswith("_V"):
            return 0
        if stem.endswith("_T"):
            return 1
        return 2

    sorted_files = sorted(
        [pf for pf in photo_files if pf.storage_key != overview_key],
        key=_sort_key,
    )

    for photo_file in sorted_files:
        photo_key = photo_file.storage_key
        file_content, dji_meta = downloaded[photo_key]
        is_thermal = dji_meta and dji_meta.image_source == "InfraredCamera"

        prompt = THERMAL_IMAGE_ANALYSIS_PROMPT if is_thermal else VISUAL_PANEL_IMAGE_ANALYSIS_PROMPT
        if dji_meta is None:
            prompt = IMAGE_ANALYSIS_PROMPT

        try:
            description = await gpt4o_client.analyze_inspection_photo(
                Path(photo_key).name,
                file_content,
                prompt=prompt,
            )

            thermal_metrics = extract_thermal_metrics(file_content) if is_thermal else None

            await repository.insert_image_analysis(
                str(report.inspection_id),
                str(report.company_id),
                photo_key,
                description,
                dji_metadata=dji_meta.model_dump(mode="json") if dji_meta else None,
                thermal_metrics=thermal_metrics.model_dump() if thermal_metrics else None,
            )
            logger.info("Analyzed photo {}", photo_key)

            # For visual images: generate location annotation and insert it as a
            # third image_analysis record so the PDF picks it up in the locatie slot.
            if not is_thermal and overview_bytes and dji_meta and dji_meta.lrf_target_lat:
                await _insert_location_record(
                    overview_bytes=overview_bytes,
                    panel_bytes=file_content,
                    panel_storage_key=photo_key,
                    inspection_id=str(report.inspection_id),
                    company_id=str(report.company_id),
                    repository=repository,
                )

        except Exception:
            logger.exception("Photo file {} failed", photo_key)
            raise

    # Analyze the overview too so it gets recorded, but AFTER the panel images
    # (it does not go into a panel slot — the PDF skips images beyond locatie_idx).
    if overview_key:
        ov_content, ov_meta = downloaded[overview_key]
        try:
            ov_description = await gpt4o_client.analyze_inspection_photo(
                Path(overview_key).name,
                ov_content,
                prompt=OVERVIEW_IMAGE_ANALYSIS_PROMPT,
            )
            await repository.insert_image_analysis(
                str(report.inspection_id),
                str(report.company_id),
                overview_key,
                ov_description,
                dji_metadata=ov_meta.model_dump(mode="json") if ov_meta else None,
            )
            logger.info("Analyzed overview {}", overview_key)
        except Exception:
            logger.exception("Overview file {} failed", overview_key)
            raise


def _is_overview_key(key: str, downloaded: dict) -> bool:
    _, dji_meta = downloaded.get(key, (None, None))
    return bool(
        dji_meta
        and dji_meta.relative_altitude is not None
        and dji_meta.relative_altitude > _OVERVIEW_ALTITUDE_M
    )


def _find_overview(
    downloaded: dict[str, tuple[bytes, object]],
) -> tuple[bytes | None, str | None]:
    for key, (content, dji_meta) in downloaded.items():
        if (
            dji_meta
            and dji_meta.relative_altitude is not None
            and dji_meta.relative_altitude > _OVERVIEW_ALTITUDE_M
        ):
            return content, key
    return None, None


async def _insert_location_record(
    overview_bytes: bytes,
    panel_bytes: bytes,
    panel_storage_key: str,
    inspection_id: str,
    company_id: str,
    repository: ReportPipelineRepository,
) -> None:
    ov_tmp = panel_tmp = out_tmp = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(overview_bytes)
            ov_tmp = f.name
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(panel_bytes)
            panel_tmp = f.name
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            out_tmp = f.name

        generate_panel_location_image(ov_tmp, panel_tmp, out_tmp)

        with open(out_tmp, "rb") as f:
            annotated = f.read()

        stem = Path(panel_storage_key).stem
        location_key = str(Path(panel_storage_key).parent / f"{stem}_location.jpg")
        await blob.upload_file("inspections", location_key, annotated, "image/jpeg")

        await repository.insert_image_analysis(
            inspection_id,
            company_id,
            location_key,
            "Locatiefoto: overzichtsopname met markering van de geïnspecteerde paneelpositie.",
            panel_location_key=location_key,
        )
        logger.info("Location image inserted for {}", panel_storage_key)

    except Exception:
        logger.exception(
            "Panel location image failed for {} — skipping locatie slot", panel_storage_key
        )
    finally:
        for p in (ov_tmp, panel_tmp, out_tmp):
            if p:
                Path(p).unlink(missing_ok=True)
