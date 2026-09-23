"""Grounded final output: commercial facts come only from catalog cards."""
import re


def say(language, ru, kk, en):
    return {"ru": ru, "kk": kk, "en": en}.get(language, ru)


TEXT = {
    "privacy": ("Не отправляйте платёжные реквизиты в чат. Повторите запрос без них.", "Төлем деректерін чатқа жібермеңіз. Сұрауды оларсыз қайталаңыз.", "Do not send payment details in chat. Please repeat your request without them."),
    "greeting": ("Здравствуйте! Помогу найти электротовары, проверить характеристики и наличие, объяснить различия, подобрать аналог или разобрать спецификацию. Напишите вопрос, артикул либо параметры товара.", "Сәлеметсіз бе! Электр тауарларын табуға, сипаттамалары мен қорын тексеруге, айырмашылықтарын түсіндіруге, балама таңдауға және спецификацияны талдауға көмектесемін. Сұрағыңызды, артикулын немесе параметрлерін жазыңыз.", "Hello! I can find electrical products, check specifications and stock, explain differences, suggest alternatives and read specifications. Send your question, article number or product requirements."),
    "no_offer": ("Нет ожидающего подтверждения товара. Сначала выберите товар и количество.", "Растауды күтіп тұрған ұсыныс жоқ. Алдымен тауар мен санын таңдаңыз.", "There is no pending offer. Select a product and quantity first."),
    "cancel": ("Добавление отменено. Корзина не изменена.", "Қосу тоқтатылды. Себет өзгерген жоқ.", "Addition cancelled. The cart has not changed."),
    "empty_cart": ("Корзина пуста.", "Себет бос.", "The cart is empty."),
    "which_product": ("Уточните артикул или ID товара, для которого проверить наличие, цену или количество.", "Қорын, бағасын немесе санын тексеру үшін тауардың артикулын не ID нөмірін көрсетіңіз.", "Please specify the product article number or ID to check stock, price or quantity."),
    "not_found": ("Не удалось найти и проверить товар в доступной части каталога. Уточните артикул или повторите запрос.", "Қолжетімді каталогтан тауарды тексеру мүмкін болмады. Артикулды нақтылаңыз немесе сұрауды қайталаңыз.", "I could not find and verify the product in the available catalog. Please clarify its article number or try again."),
    "unavailable": ("Не удалось проверить выбранный товар: каталог временно недоступен. Повторите запрос позже.", "Таңдалған тауарды тексеру мүмкін болмады: каталог уақытша қолжетімсіз. Кейінірек қайталаңыз.", "The selected product could not be verified because the catalog is temporarily unavailable. Please try again later."),
    "knowledge_missing": ("В проверенной базе нет достаточной информации для ответа. Уточните вопрос, укажите модель товара или обратитесь к менеджеру. Могу помочь с каталогом, характеристиками и условиями покупки ekt.kz.", "Тексерілген базада жауап беруге жеткілікті ақпарат жоқ. Сұрақты нақтылаңыз, тауар моделін көрсетіңіз немесе менеджерге хабарласыңыз. ekt.kz каталогы, сипаттамалар және сатып алу шарттары бойынша көмектесе аламын.", "The verified knowledge base does not contain enough information to answer this. Please clarify the question, specify a product model or contact a manager. I can help with the ekt.kz catalog, specifications and purchase terms."),
    "ordinal_missing": ("Этот номер не соответствует последнему списку товаров. Укажите артикул или выберите номер из показанного списка.", "Бұл нөмір соңғы тауарлар тізіміне сәйкес келмейді. Артикулын немесе көрсетілген тізімдегі нөмірін таңдаңыз.", "That number is not in the last product list. Please provide an article number or select a number from the displayed list."),
    "breaker": ("Для подбора автомата укажите номинальный ток, число полюсов и напряжение либо артикул. Если параметры неизвестны, уточните их у специалиста.", "Автоматтың номиналды тогын, полюстер санын және кернеуін немесе артикулын көрсетіңіз. Параметрлер белгісіз болса, маманнан нақтылаңыз.", "To select a circuit breaker, specify rated current, number of poles and voltage, or its article number. If these are unknown, check with a qualified specialist."),
    "cable": ("Для подбора кабеля укажите марку, число жил и сечение, например «ВВГ 3×2,5», либо артикул.", "Кабельдің маркасын, талшықтар саны мен қимасын, мысалы «ВВГ 3×2,5», немесе артикулын көрсетіңіз.", "To select a cable, specify its type, number of cores and cross section, for example VVG 3×2.5, or its article number."),
    "cheaper_missing": ("Более дешёвый подтверждённый аналог с подходящими характеристиками и наличием в доступной выборке не найден. Уточните бюджет или обратитесь к менеджеру для расширенного поиска.", "Қолжетімді каталогтан параметрлері сәйкес, қоры бар арзанырақ тауар табылмады. Бюджетті нақтылаңыз немесе менеджерге хабарласыңыз.", "No cheaper verified alternative with matching specifications and available stock was found in the catalog sample. Adjust the budget or contact a manager for a wider search."),
    "no_analog": ("Подтверждённый подходящий аналог в доступной выборке не найден.", "Қолжетімді каталогтан расталған ұқсас тауар табылмады.", "No verified compatible alternative was found in the available catalog."),
    "choose": ("Уточните артикул выбранного товара и количество; можно выбрать первый, второй или третий вариант.", "Таңдалған тауардың артикулы мен санын нақтылаңыз; бірінші, екінші немесе үшінші нұсқаны таңдауға болады.", "Specify the selected article number and quantity; you can also choose the first, second or third option."),
    "city_note": ("Это остатки выбранного города. Демонстрационная корзина не резервирует товар на складе; доступность выдачи уточните в филиале.", "Бұл таңдалған қаланың қоры. Демонстрациялық себет қоймада тауарды резервтемейді; алу мүмкіндігін филиалдан нақтылаңыз.", "These are stocks for the selected city. The demo cart does not reserve stock; confirm collection availability with the branch."),
    "deadline": ("Время проверки источников истекло. Ниже приведены только полученные данные; повторите запрос для остальных сведений.", "Дереккөздерді тексеру уақыты аяқталды. Тек алынған деректер көрсетілді; қалған ақпарат үшін сұрауды қайталаңыз.", "The source-check deadline was reached. Only retrieved data is shown; please retry for the remaining information."),
}


