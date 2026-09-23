"""Conservative multilingual routing and canonical entities, independent of consent."""
import re
from .contracts import AgentPlan


NUMBER_WORDS = {
    "ноль": 0, "один": 1, "одна": 1, "одну": 1, "два": 2, "две": 2, "три": 3,
    "четыре": 4, "пять": 5, "шесть": 6, "семь": 7, "восемь": 8, "девять": 9, "десять": 10,
    "нөл": 0, "бір": 1, "екі": 2, "үш": 3, "төрт": 4, "бес": 5, "алты": 6, "жеті": 7,
    "сегіз": 8, "тоғыз": 9, "он": 10, "zero": 0, "one": 1, "two": 2, "three": 3,
    "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}
CITIES = {
    "астана": ("астан", "astana", "нур-султан", "nur-sultan", "nursultan"),
    "алматы": ("алмат", "almaty"), "шымкент": ("шымкент", "shymkent"),
    "тараз": ("тараз", "taraz"), "караганда": ("караганд", "қарағанд", "karaganda", "qaragandy"),
    "атырау": ("атырау", "atyrau"), "актау": ("актау", "ақтау", "aktau", "aqtau"),
    "талдыкорган": ("талдыкорган", "талдықорған", "taldykorgan", "taldyqorgan"),
    "усть-каменогорск": ("усть-каменогорск", "өскемен", "oskemen", "ust-kamenogorsk"),
}


def language(value):
    return "kk" if value == "kz" else value if value in {"ru", "kk", "en"} else "ru"


def quantity(message):
    text = message.lower().strip().rstrip(".!")
    units = r"(?:шт\.?|штук(?:и|а)?|ед\.?|дана|pcs|pieces?|units?)"
    match = re.search(r"(?<![\w.,+-])([+-]?\d+(?:[.,]\d+)?)\s*" + units + r"\b", text)
    match = match or re.fullmatch(r"(?:нужно|нужны|нужен|хочу|количество\s*[:=]?|i need|need|quantity\s*[:=]?)\s*([+-]?\d+(?:[.,]\d+)?)", text)
    match = match or re.search(r"(?<![\w.,+-])([+-]?\d+(?:[.,]\d+)?)\s+(?:автомат(?:а|ов)?|breakers?|кабел(?:я|ей)?)(?:\s|$)", text)
    if match:
        return float(match[1].replace(",", ".")) if re.search(r"[.,]", match[1]) else int(match[1])
    words = "|".join(NUMBER_WORDS)
    found = re.search(r"(?<!\w)(" + words + r")\s*" + units + r"\b", text)
    found = found or re.fullmatch(r"(?:нужно|нужны|нужен|хочу|i need|need)?\s*(" + words + r")(?:\s+керек)?", text)
    return NUMBER_WORDS[found[1]] if found else None


def budget(message):
    found = re.search(r"(?:бюджет\s*[:=]?|до|не дороже|budget\s*[:=]?|up to|under|below)\s*(\d+(?:[.,]\d{1,2})?)(?:\s*(?:₸|тг|тенге|kzt))?\b", message.lower())
    found = found or re.search(r"(\d+(?:[.,]\d{1,2})?)\s*(?:₸|тг|теңге(?:ге|ден)?|тенге|kzt)?\s*(?:дейін|аспасын)", message.lower())
    return float(found[1].replace(",", ".")) if found else None


def city(message):
    text = message.lower()
    return next((name for name, aliases in CITIES.items() if any(alias in text for alias in aliases)), None)


def city_stores(product, place):
    canonical = city(place) or place.lower()
    aliases = CITIES.get(canonical, (canonical,))
    return [s for s in product.get("stores", []) if any(alias in s.get("name", "").lower() for alias in aliases)]


def explicit_confirmation(message):
    text = message.lower().strip().rstrip(".!")
    patterns = [r"(?:да[, ]+)?добавь(?: в корзину)?(?:\s+\d+(?:\s*(?:шт\.?|штук|ед\.?))?)?",
                r"подтверждаю(?: добавление)?", r"добавляй", r"беру",
                r"иә[, ]+(?:қос|себетке сал|себетке қос)(?:\s+\d+\s*(?:дана)?)?",
                r"yes[, ]+add(?: it| them)?(?: to (?:the )?cart)?(?:\s+\d+\s*(?:pcs|pieces|units)?)?",
                r"i confirm(?: adding(?: (?:it|them))?(?: to (?:the )?cart)?)?"]
    return any(re.fullmatch(pattern, text) for pattern in patterns)


def sensitive(message):
    text = message.lower()
    if re.search(r"\b(?:cvv|cvc)\s*[:=]?\s*\d+", text):
        return True
    # An EAN/GTIN is a catalog identifier. Long digits alone are not evidence of card data.
    payment_context = re.search(r"(?:моя|номер|банк\w*)\s+карт|card\s*(?:number|details)|my card|карта\s*(?:нөмір|дерек)|төлем дерек", text)
    return bool(payment_context and re.search(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)", text))


def electrical_constraints(text):
    found = {}
    for key, pattern in (("current", r"(?<![\w.])(\d+(?:[.,]\d+)?)\s*(?:а|a|ампер|amp)(?!\w)"),
                         ("voltage", r"(?<![\w.])(\d+(?:[.,]\d+)?)\s*(?:в|v|вольт|volt)(?!\w)"),
                         ("poles", r"(?<!\w)(\d)\s*(?:p|р|полюс\w*|poles?|полюсті)(?!\w)")):
        match = re.search(pattern, text.lower())
        if match:
            found[key] = match[1].replace(",", ".")
    for word, value in NUMBER_WORDS.items():
        if re.search(r"\b" + word + r"\s+(?:полюс\w*|poles?|полюсті)\b", text.lower()):
            found["poles"] = str(value)
    dims = re.search(r"(\d+)\s*[xх×]\s*(\d+(?:[.,]\d+)?)", text.lower())
    if dims:
        found["cable_dimensions"] = f"{dims[1]}x{dims[2].replace(',', '.')}"
    return found


def canonical_query(message, family=None, constraints=None):
    query = message
    replacements = [(r"\b(?:circuit breakers?|breakers?)\b", "автомат"), (r"\b(?:cables?|wires?)\b", "кабель"),
                    (r"\b(?:lights?|lamps?|luminaires?)\b", "светильник"), (r"\b(?:article|sku)\b", "артикул"),
                    (r"\bажыратқыш\w*", "автомат"), (r"\bкабель\w*", "кабель")]
    for pattern, value in replacements:
        query = re.sub(pattern, value, query, flags=re.I)
    if family and not re.search(r"автомат|кабел|узо|rcd", query.lower()):
        query = ("автомат " if family == "breaker" else "кабель ") + query
    if constraints:
        # Rebuild parameter selection so corrected values replace, rather than contradict, old ones.
        base = "автомат" if family == "breaker" else "кабель" if family == "cable" else query
        params = [f"{constraints[k]}{unit}" for k, unit in (("current", "А"), ("poles", "P"), ("voltage", "В")) if k in constraints]
        if constraints.get("cable_dimensions"):
            params.append(constraints["cable_dimensions"])
        query = " ".join([base] + params)
    return query


def route(message, state=None):
    state, text = state or {}, message.lower().strip()
    plan = AgentPlan(quantity=quantity(message), budget=budget(message), city=city(message), constraints=electrical_constraints(message))
    plan.explicit_identifier = bool(re.search(r"\b(?:id|sku|артикул|article|ean|gtin|штрихкод)\b\s*[:#]?\s*[\w-]*\d|\b[\w]+[-_]\d{3,}\b", text)
                                    or re.fullmatch(r"\d{4,19}", text))
    plan.family = "breaker" if re.search(r"автомат|выключател|breaker|ажыратқыш", text) else "cable" if re.search(r"кабел|провод|cable|wire", text) else None
    plan.product_hint = plan.explicit_identifier or bool(plan.family or re.search(r"светильник|ламп|тауар|product|артикул|\bid\b", text))
    is_terms = bool(re.search(r"оплат|достав|самовывоз|возврат|вернут|обмен|регистрац|минимальн|партия|delivery|shipping|payment|returns?|refund|registration|minimum|төлем|жеткіз|қайтар|тіркел|ең аз", text))
    educational = bool(re.search(r"чем .*отлич|разниц|что такое|как работает|объясни|для чего|что значит|difference|what is|what are|how does|explain|means?|айырмаш|деген не|түсіндір|қалай жұмыс", text))
    compare = bool(re.search(r"сравни|сравнение|салыстыр|compare|comparison", text))
    if compare and not plan.explicit_identifier and not state.get("candidate_ids") and re.search(r"автомат|узо|дифавтомат|mcb|rcd|rcbo|breaker", text):
        educational = True
    cheaper = bool(plan.budget is not None or re.search(r"подешевле|дешевле|арзанырақ|арзан|cheaper|less expensive", text))
    if is_terms: plan.intents.append("terms")
    if educational: plan.intents.append("educational")
    if compare: plan.intents.append("compare")
    if cheaper: plan.intents.append("cheaper")
    if re.search(r"аналог|alternative|equivalent|ұқсас|балама", text): plan.intents.append("analogs")
    if re.search(r"сертифик|certificate|сәйкестік", text): plan.intents.append("certificate")
    if re.search(r"характерист|спецификац|specification|сипаттама|қасиет", text): plan.intents.append("specifications")
    electrical_property = bool(re.search(r"напряжен|полюс|номинальн.*ток|voltage|rated current|poles|кернеу|номинал.*ток", text))
    if electrical_property and "specifications" not in plan.intents: plan.intents.append("specifications")
    if re.search(r"наличи|остат|склад|stock|available|availability|қойма|қор|бар ма", text) or plan.city: plan.intents.append("stock")
    if re.search(r"цен[ау]|стоим|price|cost|баға|бағасы", text): plan.intents.append("price")
    if re.search(r"куп|подбер|нужен|нужно|хочу|добав|find|buy|need|select|таңда|керек|сатып", text) or plan.quantity is not None: plan.intents.append("selection")
    ordinal_words = {"перв": 0, "first": 0, "бірінші": 0,
                     "втор": 1, "second": 1, "екінші": 1,
                     "трет": 2, "треть": 2, "third": 2, "үшінші": 2}
    for word, index in ordinal_words.items():
        if re.search(r"\b" + word + r"\w*", text): plan.ordinal = index
    is_ref = bool(re.search(r"этот|этого|эти|его|него|these|those|this|that|its|осы|оның|екеу", text))
    plan.followup = not plan.explicit_identifier and bool(plan.ordinal is not None or is_ref or plan.city or plan.quantity is not None or cheaper or plan.constraints or
                                                        set(plan.intents) & {"certificate", "specifications", "stock", "price", "analogs", "compare"})
    selected_article = state.get("selected_article")
    same_article = bool(selected_article and re.search(r"(?<!\w)" + re.escape(selected_article.lower()) + r"(?!\w)", text))
    same_id = bool(state.get("product_id") and re.search(r"\bid\s*[:#]?\s*" + str(state["product_id"]) + r"\b", text))
    if (same_article or same_id) and not compare and len(re.findall(r"\b[\w]+[-_]\d{3,}\b", text)) <= 1:
        plan.followup = True
    product_followup = bool(state.get("product_id") and plan.followup and set(plan.intents) & {"stock", "price", "specifications", "certificate", "selection", "analogs", "cheaper"})
    concrete_selection = bool(plan.family and (plan.constraints or "selection" in plan.intents) and not educational)
    property_followup = product_followup and (is_ref or not educational)
    if property_followup and "educational" in plan.intents:
        plan.intents.remove("educational")
    if educational and not plan.explicit_identifier and not property_followup: plan.answer_kind = "educational"
    elif is_terms and not plan.explicit_identifier and not product_followup and not concrete_selection: plan.answer_kind = "knowledge"
    elif plan.product_hint or plan.followup or state.get("family"): plan.answer_kind = "product"
    for pattern, query in (
        (r"достав|самовывоз|delivery|shipping|жеткіз", "доставка самовывоз сроки"),
        (r"оплат|payment|төлем", "способы оплаты"),
        (r"возврат|вернут|обмен|returns?|refund|қайтар", "возврат обмен товара"),
        (r"минимальн|партия|minimum|ең аз", "минимальная партия кратность"),
        (r"регистрац|registration|тіркел", "регистрация личный кабинет"),
    ):
        if re.search(pattern, text): plan.knowledge_queries.append(query)
    plan.query = canonical_query(message)
    return plan
