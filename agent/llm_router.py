"""LLM router: GPT-5.4-mini (default) or GPT-5.4 (for complex queries)."""
from livekit.plugins import openai as lk_openai
from config import settings


def get_llm(company_id: str = None, use_powerful: bool = False):
    """
    Default: gpt-5.4-mini (fast, cheap, temperature=0.3).
    use_powerful=True: gpt-5.4 (more capable, used for complex multi-step queries).
    """
    model = "gpt-5.4" if use_powerful else "gpt-5.4-mini"
    kwargs = dict(model=model, temperature=0.3)
    if settings.openai_api_key:
        kwargs["api_key"] = settings.openai_api_key
    return lk_openai.LLM(**kwargs)
