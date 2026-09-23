"""Small, versioned retrieval corpus with explicit provenance."""
import re

VERIFIED_AT = "2026-09-23"
TERMS_URL = "https://ekt.kz/checkout-delivery/"
CONTACTS_URL = "https://ekt.kz/about/contacts/"


def article(identifier, category, title, keywords, content, source=TERMS_URL, status="verified_public_page", kk=""):
    return {"id": identifier, "category": category, "title": title, "keywords": keywords,
            "content": content, "content_kk": kk, "source_url": source,
            "verified_at": VERIFIED_AT, "verification_status": status}


KB_ARTICLES = [
    article("payment", "payment", "Оплата и счета", ["оплат", "счет", "ндс", "юрлиц", "касса", "карт", "төлем", "шот", "kaspi"],
            "Частным покупателям доступны онлайн-оплата картой, наличные при получении и оплата в торговом зале. "
            "Юрлица могут оплатить выставленный счёт переводом либо наличными при самовывозе. "
            "Ставку НДС, рассрочку и условия конкретного счёта уточните у менеджера. Платёжные данные в чат не отправляйте.",
            kk="Жеке тұлғалар карта арқылы онлайн немесе тауарды алғанда қолма-қол төлей алады. Заңды тұлғалар шот бойынша аударым жасай алады. ҚҚС пен нақты шот шарттарын менеджерден нақтылаңыз. Карта деректерін чатқа жібермеңіз."),
    article("delivery", "delivery", "Доставка и самовывоз", ["достав", "самовывоз", "срок", "курьер", "жеткіз", "алып кет"],
            "Согласованная доставка по Алматы указана в пределах 48 часов; возможен самовывоз. "
            "Срок и стоимость отправки в другие города зависят от адреса, массы и объёма заказа и согласуются с менеджером. "
            "На странице есть расходящиеся пороги бесплатной доставки, поэтому точную стоимость нужно подтвердить.",
            kk="Алматыда келісілген жеткізу мерзімі 48 сағатқа дейін деп көрсетілген. Басқа қалаларға жеткізу құны мен мерзімін менеджермен келісу қажет. Өздігінен алып кетуге болады."),
    article("minimum_order", "quantity", "Минимальная партия и кратность", ["миним", "партия", "кратност", "количеств", "саны", "ең аз"],
            "Минимальная партия и кратность проверяются по полям конкретного товара в API. "
            "Универсальное правило «всё от одной штуки» не подтверждено. Укажите артикул, чтобы проверить упаковку.",
            source="https://ekt.kz/api/products", status="product_api_required",
            kk="Ең аз тапсырыс саны мен қаптама еселігі нақты тауардың API деректерімен тексеріледі. Артикулын көрсетіңіз."),
    article("certificates", "certificates", "Сертификаты конкретного товара", ["сертифик", "паспорт", "гост", "тр тс", "гарант", "сәйкест"],
            "Укажите артикул. Ассистент выдаёт ссылку на сертификат только при её наличии в карточке API. "
            "Отсутствие ссылки не доказывает отсутствие сертификата: запросите документ у менеджера.",
            source="https://ekt.kz/api/products", status="product_api_required",
            kk="Артикулын көрсетіңіз. Сертификат сілтемесі API-де бар болса ғана беріледі. Сілтеме болмаса, құжатты менеджерден сұраңыз."),
    article("contacts", "contacts", "Связь с менеджером", ["менедж", "оператор", "человек", "контакт", "инженер", "байланыс"],
            "Выберите город на официальной странице контактов ekt.kz. В прототипе нет соединения с CRM: обращение автоматически не отправляется.",
            source=CONTACTS_URL, kk="ekt.kz байланыс бетінде қалаңызды таңдаңыз. Бұл прототип өтінішті CRM-ге автоматты түрде жібермейді."),
    article("registration", "account", "Регистрация и возврат", ["регистрац", "кабинет", "бин", "возврат", "обмен", "тіркел", "қайтар"],
            "Используйте раздел личного кабинета на ekt.kz; форму регистрации выбирают для физического или юридического лица. "
            "Индивидуальные условия возврата и комплект документов уточните у выбранного филиала.",
            source="https://ekt.kz/about/information/",
            kk="ekt.kz жеке кабинет бөлімін пайдаланыңыз. Тіркелу түрін жеке немесе заңды тұлға ретінде таңдаңыз. Қайтару шарттарын филиалдан нақтылаңыз."),
]


def search_knowledge_base(query, limit=3):
    words = re.findall(r"[\w]+", str(query).lower())
    scored = []
    for item in KB_ARTICLES:
        score = sum(1 for word in words if len(word) > 2 and any(
            word.startswith(stem) or stem.startswith(word) for stem in item["keywords"]))
        if score:
            scored.append((score, item))
    return [dict(item) for _, item in sorted(scored, key=lambda row: row[0], reverse=True)[:limit]]


def source_metadata(item):
    return {key: item[key] for key in ("id", "title", "source_url", "verified_at", "verification_status")}


def purchase_terms():
    selected = [item for item in KB_ARTICLES if item["id"] in {"payment", "delivery", "minimum_order"}]
    return {"articles": selected, "sources": [source_metadata(item) for item in selected],
            "payment": [selected[0]["content"]], "delivery": [selected[1]["content"]],
            "minimum_order": selected[2]["content"]}
