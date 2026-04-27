"""
Load the onboarding *system* prompt from disk so copy lives outside Python code.
Optional: set `onboarding_system_prompt_path` in Settings to an absolute file path
(e.g. mounted ConfigMap) to override the bundled `onboarding_system.md`.
"""

import logging
from pathlib import Path

from app.core.config import Settings

logger = logging.getLogger(__name__)

_BUNDLED = Path(__file__).resolve().parent / "onboarding_system.md"
_FALLBACK = (
    "You are the Whatcommerce WhatsApp signup assistant. Be warm and concise. "
    "Use the provided tools to read and save signup data and to create a Paystack link."
)


def get_onboarding_system_base(settings: Settings) -> str:
    override = (getattr(settings, "onboarding_system_prompt_path", None) or "").strip()
    if override:
        p = Path(override)
        if p.is_file():
            try:
                return p.read_text(encoding="utf-8").strip()
            except OSError as e:
                logger.error("onboarding prompt override read failed: %s", e)
        else:
            logger.warning(
                "onboarding_system_prompt_path set but not a file: %s", override
            )
    if _BUNDLED.is_file():
        try:
            return _BUNDLED.read_text(encoding="utf-8").strip()
        except OSError as e:
            logger.error("bundled onboarding prompt read failed: %s", e)
    logger.warning("using minimal fallback onboarding system prompt")
    return _FALLBACK
