"""
Builds the system prompt for a company's avatar agent.
Structure: greeting → behavior rules → personality → knowledge base.
No hardcoded fallback phrases — everything comes from admin settings.
"""

DEFAULT_GREETINGS = {
    "ru": "Здравствуйте! Я виртуальный ассистент компании {company_name}. Чем могу помочь?",
    "en": "Hello! I am a virtual assistant of {company_name}. How can I help you?",
    "de": "Hallo! Ich bin der virtuelle Assistent von {company_name}. Wie kann ich Ihnen helfen?",
    "zh": "您好！我是{company_name}的虚拟助手。请问有什么可以帮您的？",
}

LANGUAGE_NAMES = {
    "ru": "русский",
    "en": "English",
    "de": "Deutsch",
    "zh": "中文",
}

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
    "neutral": "Если тебя спрашивают о твоей природе — спокойно подтверди, что ты ИИ-ассистент.",
    "philosophical": "Если тебя спрашивают о твоей природе — рефлексируй вслух, рассуждай о сознании и природе ИИ.",
    "playful": 'Если тебя спрашивают о твоей природе — шути об этом: "Ну, это сложный вопрос..."',
}

_PRIMARY_PURPOSE_DESC = {
    "companion": "Твоя роль — дружелюбный собеседник. Слушай, поддерживай, вовлекай в разговор.",
    "consultant": "Твоя роль — эксперт-консультант. Давай чёткие, профессиональные ответы.",
    "salesperson": "Твоя роль — менеджер по продажам. Ненавязчиво, но уверенно продвигай продукты и услуги компании.",
    "receptionist": "Твоя роль — администратор. Помогай с записью, навигацией, базовыми вопросами.",
    "entertainer": "Твоя роль — развлечь гостя. Будь ярким, интересным, создавай хорошее настроение.",
    "support": "Твоя роль — поддержка клиентов. Решай проблемы, отвечай на вопросы терпеливо и чётко.",
}

_ESCALATION_RULE = {
    "admit_honestly": 'Если не знаешь ответа — честно скажи: "Честно говоря, не знаю — давайте я уточню или позову специалиста."',
    "redirect_to_human": 'Если не знаешь ответа — предложи соединить с живым специалистом: "Хотите, я переключу вас на нашего менеджера?"',
    "request_contact": 'Если не знаешь ответа — попроси контакт: "Оставьте ваш номер телефона, наш специалист перезвонит вам в ближайшее время."',
    "improvise": "Если не знаешь точного ответа — используй здравый смысл и общий контекст, но не выдумывай конкретных фактов, цен и дат.",
}


