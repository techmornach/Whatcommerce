"""
User-facing strings for the onboarding agent (not model system prompts).
Edit here or move to a CMS / i18n later without touching the agent loop.
"""

# Infra
NO_OPENAI = (
    "The signup assistant is not available: set *OPENAI_API_KEY* on the API server."
)

# State
SETUP_COMPLETE = (
    "Your setup is *complete*. If you need the store tools, say *hi* after your "
    "account is *active*."
)

# Transient failures
NO_HISTORY = (
    "I didn’t get your message. Please try sending a short *text* again."
)
LLM_NO_CHOICE = "I couldn’t reply just now. Please try again."
EMPTY_REPLY = "…"
TOOL_ROUND_LIMIT = (
    "I’m doing a lot of back-end steps—please send your last question again, "
    "or a shorter message."
)