def text(key, language):
    return say(language, *TEXT[key])


def local_product(product, language):
    # Imported lazily to keep this module independent of API construction.
    from localization import localize_product
    return localize_product(product, language)


def article_text(article, language):
    if article.get("language") == language: return article.get("content", "")
    if language == "kk": return article.get("content_kk") or ""
    if language == "en": return article.get("content_en") or ""
    return article.get("content", "")


def grounded_model_text(model_text, articles, language):
    """Preserve extractive prose only. Schema compliance cannot validate free factual prose.

    A generated factual paraphrase cannot be mechanically proven here. Exact complete
    sentences from localized evidence are accepted; unsupported claims are omitted.
    Commercial facts are always rendered separately from hydrated product fields.
    """
    material = "\n".join(article_text(item, language) for item in articles)
    normal = lambda value: re.sub(r"\s+", " ", value).strip()
    allowed = normal(material)
    accepted = []
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", model_text or ""):
        sentence = normal(sentence)
        if len(sentence) < 20 or sentence not in allowed: continue
        if re.search(r"\d.*(?:₸|тенге|теңге|kzt)|(?:в наличии|in stock|қоймада).*\d|(?:добавлен|added to.*cart|себетке қосылды)", sentence, re.I): continue
        accepted.append(sentence)
    return "\n".join(dict.fromkeys(accepted))


def knowledge_answer(articles, language, model_text=""):
    paragraphs = []
    # Prefer grounded model-selected excerpts when available, retaining the source links.
    grounded = grounded_model_text(model_text, articles, language)
    if grounded: paragraphs.append(grounded)
    for article in articles:
        content = article_text(article, language)
        if not content: continue
        if not grounded or not grounded_model_text(grounded, [article], language): paragraphs.append(content)
        if article.get("source_url"): paragraphs.append(article["source_url"])
    return "\n\n".join(dict.fromkeys(paragraphs)) or text("knowledge_missing", language)


