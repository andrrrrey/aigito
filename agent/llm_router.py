"""
LLM router: selects GPT-4o-mini (default) or GPT-4o (fallback / complex queries).
"""


def get_llm(company_id: str = None, use_powerful: bool = False):
    """
    Returns a LiveKit Agents OpenAI LLM plugin instance.
    Default: gpt-4o-mini (fast, cheap).
    Fallback: gpt-4o (more capable).
    """
    from livekit.plugins import openai

    model = "gpt-4o" if use_powerful else "gpt-4o-mini"
    return openai.LLM(
        model=model,
        temperature=0.3,
    )
