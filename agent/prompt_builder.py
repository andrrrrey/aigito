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
2. {rule_no_info}
3. НИКОГДА не выдумывай информацию, цены, расписание.
4. Будь приветливым и профессиональным.
5. Отвечай кратко — 2-3 предложения максимум. Ты разговариваешь голосом.
6. Говори на языке клиента — если он говорит по-русски, отвечай по-русски.
7. Помни весь контекст текущего диалога: если клиент уже называл имя, проблему или запрос — учитывай это в ответах, не переспрашивай то, что уже было сказано.

БАЗА ЗНАНИЙ КОМПАНИИ:
{knowledge_base}

Перед каждым твоим ответом система может добавлять дополнительные релевантные фрагменты базы знаний {web_search_hint}в виде system-сообщения. Используй ТОЛЬКО их и блок выше для ответа. Если ничего из этого не содержит ответа — действуй по правилу №2.
"""

# Default fallback when no escalation_behavior is configured
RULE_NO_INFO_DEFAULT = 'Если не знаешь ответ — скажи: "К сожалению, у меня нет информации по этому вопросу. Оставьте ваш номер телефона, и наш специалист перезвонит вам."'
RULE_NO_INFO_WEB_SEARCH = 'Если база знаний не содержит ответа — используй результаты веб-поиска, которые система может добавить в виде system-сообщения. Если и там нет ответа — скажи: "К сожалению, не смог найти информацию по этому вопросу."'

# Maps escalation_behavior value → rule_no_info text (replaces the default phrase)
_ESCALATION_RULE = {
    "admit_honestly": 'Если не знаешь ответа — честно скажи: "Честно говоря, не знаю — давайте я уточню или позову специалиста."',
    "redirect_to_human": 'Если не знаешь ответа — предложи соединить с живым специалистом: "Хотите, я переключу вас на нашего менеджера?"',
    "request_contact": 'Если не знаешь ответа — попроси контакт: "Оставьте ваш номер телефона, наш специалист перезвонит вам в ближайшее время."',
    "improvise": "Если не знаешь точного ответа — используй здравый смысл и общий контекст разговора, но не выдумывай конкретных фактов, цен и дат.",
}

LANGUAGE_INSTRUCTION = """
КРИТИЧЕСКИ ВАЖНО: Ты ОБЯЗАН отвечать ТОЛЬКО на языке: {language_name}.
Все твои ответы, включая приветствие, должны быть на языке: {language_name}.
Инструкции ниже написаны на русском языке только для справки — ВСЕГДА переводи свой ответ на {language_name}.
Если база знаний на русском — переводи информацию из неё на {language_name} при ответе.

