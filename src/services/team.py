from src.db.team import queries
from src.models.team.member import TeamMember


async def list_team_members(company_id: str) -> list[TeamMember]:
    return await queries.list_company_members(company_id)
