from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from src.models.reports.pipeline import ReportPipelineContext


def build_report(status: str = "generating") -> ReportPipelineContext:
    return ReportPipelineContext(
        id=uuid4(),
        inspection_id=uuid4(),
        company_id=uuid4(),
        template_id=uuid4(),
        status=status,
        extra_context="Extra",
        metadata={
            "type_onderzoek": "Lekdetectie",
            "type_klant": "Zakelijk",
        },
    )


def build_pipeline_connection() -> MagicMock:
    connection = MagicMock()
    connection.execute = AsyncMock()
    transaction = MagicMock()
    transaction.__aenter__ = AsyncMock(return_value=None)
    transaction.__aexit__ = AsyncMock(return_value=None)
    connection.transaction = MagicMock(return_value=transaction)
    return connection