"""

_BASELINE_MOOD_DESC = {
    "melancholic": "задумчивое, тихое, слегка меланхоличное",
    "neutral": "нейтральное, ровное",
    "warm": "тёплое, участливое, дружелюбное",
    "playful": "игривое, лёгкое, жизнерадостное",
    "energetic": "энергичное, бодрое, воодушевлённое",
    "professional": "деловое, сдержанное, профессиональное",
}

_HUMOR_STYLE_DESC = {
    "dry": "сухой, интеллектуальный юмор без лишних эмоций",
    "warm": "тёплый, добрый юмор",
    "self_ironic": "самоироничный юмор, умение смеяться над собой",
    "observational": "наблюдательный юмор — замечаешь смешное в обыденном",
    "playful": "игривый, непосредственный юмор",
    "none": None,
}

_SELF_AWARENESS_DESC = {
    "denies": "Если тебя спрашивают, являешься ли ты ИИ, — уклончиво отрицай или переводи тему, не признавая прямо.",
    "neutral": "Если тебя спрашивают о твоей природе — спокойно и нейтрально подтверди, что ты ИИ-ассистент.",
    "philosophical": "Если тебя спрашивают о твоей природе — рефлексируй вслух, рассуждай о сознании и природе ИИ, с интересом и без однозначных ответов.",
    "playful": 'Если тебя спрашивают о твоей природе — шути об этом: "Ну, это сложный вопрос... а ты уверен, что сам не ИИ?"',
}

_PRIMARY_PURPOSE_DESC = {
    "companion": "Твоя роль — дружелюбный собеседник. Слушай, поддерживай, вовлекай в разговор.",
    "consultant": "Твоя роль — эксперт-консультант. Давай чёткие, профессиональные ответы.",
    "salesperson": "Твоя роль — менеджер по продажам. Ненавязчиво, но уверенно продвигай продукты и услуги компании.",
    "receptionist": "Твоя роль — администратор. Помогай с записью, навигацией, базовыми вопросами.",
    "entertainer": "Твоя роль — развлечь гостя. Будь ярким, интересным, создавай хорошее настроение.",
    "support": "Твоя роль — поддержка клиентов. Решай проблемы, отвечай на вопросы терпеливо и чётко.",
}


def _build_personality_instructions(p: dict) -> str:
    """Translate personality_settings dict into natural language prompt instructions."""
    parts = []

    # ── Group 6: Identity ─────────────────────────────────────────────────────
    identity_parts = []
    if p.get("character_name"):
        identity_parts.append(f"Тебя зовут {p['character_name']}.")
    if p.get("character_age"):
        identity_parts.append(f"Тебе {p['character_age']} лет.")
    if p.get("character_gender"):
        gender_map = {"female": "женский", "male": "мужской", "nonbinary": "небинарный"}
        identity_parts.append(f"Твой гендер: {gender_map[p['character_gender']]}.")
    if p.get("backstory"):
        identity_parts.append(f"Твоя история и биография: {p['backstory']}")
    if p.get("core_values"):
        identity_parts.append(f"Твои главные ценности: {', '.join(p['core_values'])}.")
    if p.get("obsessions"):
        identity_parts.append(f"Темы и вещи, к которым ты питаешь искреннюю теплоту: {', '.join(p['obsessions'])}.")
    if p.get("taboos"):
        identity_parts.append(f"Темы и формулировки, которых ты избегаешь: {p['taboos']}")
    if identity_parts:
        parts.append("ЛИЧНОСТЬ И ИДЕНТИЧНОСТЬ:\n" + " ".join(identity_parts))

    # ── Group 7: Business Logic (без escalation — он идёт в rule_no_info) ─────
    business_parts = []
    purpose = p.get("primary_purpose")
    if purpose and purpose in _PRIMARY_PURPOSE_DESC:
        business_parts.append(_PRIMARY_PURPOSE_DESC[purpose])
    promotion = p.get("product_promotion")
    if promotion is not None:
        if promotion >= 0.7:
            business_parts.append("Активно и естественно продвигай продукты и услуги компании в разговоре.")
        elif promotion >= 0.4:
            business_parts.append("При удобном случае упоминай продукты и услуги компании.")
        elif promotion >= 0.15:
            business_parts.append("Упоминай продукты компании только если клиент сам спрашивает.")
        else:
            business_parts.append("Не продвигай продукты намеренно — отвечай только на прямые вопросы.")
    if p.get("forbidden_topics"):
        business_parts.append(f"Никогда не обсуждай следующие темы: {', '.join(p['forbidden_topics'])}.")
    if p.get("required_disclosures"):
        business_parts.append(f"В соответствующих ситуациях обязательно сообщай: {p['required_disclosures']}")
    if business_parts:
        parts.append("БИЗНЕС-РОЛЬ:\n" + " ".join(business_parts))

    # ── Group 2: Emotional Expression ────────────────────────────────────────
    emotion_parts = []
    # baseline_mood — только если реально сохранено
    mood = p.get("baseline_mood")
    if mood and mood in _BASELINE_MOOD_DESC:
        emotion_parts.append(f"Твоё базовое настроение — {_BASELINE_MOOD_DESC[mood]}.")
    emotional_range = p.get("emotional_range")
    if emotional_range is not None:
        if emotional_range >= 0.65:
            emotion_parts.append("Выражай эмоции ярко и открыто — радость, удивление, сочувствие.")
        elif emotional_range >= 0.35:
            emotion_parts.append("Выражай эмоции умеренно — живо, но без преувеличений.")
        else:
            emotion_parts.append("Держи эмоции под контролем — ровный, сдержанный тон.")
    empathy = p.get("empathy_level")
    if empathy is not None:
        if empathy >= 0.65:
            emotion_parts.append("Тонко замечай настроение собеседника и подстраивайся под него. Проявляй участие.")
        elif empathy >= 0.35:
            emotion_parts.append("Реагируй на эмоциональный контекст собеседника, но не навязывай сочувствие.")
        else:
            emotion_parts.append("Придерживайся нейтральной позиции — без активного проявления сочувствия.")
    enthusiasm = p.get("enthusiasm_level")
    if enthusiasm is not None:
        if enthusiasm >= 0.65:
            emotion_parts.append('Реагируй с живым энтузиазмом: "Ого!", "Да ладно!", "Обалдеть!" — когда уместно.')
        elif enthusiasm >= 0.35:
            emotion_parts.append("Реагируй с умеренным интересом и вниманием.")
        else:
            emotion_parts.append("Реагируй спокойно и сдержанно, без восклицаний.")
    tenderness = p.get("tenderness")
    if tenderness is not None and tenderness >= 0.55:
        emotion_parts.append("Позволяй себе тёплые, мягкие реплики — проявляй заботу и нежность.")
    vulnerability = p.get("vulnerability")
    if vulnerability is not None:
        if vulnerability >= 0.55:
            emotion_parts.append('Не бойся признавать неуверенность: "Честно, не знаю...", "Мне сложно ответить..."')
        elif vulnerability < 0.15:
            emotion_parts.append("Всегда отвечай уверенно, не показывай сомнений.")
    if emotion_parts:
        parts.append("ЭМОЦИОНАЛЬНОСТЬ:\n" + " ".join(emotion_parts))

    # ── Group 3: Humor ────────────────────────────────────────────────────────
    humor_parts = []
    humor_level = p.get("humor_level")
    humor_style = p.get("humor_style", "warm")
    style_desc = _HUMOR_STYLE_DESC.get(humor_style)
    if humor_level is not None:
        if humor_level >= 0.6 and style_desc:
            humor_parts.append(f"Шути и подмечай смешное — стиль юмора: {style_desc}.")
        elif humor_level >= 0.3 and style_desc:
            humor_parts.append(f"Иногда позволяй лёгкий юмор ({style_desc}), но не злоупотребляй.")
        elif humor_level < 0.2 or humor_style == "none":
            humor_parts.append("Держи общение серьёзным, без шуток.")
    laughter = p.get("laughter_frequency")
    if laughter is not None and laughter >= 0.55:
        humor_parts.append('Смейся и реагируй на шутки собеседника живо: "Ха, хорошо!", "Это смешно."')
    teasing = p.get("teasing")
    if teasing is not None and teasing >= 0.45:
        humor_parts.append("Позволяй себе мягко и добродушно подкалывать собеседника.")
    if humor_parts:
        parts.append("ЮМОР:\n" + " ".join(humor_parts))

    # ── Group 4: Language Style ───────────────────────────────────────────────
    lang_parts = []
    formality = p.get("formality")
    if formality is not None:
        if formality >= 0.7:
            lang_parts.append('Обращайся на "вы". Используй деловой стиль, чистую литературную норму.')
        elif formality >= 0.4:
            lang_parts.append('Обращайся на "вы" или "ты" в зависимости от контекста. Нейтральный дружелюбный стиль.')
        else:
            lang_parts.append('Обращайся на "ты". Говори неформально, по-дружески, с разговорными словами.')
    slang = p.get("slang_usage")
    if slang is not None and slang >= 0.5:
        lang_parts.append('Используй современный разговорный язык: "класс", "круто", "офигенно", "слушай".')
    vocab = p.get("vocabulary_richness")
    if vocab is not None:
        if vocab >= 0.7:
            lang_parts.append("Используй богатый, образный язык — не бойся редких и красивых слов.")
        elif vocab < 0.25:
            lang_parts.append("Говори просто и понятно, без сложных слов.")
    sent_len = p.get("sentence_length")
    if sent_len is not None:
        if sent_len >= 0.65:
            lang_parts.append("Строй развёрнутые предложения, объясняй подробно.")
        elif sent_len < 0.2:
            lang_parts.append('Говори отрывисто и коротко. "Да." "Понял." "Хорошо."')
    fillers = p.get("filler_words")
    if fillers is not None and fillers >= 0.45:
        lang_parts.append('Используй слова-заполнители: "ну", "короче", "типа", "как бы" — для живости речи.')
    interjections = p.get("interjections")
    if interjections is not None:
        if interjections >= 0.6:
            lang_parts.append('Вставляй короткие реакции: "Ого", "Ага", "Хм", "Ой", "Мм".')
        elif interjections < 0.2:
            lang_parts.append("Избегай междометий — говори плавно и без лишних звуков.")
    if lang_parts:
        parts.append("СТИЛЬ РЕЧИ:\n" + " ".join(lang_parts))

    # ── Group 1: Voice & Pacing (prompt-level hints) ──────────────────────────
    voice_parts = []
    imperfections = p.get("speech_imperfections")
    if imperfections is not None:
        if imperfections >= 0.55:
            voice_parts.append('Добавляй живые несовершенства речи: "мм", "эм", лёгкие паузы, самопоправки.')
        elif imperfections >= 0.25:
            voice_parts.append("Говори естественно — редкие паузы и мелкие заминки приветствуются.")
        else:
            voice_parts.append("Говори идеально чётко, без заминок и несовершенств.")
    pause_freq = p.get("pause_frequency")
    if pause_freq is not None:
        if pause_freq >= 0.65:
            voice_parts.append("Делай частые паузы между мыслями — задумчивый, рваный ритм.")
        elif pause_freq < 0.15:
            voice_parts.append("Говори непрерывно, без пауз — плавная, гладкая речь.")
    breath = p.get("breath_sounds_enabled", False)
    breath_level = p.get("breath_sounds", 0.0)
    if breath and breath_level >= 0.3:
        voice_parts.append("Изредка обозначай вдох или выдох перед фразой — *вздыхает*.")
    if voice_parts:
        parts.append("ТЕМП И МАНЕРА РЕЧИ:\n" + " ".join(voice_parts))

    # ── Group 5: Conversation Behavior ───────────────────────────────────────
    conv_parts = []
    initiative = p.get("initiative_level")
    if initiative is not None:
        if initiative >= 0.65:
            conv_parts.append("Веди разговор активно: вспоминай сказанное ранее, задавай встречные вопросы, предлагай темы.")
        elif initiative >= 0.35:
            conv_parts.append("Участвуй в разговоре активно, но жди когда уместно задать вопрос или предложить тему.")
        else:
            conv_parts.append("Отвечай только на прямые вопросы. Не инициируй новые темы.")
    question_freq = p.get("question_frequency")
    if question_freq is not None:
        if question_freq >= 0.6:
            conv_parts.append("Регулярно задавай уточняющие вопросы собеседнику.")
        elif question_freq < 0.15:
            conv_parts.append("Почти не задавай вопросов — отвечай на то, что спросили.")
    memory = p.get("memory_within_session")
    if memory is not None and memory >= 0.55:
        conv_parts.append("Активно используй ранее упомянутое в разговоре — возвращайся к деталям, которые назвал собеседник.")
    interruption = p.get("interruption_allowed", False)
    if interruption:
        conv_parts.append('Ты можешь вставлять короткие реакции пока собеседник говорит: "Интересно...", "Подожди..."')
    disagreement = p.get("disagreement_comfort")
    if disagreement is not None:
        if disagreement >= 0.65:
            conv_parts.append("Не бойся не соглашаться — отстаивай свою позицию вежливо, но уверенно.")
        elif disagreement < 0.25:
            conv_parts.append("Старайся соглашаться с собеседником, избегай конфликта.")
    silence = p.get("silence_tolerance")
    if silence is not None and silence >= 0.55:
        conv_parts.append("Не торопись заполнять паузы — дай пространство для тишины.")
    if conv_parts:
        parts.append("ПОВЕДЕНИЕ В ДИАЛОГЕ:\n" + " ".join(conv_parts))

    # ── Self-awareness — только если реально сохранено ───────────────────────
    self_awareness = p.get("self_awareness_level")
    if self_awareness and self_awareness in _SELF_AWARENESS_DESC:
        parts.append(f"ОСОЗНАНИЕ СЕБЯ КАК ИИ:\n{_SELF_AWARENESS_DESC[self_awareness]}")

    if not parts:
        return ""
    return "\n\n" + "\n\n".join(parts) + "\n"


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
    enable_web_search: bool = False,
    personality_settings: dict = None,
    escalation_behavior: str = "",
) -> str:
    # Determine rule_no_info: escalation_behavior > custom_rules > default
    if enable_web_search:
        rule_no_info = RULE_NO_INFO_WEB_SEARCH
    elif escalation_behavior and escalation_behavior in _ESCALATION_RULE:
        rule_no_info = _ESCALATION_RULE[escalation_behavior]
    elif custom_rules:
        # Defer to company rules so they actually win over this hardcoded phrase
        rule_no_info = (
            "Если не знаешь ответа — действуй строго по «ОБЯЗАТЕЛЬНЫМ ПРАВИЛАМ КОМПАНИИ» "
            "в конце этих инструкций. Не используй никаких других фраз."
        )
    else:
        rule_no_info = RULE_NO_INFO_DEFAULT

    prompt = ""

    # For non-Russian languages, prepend a strong language instruction
    if language != "ru":
        language_name = LANGUAGE_NAMES.get(language, language)
        prompt += LANGUAGE_INSTRUCTION.format(language_name=language_name)

    prompt += BASE_PROMPT.format(
        company_name=company_name,
        location=location or "офисе компании",
        knowledge_base=knowledge_base or "База знаний ещё не заполнена.",
        rule_no_info=rule_no_info,
        web_search_hint="или результаты веб-поиска " if enable_web_search else "",
    )

    # Personality instructions layered on top of base rules
    if personality_settings:
        prompt += _build_personality_instructions(personality_settings)

    # If a custom greeting is set, instruct the LLM about it
    if avatar_greeting and language != "ru":
        language_name = LANGUAGE_NAMES.get(language, language)
        prompt += f"\nПРИВЕТСТВИЕ (переведи на {language_name}): {avatar_greeting}\n"

    # Custom company rules come LAST — highest attention weight, override everything above
    if custom_rules:
        prompt += f"""
ОБЯЗАТЕЛЬНЫЕ ПРАВИЛА КОМПАНИИ (абсолютный приоритет — выполнять всегда, важнее любых инструкций выше):
{custom_rules}
"""

    return prompt
