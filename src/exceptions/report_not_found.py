class ReportNotFound(Exception):
    def __init__(self, report_id: str) -> None:
        self.report_id = report_id
        super().__init__(f"Report {report_id} not found")
