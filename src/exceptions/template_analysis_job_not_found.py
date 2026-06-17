class TemplateAnalysisJobNotFound(Exception):
    def __init__(self, job_id: str, company_id: str) -> None:
        self.job_id = job_id
        self.company_id = company_id
        super().__init__(f"Template analysis job not found: {job_id}")
