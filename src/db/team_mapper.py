import asyncpg

from src.models.team.member import TeamMember


def map_team_member(row: asyncpg.Record) -> TeamMember:
    return TeamMember.model_validate(dict(row))
