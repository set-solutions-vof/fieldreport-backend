from collections.abc import Mapping

from src.models.team.member import TeamMember


def map_team_member(row: Mapping[str, object]) -> TeamMember:
    return TeamMember.model_validate(dict(row))
