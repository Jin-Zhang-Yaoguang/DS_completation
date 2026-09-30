"""V117 研究反馈与失败归因。"""

from .loss_attribution import (CATEGORY_DEFINITIONS, CATEGORY_LABELS,
                               LOSS_CATEGORIES, LossAttributionLedger)
from .research_feedback import (build_feedback_report, compute_oracle_metrics,
                                oracle_readiness, primary_failure)

__all__ = [
    "CATEGORY_DEFINITIONS", "CATEGORY_LABELS", "LOSS_CATEGORIES", "LossAttributionLedger",
    "build_feedback_report", "compute_oracle_metrics", "oracle_readiness", "primary_failure",
]
