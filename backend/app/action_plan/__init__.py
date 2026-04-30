"""F31 — Plan d'Action ESG (MVP) : module backend.

Expose le routeur FastAPI et le service principal.
"""

from app.action_plan.routes import router  # noqa: F401
from app.action_plan.service import (  # noqa: F401
    ActionPlanService,
    NoScoreCalculationError,
)
