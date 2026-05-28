from typing import Literal

TemplateAnalysisJobStatus = Literal[
    "queued",
    "processing",
    "pending_review",
    "active",
    "failed",
]