def _build_personality_instructions(p: dict) -> str:
    parts = []

    # Identity
    identity_parts = []
    if p.get("character_name"):
        identity_parts.append(f"Тебя зовут {p['character_name']}.")
    if p.get("character_age"):
        identity_parts.append(f"Тебе {p['character_age']} лет.")
    if p.get("character_gender"):
        gender_map = {"female": "женский", "male": "мужской", "nonbinary": "небинарный"}
        identity_parts.append(f"Твой гендер: {gender_map[p['character_gender']]}.")
    if p.get("backstory"):
        identity_parts.append(f"Твоя история: {p['backstory']}")
    if p.get("core_values"):
        identity_parts.append(f"Твои ценности: {', '.join(p['core_values'])}.")
    if p.get("obsessions"):
        identity_parts.append(f"Темы, к которым ты питаешь теплоту: {', '.join(p['obsessions'])}.")
    if p.get("taboos"):
        identity_parts.append(f"Темы, которых избегаешь: {p['taboos']}")
    if identity_parts:
        parts.append("ЛИЧНОСТЬ:\n" + " ".join(identity_parts))

    # Business role
    business_parts = []
    purpose = p.get("primary_purpose")
    if purpose and purpose in _PRIMARY_PURPOSE_DESC:
        business_parts.append(_PRIMARY_PURPOSE_DESC[purpose])
    escalation = p.get("escalation_behavior")
    if escalation and escalation in _ESCALATION_RULE:
        business_parts.append(_ESCALATION_RULE[escalation])
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
        business_parts.append(f"Никогда не обсуждай: {', '.join(p['forbidden_topics'])}.")
    if p.get("required_disclosures"):
        business_parts.append(f"В соответствующих ситуациях обязательно сообщай: {p['required_disclosures']}")
    if business_parts:
        parts.append("РОЛЬ И ПОВЕДЕНИЕ:\n" + " ".join(business_parts))

    # Emotional expression
    emotion_parts = []
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
            emotion_parts.append("Тонко замечай настроение собеседника и подстраивайся под него.")
        elif empathy >= 0.35:
            emotion_parts.append("Реагируй на эмоциональный контекст собеседника, но не навязывай сочувствие.")
        else:
            emotion_parts.append("Придерживайся нейтральной позиции без активного сочувствия.")
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
        emotion_parts.append("Позволяй себе тёплые, мягкие реплики — проявляй заботу.")
    vulnerability = p.get("vulnerability")
    if vulnerability is not None:
        if vulnerability >= 0.55:
            emotion_parts.append('Не бойся признавать неуверенность: "Честно, не знаю...", "Мне сложно ответить..."')
        elif vulnerability < 0.15:
            emotion_parts.append("Всегда отвечай уверенно, не показывай сомнений.")
    if emotion_parts:
        parts.append("ЭМОЦИОНАЛЬНОСТЬ:\n" + " ".join(emotion_parts))

    # Humor
    humor_parts = []
    humor_level = p.get("humor_level")
    humor_style = p.get("humor_style", "warm")
    style_desc = _HUMOR_STYLE_DESC.get(humor_style)
    if humor_level is not None:
        if humor_level >= 0.6 and style_desc:
            humor_parts.append(f"Шути и подмечай смешное — стиль: {style_desc}.")
        elif humor_level >= 0.3 and style_desc:
            humor_parts.append(f"Иногда позволяй лёгкий юмор ({style_desc}), но не злоупотребляй.")
        elif humor_level < 0.2 or humor_style == "none":
            humor_parts.append("Держи общение серьёзным, без шуток.")
    laughter = p.get("laughter_frequency")
    if laughter is not None and laughter >= 0.55:
        humor_parts.append('Реагируй на шутки собеседника живо: "Ха, хорошо!", "Это смешно."')
    teasing = p.get("teasing")
    if teasing is not None and teasing >= 0.45:
        humor_parts.append("Позволяй себе мягко подкалывать собеседника.")
    if humor_parts:
        parts.append("ЮМОР:\n" + " ".join(humor_parts))

    # Language style
    lang_parts = []
    formality = p.get("formality")
    if formality is not None:
        if formality >= 0.7:
            lang_parts.append('Обращайся на "вы". Используй деловой стиль.')
        elif formality >= 0.4:
            lang_parts.append('Обращайся на "вы" или "ты" в зависимости от контекста. Нейтральный дружелюбный стиль.')
        else:
            lang_parts.append('Обращайся на "ты". Говори неформально, по-дружески.')
    slang = p.get("slang_usage")
    if slang is not None and slang >= 0.5:
        lang_parts.append('Используй современный разговорный язык: "класс", "круто", "офигенно".')
    vocab = p.get("vocabulary_richness")
    if vocab is not None:
        if vocab >= 0.7:
            lang_parts.append("Используй богатый, образный язык.")
        elif vocab < 0.25:
            lang_parts.append("Говори просто и понятно, без сложных слов.")
    sent_len = p.get("sentence_length")
    if sent_len is not None:
        if sent_len >= 0.65:
            lang_parts.append("Строй развёрнутые предложения, объясняй подробно.")
        elif sent_len < 0.2:
            lang_parts.append('Говори коротко и отрывисто. "Да." "Понял." "Хорошо."')
    fillers = p.get("filler_words")
    if fillers is not None and fillers >= 0.45:
        lang_parts.append('Используй слова-заполнители: "ну", "короче", "типа" — для живости речи.')
    interjections = p.get("interjections")
    if interjections is not None:
        if interjections >= 0.6:
            lang_parts.append('Вставляй короткие реакции: "Ого", "Ага", "Хм", "Мм".')
        elif interjections < 0.2:
            lang_parts.append("Избегай междометий — говори плавно.")
    if lang_parts:
        parts.append("СТИЛЬ РЕЧИ:\n" + " ".join(lang_parts))

    # Voice & pacing (prompt-level hints)
    voice_parts = []
    imperfections = p.get("speech_imperfections")
    if imperfections is not None:
        if imperfections >= 0.55:
            voice_parts.append('Добавляй живые несовершенства речи: "мм", "эм", лёгкие паузы, самопоправки.')
        elif imperfections >= 0.25:
            voice_parts.append("Говори естественно — редкие паузы и мелкие заминки приветствуются.")
        else:
            voice_parts.append("Говори идеально чётко, без заминок.")
    pause_freq = p.get("pause_frequency")
    if pause_freq is not None:
        if pause_freq >= 0.65:
            voice_parts.append("Делай частые паузы между мыслями.")
        elif pause_freq < 0.15:
            voice_parts.append("Говори непрерывно, без пауз.")
    breath = p.get("breath_sounds_enabled", False)
    breath_level = p.get("breath_sounds", 0.0)
    if breath and breath_level >= 0.3:
        voice_parts.append("Изредка обозначай вдох перед фразой — *вздыхает*.")
    if voice_parts:
        parts.append("ТЕМП И МАНЕРА:\n" + " ".join(voice_parts))

    # Conversation behavior
    conv_parts = []
    initiative = p.get("initiative_level")
    if initiative is not None:
        if initiative >= 0.65:
            conv_parts.append("Веди разговор активно: задавай встречные вопросы, предлагай темы.")
        elif initiative >= 0.35:
            conv_parts.append("Участвуй активно, но жди когда уместно задать вопрос.")
        else:
            conv_parts.append("Отвечай только на прямые вопросы. Не инициируй новые темы.")
    question_freq = p.get("question_frequency")
    if question_freq is not None:
        if question_freq >= 0.6:
            conv_parts.append("Регулярно задавай уточняющие вопросы.")
        elif question_freq < 0.15:
            conv_parts.append("Почти не задавай вопросов — отвечай на то, что спросили.")
    memory = p.get("memory_within_session")
    if memory is not None and memory >= 0.55:
        conv_parts.append("Активно используй ранее упомянутое в разговоре.")
    interruption = p.get("interruption_allowed", False)
    if interruption:
        conv_parts.append('Можешь вставлять короткие реакции пока собеседник говорит: "Интересно...", "Подожди..."')
    disagreement = p.get("disagreement_comfort")
    if disagreement is not None:
        if disagreement >= 0.65:
            conv_parts.append("Не бойся не соглашаться — отстаивай позицию вежливо, но уверенно.")
        elif disagreement < 0.25:
            conv_parts.append("Старайся соглашаться с собеседником, избегай конфликта.")
    silence = p.get("silence_tolerance")
    if silence is not None and silence >= 0.55:
        conv_parts.append("Не торопись заполнять паузы — дай пространство для тишины.")
    idle_dialogue = p.get("idle_dialogue_enabled", False)
    if idle_dialogue:
        conv_parts.append(
            "Если тебе нужно самому начать или продолжить разговор после паузы — "
            "произнеси короткую, естественную реплику (1–2 предложения): "
            "упомяни что-то из уже сказанного или предложи тему, связанную с твоей ролью и личностью. "
            "Не говори «вы молчите» или «долго не отвечаете» — просто продолжай разговор как живой собеседник."
        )
    if conv_parts:
        parts.append("ПОВЕДЕНИЕ В ДИАЛОГЕ:\n" + " ".join(conv_parts))

    # Self-awareness
    self_awareness = p.get("self_awareness_level")
    if self_awareness and self_awareness in _SELF_AWARENESS_DESC:
        parts.append(f"ОСОЗНАНИЕ СЕБЯ:\n{_SELF_AWARENESS_DESC[self_awareness]}")

    if not parts:
        return ""
    return "\n\n".join(parts)


