from src.integrations import report_repository
from src.models.auth.authentication import CurrentUser
from src.models.reports.report import ReportSummary


async def list_reports_for_user(user: CurrentUser) -> list[ReportSummary]:
    return await report_repository.list_report_summaries_by_company_id(str(user.company_id))
