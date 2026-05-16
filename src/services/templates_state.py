from src.models.templates.records import CompanyTemplateRecord, TemplateAnalysisJobRecord
from src.models.templates.state import TemplateCompanyState


def resolve_template_company_state(
    company: CompanyTemplateRecord,
    job: TemplateAnalysisJobRecord | None,
) -> TemplateCompanyState:
    if job is not None:
        if job.status in {"queued", "processing", "extracting"}:
            return TemplateCompanyState(
                view_status="extracting",
                job_id=job.id,
                reports_count=job.reports_count,
            )

        if job.status == "pending_review":
            return TemplateCompanyState(
                view_status="pending_review",
                structure=job.structure,
                job_id=job.id,
                reports_count=job.reports_count,
            )

        if job.status == "failed":
            if company.template_id is not None:
                return TemplateCompanyState(
                    view_status="active",
                    structure=company.structure,
                    template_id=company.template_id,
                )

            return TemplateCompanyState(
                view_status="failed",
                job_id=job.id,
                reports_count=job.reports_count,
                error_message=job.error_message,
            )

        if job.status == "active":
            structure = company.structure if company.template_id is not None else job.structure

            return TemplateCompanyState(
                view_status="active",
                structure=structure,
                job_id=job.id,
                template_id=company.template_id or job.template_id,
                reports_count=job.reports_count,
            )

    if company.template_id is not None:
        return TemplateCompanyState(
            view_status="active",
            structure=company.structure,
            template_id=company.template_id,
        )

    return TemplateCompanyState(view_status="not_configured")


def resolve_template_job_state(job: TemplateAnalysisJobRecord) -> TemplateCompanyState:
    if job.status in {"queued", "processing", "extracting"}:
        return TemplateCompanyState(
            view_status="extracting",
            job_id=job.id,
            reports_count=job.reports_count,
        )

    if job.status == "pending_review":
        return TemplateCompanyState(
            view_status="pending_review",
            structure=job.structure,
            job_id=job.id,
            reports_count=job.reports_count,
        )

    if job.status == "failed":
        return TemplateCompanyState(
            view_status="failed",
            job_id=job.id,
            reports_count=job.reports_count,
            error_message=job.error_message,
        )

    return TemplateCompanyState(
        view_status="active",
        structure=job.structure,
        job_id=job.id,
        template_id=job.template_id,
        reports_count=job.reports_count,
    )
