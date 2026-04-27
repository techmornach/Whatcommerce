"""Allow onboarding FSM state 'complete' (Paystack activation).

Revision ID: 8b2a3c0d1e2f
Revises: 15e03674ff1e
Create Date: 2026-04-27

"""
from typing import Sequence, Union

from alembic import op

revision: str = "8b2a3c0d1e2f"
down_revision: Union[str, None] = "15e03674ff1e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_STATES = (
    "ask_name",
    "ask_business",
    "ask_address",
    "ask_email",
    "ask_plan",
    "ask_billing",
    "payment_sent",
    "complete",
)
_PREVIOUS = tuple(s for s in _STATES if s != "complete")


def upgrade() -> None:
    op.drop_constraint("onboarding_state", "onboarding_sessions", type_="check")
    _in = ", ".join(f"'{s}'" for s in _STATES)
    op.create_check_constraint(
        "onboarding_state",
        "onboarding_sessions",
        f"state IN ({_in})",
    )


def downgrade() -> None:
    op.drop_constraint("onboarding_state", "onboarding_sessions", type_="check")
    _in = ", ".join(f"'{s}'" for s in _PREVIOUS)
    op.create_check_constraint(
        "onboarding_state",
        "onboarding_sessions",
        f"state IN ({_in})",
    )
