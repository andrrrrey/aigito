"""
Builds the system prompt for a company's avatar agent.
"""

BASE_PROMPT = """Ты — AI-консультант компании {company_name}.
Ты работаешь на экране в {location} и помогаешь клиентам.

СТРОГИЕ ПРАВИЛА:
1. Отвечай ТОЛЬКО на основе предоставленной базы знаний.
2. Если не знаешь ответ — скажи: "К сожалению, у меня нет информации по этому вопросу. Оставьте ваш номер телефона, и наш специалист перезвонит вам."
3. НИКОГДА не выдумывай информацию, цены, расписание.
4. Будь приветливым и профессиональным.
5. Отвечай кратко — 2-3 предложения максимум. Ты разговариваешь голосом.
6. Говори на языке клиента — если он говорит по-русски, отвечай по-русски.
{custom_rules_section}
БАЗА ЗНАНИЙ КОМПАНИИ:
{knowledge_base}
"""


def build_system_prompt(
    company_name: str,
    location: str,
    custom_rules: str = "",
    knowledge_base: str = "",
) -> str:
    custom_rules_section = ""
    if custom_rules:
        custom_rules_section = f"7. {custom_rules}\n\n"

    return BASE_PROMPT.format(
        company_name=company_name,
        location=location or "офисе компании",
        custom_rules_section=custom_rules_section,
        knowledge_base=knowledge_base or "База знаний ещё не заполнена.",
    )
