from types import SimpleNamespace
from unittest.mock import AsyncMock


class FakeResult:
    def __init__(
        self,
        row: dict[str, object] | None = None,
        rows: list[dict[str, object]] | None = None,
    ) -> None:
        self.row = row
        self.rows = rows if rows is not None else ([] if row is None else [row])

    def mappings(self):
        return self

    def first(self):
        return self.row

    def one(self):
        return self.row

    def all(self):
        return self.rows


def build_connection(
    row: dict[str, object] | None = None,
    rows: list[dict[str, object]] | None = None,
    results: list[FakeResult] | None = None,
) -> SimpleNamespace:
    execute = AsyncMock()

    if results is not None:
        execute.side_effect = results
    else:
        execute.return_value = FakeResult(row=row, rows=rows)

    return SimpleNamespace(execute=execute)
