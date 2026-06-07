from src.db import team_queries
from src.models.team.member import TeamMember


async def list_team_members(company_id: str) -> list[TeamMember]:
    return await team_queries.list_company_members(company_id)
