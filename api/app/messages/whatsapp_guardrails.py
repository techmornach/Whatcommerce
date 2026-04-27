"""User-facing copy for input/output guard rails."""

INPUT_GUARD_REFUSAL = (
    "I can’t act on that kind of request. I’m here to help with *Whatcommerce* and your store. "
    "What would you like to do with products, orders, or your account?"
)

# When the output guard flags generated text as unsafe to send; keep generic and short.
OUTPUT_GUARD_REPLACEMENT = (
    "I can’t show that message. Please ask again about your *store*, *products*, *orders*, "
    "or *subscription* and I’ll help right away."
)