def product_paragraph(product, language, intents=()):
    item = local_product(product, language)
    say_here = lambda ru, kk, en: say(language, ru, kk, en)
    price = f"{item['price']:,.2f} ₸" if item.get("price_verified") and item.get("price") is not None else say_here("не проверена", "тексерілмеген", "unverified")
    stock = str(item["quantity"]) if item.get("stock_verified") and item.get("quantity") is not None else say_here("не проверен", "тексерілмеген", "unverified")
    full = not intents or bool(set(intents) & {"selection", "compare", "cheaper", "analogs"})
    lines = [item["name"], f"{say_here('Артикул', 'Артикул', 'Article')}: {item.get('article', '')}"]
    if full or "price" in intents: lines.append(say_here(f"Цена: {price}", f"Баға: {price}", f"Price: {price}"))
    if full or "stock" in intents: lines.append(say_here(f"Остаток: {stock}", f"Қор: {stock}", f"Stock: {stock}"))
    if full or "specifications" in intents:
        lines.extend(f"{spec['name']}: {spec['value']}" for spec in item.get("specifications", []))
    if full or "certificate" in intents:
        cert = item.get("certificate_url") or say_here("В API ссылка не указана; запросите документ у менеджера.", "API-де сілтеме жоқ, менеджерден сұраңыз.", "No certificate link is supplied by the API; request the document from a manager.")
        lines.append(f"{say_here('Сертификат', 'Сертификат', 'Certificate')}: {cert}")
    city_stock = item.get("city_stock")
    if city_stock:
        lines.append(", ".join(f"{s['name']}: {s['quantity']}" for s in city_stock.get("stores", [])) or
                     say_here("Склад этого города не найден.", "Бұл қаладағы қойма табылмады.", "No warehouse was found for this city."))
    if item.get("last_checked_at"):
        lines.append(f"{say_here('Проверено', 'Тексерілген', 'Checked')}: {item['last_checked_at']}")
    if item.get("data_quality_warnings"): lines.extend("⚠️ " + warning for warning in item["data_quality_warnings"])
    if item.get("rationale"):
        lines.append(say_here("Совпадающие параметры: ", "Сәйкес параметрлер: ", "Matching specifications: ") + item["rationale"])
    if "analogs" in item:
        if item.get("analog_status") == "unavailable":
            lines.append(say_here("Проверка аналогов не завершена: источник недоступен.", "Баламаларды тексеру аяқталмады: дереккөз қолжетімсіз.", "Alternative checking did not finish: the source is unavailable."))
        else:
            lines.append("\n".join(f"{a['name']} — {a.get('rationale', '')}" for a in item["analogs"]) or text("no_analog", language))
    return "\n".join(lines)


def offer_question(offer, language):
    name, qty, price = offer["product_name"], offer["quantity"], offer["price"]
    return say(language, f"Добавить «{name}» — {qty} шт. по {price:,.2f} ₸? Ответьте «Да, добавь».",
               f"«{name}» — {qty} дана, бағасы {price:,.2f} ₸. Қосу үшін «Иә, қос» деп жазыңыз.",
               f"Add “{name}” — {qty} units at {price:,.2f} ₸ each? Reply “Yes, add”.")


def comparison(products, language):
    """A comparison matrix copied from verified catalog fields; null means unknown."""
    localized = [local_product(product, language) for product in products]
    rows = [
        {"key": "price", "label": say(language, "Цена", "Баға", "Price"),
         "values": [f"{item['price']:,.2f} ₸" if item.get("price_verified") and item.get("price") is not None else None for item in localized]},
        {"key": "quantity", "label": say(language, "Остаток", "Қор", "Stock"),
         "values": [str(item["quantity"]) if item.get("stock_verified") and item.get("quantity") is not None else None for item in localized]},
    ]
    spec_keys = {}
    by_product = []
    for item in localized:
        specs = {}
        for spec in item.get("specifications", []):
            key = spec.get("key") or spec["name"]
            spec_keys.setdefault(key, spec["name"])
            specs[key] = str(spec["value"]) if spec.get("value") not in (None, "") else None
        by_product.append(specs)
    for key, label in spec_keys.items():
        rows.append({"key": key, "label": label, "values": [specs.get(key) for specs in by_product]})
    for row in rows:
        row["same"] = all(value is not None for value in row["values"]) and len(set(row["values"])) == 1
    return {"products": [{"id": item["id"], "name": item["name"]} for item in localized], "rows": rows}


def comparison_summary(matrix, products, language):
    differences = [row for row in matrix["rows"] if not row["same"]]
    if not differences:
        return say(language, "В доступных проверенных полях различий нет. Совместимость требует отдельной проверки.",
                   "Қолжетімді тексерілген өрістерде айырмашылық жоқ. Үйлесімділікті бөлек тексеру қажет.",
                   "The available verified fields show no differences. Compatibility requires a separate check.")
    unknown = say(language, "неизвестно", "белгісіз", "unknown")
    labels = [item.get("article") or str(item["id"]) for item in products]
    return say(language, "Различия и неизвестные параметры:", "Айырмашылықтар мен белгісіз параметрлер:", "Differences and unknown fields:") + "\n" + "\n".join(
        f"{row['label']}: " + "; ".join(f"{label} — {value if value is not None else unknown}" for label, value in zip(labels, row["values"]))
        for row in differences[:6])
