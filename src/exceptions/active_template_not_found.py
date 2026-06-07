class ActiveTemplateNotFound(Exception):
    def __init__(self, company_id: str) -> None:
        self.company_id = company_id
        super().__init__(f"Active template not found for company: {company_id}")