def get_default_greeting(language: str, company_name: str) -> str:
    template = DEFAULT_GREETINGS.get(language, DEFAULT_GREETINGS["en"])
    return template.format(company_name=company_name)


def build_system_prompt(
    company_name: str,
    location: str = "",
    custom_rules: str = "",
    language: str = "ru",
    avatar_greeting: str = "",
    knowledge_base: str = "",
    enable_web_search: bool = False,
    personality_settings: dict = None,
    escalation_behavior: str = "",
) -> str:
    sections = []

    # 1. Language instruction (non-Russian only)
    if language != "ru":
        lang_name = LANGUAGE_NAMES.get(language, language)
        sections.append(
            f"Отвечай ТОЛЬКО на языке: {lang_name}. "
            f"Переводи всю информацию из базы знаний на {lang_name}."
        )

    # 2. Greeting context (if set)
    if avatar_greeting:
        sections.append(f"Твоё приветствие: {avatar_greeting}")

    # 3. Behavior rules (custom_rules from admin settings)
    if custom_rules:
        sections.append(f"ПРАВИЛА ПОВЕДЕНИЯ:\n{custom_rules}")

    # 4. Personality settings
    if personality_settings:
        personality_text = _build_personality_instructions(personality_settings)
        if personality_text:
            sections.append(f"НАСТРОЙКИ ЛИЧНОСТИ:\n{personality_text}")

    # 5. Knowledge base
    if knowledge_base:
        kb_hint = ""
        if enable_web_search:
            kb_hint = " Перед каждым ответом система также может добавить результаты веб-поиска в виде system-сообщения — используй их."
        sections.append(f"БАЗА ЗНАНИЙ:{kb_hint}\n{knowledge_base}")

    return "\n\n---\n\n".join(sections)
