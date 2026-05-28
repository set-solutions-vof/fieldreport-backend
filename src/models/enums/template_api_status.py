from typing import Literal

TemplateApiStatus = Literal[
    "not_configured",
    "processing",
    "pending_review",
    "active",
    "failed",
]
