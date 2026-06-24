from typing import Annotated
from uuid import UUID

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, Response, status

from src.db.connection import get_database
from src.db.report.queries import check_all_sections_approved
from src.db.schema.tables import reports as reports_table
from src.exceptions import ReportNotFound
from src.http.v1.request.report import ReportSectionUpdateRequest
from src.http.v1.response.report import (
    ReportDetailResponse,
    ReportSectionResponse,
    ReportSummaryResponse,
    report_detail_response,
    report_section_response,
    report_summary_responses,
)
from src.models.auth.authentication import CurrentUser
from src.security.authentication import get_current_user
from src.services import reports
from src.services.report_pdf import render_report_to_pdf
from src.storage.blob import upload_file

router = APIRouter(tags=["Reports"])


@router.get(
    "/api/v1/reports",
    response_model=list[ReportSummaryResponse],
    summary="List reports",
    description="Returns all reports for the authenticated user's company.",
)
async def get_reports(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> list[ReportSummaryResponse]:
    report_summaries = await reports.list_reports_for_user(current_user)

    return report_summary_responses(report_summaries)


@router.get(
    "/api/v1/reports/{report_id}",
    response_model=ReportDetailResponse,
    summary="Get report",
    description="Returns a single report with sections and evidence sources.",
)
async def get_report(
    report_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> ReportDetailResponse:
    try:
        report_detail = await reports.get_report_detail(str(report_id), current_user)
    except ReportNotFound:
        raise HTTPException(status_code=404, detail="Report not found")

    return report_detail_response(report_detail)


@router.patch(
    "/api/v1/reports/{report_id}/sections/{section_id}",
    response_model=ReportSectionResponse,
    summary="Update report section",
    description="Updates reviewed content and approval status for a report section.",
)
async def update_report_section(
    report_id: UUID,
    section_id: str,
    request_body: ReportSectionUpdateRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> ReportSectionResponse:
    try:
        section = await reports.update_report_section(
            str(report_id),
            section_id,
            current_user,
            request_body.reviewed_content,
            request_body.approved,
        )
    except ReportNotFound:
        raise HTTPException(status_code=404, detail="Report or section not found")

    return report_section_response(section)


@router.post(
    "/api/v1/reports/{report_id}/retry",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Retry report",
    description="Retries a failed report generation.",
)
async def retry_report(
    report_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> Response:
    try:
        await reports.retry_failed_report(str(report_id), current_user)
    except ReportNotFound:
        raise HTTPException(status_code=404, detail="Report not found")
    except ValueError:
        raise HTTPException(status_code=409, detail="Report can only be retried when failed")

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/api/v1/reports/{report_id}/export",
    summary="Export report to PDF",
    description="Renders approved report sections to PDF and returns the file.",
)
async def export_report(
    report_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> Response:
    company_id = current_user.company_id

    all_approved = await check_all_sections_approved(str(report_id), company_id)
    if not all_approved:
        raise HTTPException(
            status_code=422,
            detail="All report sections must be approved before export.",
        )

    pdf_bytes = await render_report_to_pdf(str(report_id), company_id)

    async with get_database().acquire() as conn:
        row = (await conn.execute(
            sa.select(reports_table.c.inspection_id)
            .where(
                reports_table.c.id == str(report_id),
                reports_table.c.company_id == company_id,
            )
        )).mappings().one()

    inspection_id = row["inspection_id"]
    pdf_key = f"{inspection_id}/reports/{report_id}.pdf"

    await upload_file("inspections", pdf_key, pdf_bytes, "application/pdf")

    async with get_database().acquire() as conn:
        await conn.execute(
            reports_table.update()
            .where(
                reports_table.c.id == str(report_id),
                reports_table.c.company_id == company_id,
            )
            .values(pdf_storage_key=pdf_key, updated_at=sa.func.now())
        )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="report-{report_id}.pdf"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )
