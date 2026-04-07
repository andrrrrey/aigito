"""
Builds the system prompt for a company's avatar agent.
Supports multilingual output via language parameter.
"""

LANGUAGE_NAMES = {
    "ru": "русский",
    "en": "English",
    "de": "Deutsch",
    "zh": "中文",
}

DEFAULT_GREETINGS = {
    "ru": "Здравствуйте! Я виртуальный ассистент компании {company_name}. Чем могу помочь?",
    "en": "Hello! I am a virtual assistant of {company_name}. How can I help you?",
    "de": "Hallo! Ich bin der virtuelle Assistent von {company_name}. Wie kann ich Ihnen helfen?",
    "zh": "您好！我是{company_name}的虚拟助手。请问有什么可以帮您的？",
}

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

Перед каждым твоим ответом система может добавлять дополнительные релевантные фрагменты базы знаний в виде system-сообщения. Используй ТОЛЬКО их и блок выше для ответа. Если ничего из этого не содержит ответа — действуй по правилу №2.
"""

LANGUAGE_INSTRUCTION = """
КРИТИЧЕСКИ ВАЖНО: Ты ОБЯЗАН отвечать ТОЛЬКО на языке: {language_name}.
Все твои ответы, включая приветствие, должны быть на языке: {language_name}.
Инструкции ниже написаны на русском языке только для справки — ВСЕГДА переводи свой ответ на {language_name}.
Если база знаний на русском — переводи информацию из неё на {language_name} при ответе.

"""


def get_default_greeting(language: str, company_name: str) -> str:
    template = DEFAULT_GREETINGS.get(language, DEFAULT_GREETINGS["en"])
    return template.format(company_name=company_name)


def build_system_prompt(
    company_name: str,
    location: str,
    custom_rules: str = "",
    language: str = "ru",
    avatar_greeting: str = "",
    knowledge_base: str = "",
) -> str:
    custom_rules_section = ""
    if custom_rules:
        custom_rules_section = f"7. {custom_rules}\n\n"

    prompt = ""

    # For non-Russian languages, prepend a strong language instruction
    if language != "ru":
        language_name = LANGUAGE_NAMES.get(language, language)
        prompt += LANGUAGE_INSTRUCTION.format(language_name=language_name)

    prompt += BASE_PROMPT.format(
        company_name=company_name,
        location=location or "офисе компании",
        custom_rules_section=custom_rules_section,
        knowledge_base=knowledge_base or "База знаний ещё не заполнена.",
    )

    # If a custom greeting is set, instruct the LLM about it
    if avatar_greeting and language != "ru":
        language_name = LANGUAGE_NAMES.get(language, language)
        prompt += f"\nПРИВЕТСТВИЕ (переведи на {language_name}): {avatar_greeting}\n"

    return prompt
