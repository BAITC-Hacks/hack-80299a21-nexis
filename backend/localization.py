"""Presentation-only translations. Original catalog facts and authorization stay intact."""
import copy
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

LANGUAGES = ("ru", "kk", "en")


def normalize_language(value):
    value = str(value or "ru").lower().replace("_", "-").split("-")[0]
    return "kk" if value == "kz" else value if value in LANGUAGES else "ru"


# Each tuple is RU, KK, EN. Never translate product identifiers or numeric values.
TEXT = {
    "llm_unavailable_rules_used": ("Модель недоступна; ответ подготовлен по правилам и доступным источникам.", "Модель қолжетімсіз; жауап ережелер мен қолжетімді дереккөздер бойынша дайындалды.", "The model is unavailable; the response uses rules and available sources."),
    "request_deadline": ("Время обработки истекло. Доступны только уже проверенные результаты.", "Өңдеу уақыты аяқталды. Тек тексерілген нәтижелер көрсетілді.", "Processing timed out. Only already verified results are available."),
    "catalog_match_unavailable": ("Подходящий товар не удалось подтвердить в доступном каталоге.", "Қолжетімді каталогтан сәйкес тауарды растау мүмкін болмады.", "A matching product could not be verified in the available catalog."),
    "knowledge_unavailable": ("В базе знаний не найден подтверждённый ответ.", "Білім базасынан расталған жауап табылмады.", "No supported answer was found in the knowledge base."),
    "cheaper_match_unavailable": ("Подтверждённый более дешёвый вариант не найден.", "Расталған арзанырақ нұсқа табылмады.", "No verified cheaper alternative was found."),
    "analog_match_unavailable": ("Подтверждённый подходящий аналог не найден.", "Расталған сәйкес балама табылмады.", "No verified compatible alternative was found."),
    "source_unavailable": ("Один из источников временно недоступен.", "Дереккөздердің бірі уақытша қолжетімсіз.", "One of the sources is temporarily unavailable."),
    "tool_limit": ("Достигнут предел запросов к источникам. Уточните один вопрос.", "Дереккөздерге сұрау шегіне жетті. Бір сұрақты нақтылаңыз.", "The source request limit was reached. Please narrow the question."),
    "invalid_arguments": ("Не удалось уточнить параметры запроса к источнику.", "Дереккөз сұрауының параметрлерін нақтылау мүмкін болмады.", "The source request parameters could not be resolved."),
    "tool_not_allowed": ("Запрошенное действие недоступно этому ассистенту.", "Сұралған әрекет бұл көмекшіге қолжетімсіз.", "The requested action is not available to this assistant."),
    "invalid_product_id": ("Уточните идентификатор товара.", "Тауар идентификаторын нақтылаңыз.", "Please specify the product identifier."),
    "city_required": ("Укажите город для проверки складов.", "Қоймаларды тексеру үшін қаланы көрсетіңіз.", "Specify a city to check its warehouses."),
    "unavailable": ("Не удалось выполнить запрос. Попробуйте ещё раз.", "Сұрауды орындау мүмкін болмады. Қайталап көріңіз.", "The request could not be completed. Please try again."),
    "validation_error": ("Проверьте поля запроса и выбранный язык: ru, kk или en.", "Сұрау өрістерін және тілді тексеріңіз: ru, kk немесе en.", "Check the request fields and language: ru, kk or en."),
    "rate_limited": ("Слишком много запросов. Повторите через минуту.", "Сұраулар тым көп. Бір минуттан кейін қайталаңыз.", "Too many requests. Please try again in one minute."),
    "invalid_session": ("Сессия не найдена или истекла. Создайте новую сессию.", "Сессия табылмады немесе мерзімі аяқталды. Жаңа сессия ашыңыз.", "The session is missing or expired. Start a new session."),
    "session_mismatch": ("Идентификаторы сессии не совпадают.", "Сессия идентификаторлары сәйкес келмейді.", "Session identifiers do not match."),
    "expired_cart_link": ("Ссылка истекла. Получите новую ссылку в чате.", "Сілтеменің мерзімі аяқталды. Чаттан жаңа сілтеме алыңыз.", "This link has expired. Request a new cart link in the chat."),
    "invalid_quantity": ("Укажите целое положительное количество до 100000; для удаления используйте изменение корзины с количеством 0.", "100000-ға дейінгі оң бүтін санды көрсетіңіз; жою үшін себетті өзгерту кезінде 0 санын қолданыңыз.", "Enter a positive whole quantity up to 100000; use a cart change with quantity 0 to remove an item."),
    "catalog_unavailable": ("Не удалось проверить каталог, цену или остаток. Попробуйте позже.", "Каталогты, бағаны немесе қорды тексеру мүмкін болмады. Кейінірек қайталаңыз.", "The catalog, price or stock could not be verified. Please try later."),
    "price_unavailable": ("Цена требует уточнения у менеджера.", "Бағаны менеджерден нақтылау қажет.", "Please confirm the price with a manager."),
    "product_not_found": ("Товар не найден.", "Тауар табылмады.", "Product not found."),
    "insufficient_stock": ("Доступно для добавления не более {remaining} шт.", "Қосуға болатын ең көп саны: {remaining} дана.", "The maximum quantity available to add is {remaining}."),
    "packaging_mismatch": ("Минимальная партия: {minimum}; кратность: {multiple}.", "Ең аз партия: {minimum}; қаптама еселігі: {multiple}.", "Minimum quantity: {minimum}; order multiple: {multiple}."),
    "invalid_offer": ("Подтверждение не найдено, использовано или истекло. Выберите товар заново.", "Ұсыныс табылмады, қолданылған немесе мерзімі аяқталған. Тауарды қайта таңдаңыз.", "The offer is missing, used or expired. Select the product again."),
    "offer_mismatch": ("Товар или количество отличаются от предложения.", "Тауар немесе саны ұсынысқа сәйкес келмейді.", "The product or quantity differs from the offer."),
    "confirmation_required": ("Требуется явное подтверждение изменения корзины.", "Себетті өзгерту үшін нақты растау қажет.", "Explicit confirmation is required to change the cart."),
    "cart_item_not_found": ("Товара нет в корзине. Обновите её состояние.", "Тауар себетте жоқ. Себетті жаңартыңыз.", "This item is not in the cart. Refresh the cart."),
    "quantity_unchanged": ("Это количество уже установлено.", "Бұл сан бұрыннан орнатылған.", "This quantity is already set."),
    "cart_changed": ("Корзина изменилась. Обновите её и подтвердите новое предложение.", "Себет өзгерді. Оны жаңартып, жаңа ұсынысты растаңыз.", "The cart has changed. Refresh it and confirm a new offer."),
    "price_changed": ("Цена изменилась. Получите новое предложение и подтвердите его.", "Баға өзгерді. Жаңа ұсынысты алып, растаңыз.", "The price has changed. Request and confirm a new offer."),
    "unsupported_file": ("Поддерживаются PDF, TXT, DOCX, XLSX, XLS, JPEG, PNG, WEBP. Файл .doc сохраните как .docx.", "PDF, TXT, DOCX, XLSX, XLS, JPEG, PNG, WEBP қолданылады. .doc файлын .docx ретінде сақтаңыз.", "Supported: PDF, TXT, DOCX, XLSX, XLS, JPEG, PNG and WEBP. Convert .doc files to .docx."),
    "empty_file": ("Файл пуст.", "Файл бос.", "The file is empty."),
    "file_too_large": ("Файл превышает 15 МиБ или весь запрос превышает 16 МиБ.", "Файл 15 МиБ-тан немесе бүкіл сұрау 16 МиБ-тан асады.", "The file exceeds 15 MiB or the full request exceeds 16 MiB."),
    "file_signature_mismatch": ("Содержимое файла не соответствует расширению.", "Файл мазмұны кеңейтіміне сәйкес келмейді.", "The file contents do not match the extension."),
    "archive_too_large": ("Распакованное содержимое слишком велико.", "Ашылған архивтің көлемі тым үлкен.", "The uncompressed archive is too large."),
    "encrypted_document": ("Защищённые паролем файлы не поддерживаются.", "Құпиясөзбен қорғалған файлдар қолданылмайды.", "Password-protected documents are not supported."),
    "ocr_unavailable": ("Распознавание фото недоступно. Отправьте текстовую спецификацию.", "Суреттен мәтін тану қолжетімсіз. Мәтіндік спецификация жіберіңіз.", "Image recognition is unavailable. Please upload a text specification."),
    "ocr_languages_missing": ("В OCR отсутствуют языковые данные rus/eng/kaz.", "OCR жүйесінде rus/eng/kaz тілдері орнатылмаған.", "OCR language data for rus/eng/kaz are missing."),
    "ocr_timeout": ("Распознавание заняло слишком много времени. Отправьте меньший фрагмент.", "Тану уақыты аяқталды. Кішірек бөлігін жіберіңіз.", "Recognition timed out. Please upload a smaller section."),
    "invalid_text_encoding": ("TXT должен быть в UTF-8.", "TXT файлы UTF-8 кодтауында болуы керек.", "TXT files must use UTF-8 encoding."),
    "too_many_pages": ("В PDF больше 50 страниц.", "PDF файлында 50 беттен артық.", "The PDF exceeds 50 pages."),
    "too_many_scans": ("Разделите скан на файлы не более 10 страниц.", "Сканды 10 беттен аспайтын файлдарға бөліңіз.", "Split the scan into files of up to 10 scanned pages."),
    "image_too_large": ("Изображение или страница скана превышает 16 мегапикселей.", "Сурет немесе скан беті 16 мегапиксельден асады.", "The image or scan page exceeds 16 megapixels."),
    "text_too_large": ("Документ превышает лимит 100000 символов.", "Құжат 100000 таңбадан асады.", "The document exceeds the 100000-character limit."),
    "table_too_large": ("Таблица превышает 2000 строк или 100 столбцов.", "Кесте 2000 жолдан немесе 100 бағаннан асады.", "The spreadsheet exceeds 2000 rows or 100 columns."),
    "invalid_table_row": ("Проверьте кавычки и разделители в строках таблицы.", "Кесте жолдарындағы тырнақшалар мен бөлгіштерді тексеріңіз.", "Check quotation marks and delimiters in the table rows."),
    "too_many_rows": ("В спецификации больше 250 позиций. Разделите файл.", "Спецификацияда 250-ден артық позиция бар. Файлды бөліңіз.", "The specification exceeds 250 items. Split the file."),
    "unreadable_file": ("Файл повреждён или текст не удалось извлечь. Сохраните его заново.", "Файл бүлінген немесе мәтінді алу мүмкін болмады. Қайта сақтаңыз.", "The file is damaged or its text could not be extracted. Save it again."),
    "no_text": ("Читаемый текст не найден. Нужны отчётливые маркировка и артикул.", "Оқылатын мәтін табылмады. Анық таңбалау мен артикул қажет.", "No readable text was found. Clear markings and a product code are needed."),
    "no_product_rows": ("В файле не найдены строки спецификации.", "Файлдан спецификация жолдары табылмады.", "No specification rows were found in the file."),
    "processing_budget_exceeded": ("Лимит времени обработки; загрузите оставшиеся строки отдельным файлом.", "Өңдеу уақыты аяқталды; қалған жолдарды бөлек файлмен жүктеңіз.", "Processing timed out; upload the remaining rows as a separate file."),
    "quantity_required": ("Уточните целое положительное количество.", "Оң бүтін санмен мөлшерін нақтылаңыз.", "Specify a positive whole quantity."),
    "ambiguous_match": ("Нет однозначного совпадения; уточните артикул.", "Бірмәнді сәйкестік жоқ; артикулын нақтылаңыз.", "No unambiguous match; please specify the product code."),
    "quantity_unknown": ("Количество требует уточнения", "Санын нақтылау қажет", "Quantity needs clarification"),
    "stock_unknown": ("Остаток не проверен", "Қор тексерілмеген", "Stock not verified"),
    "in_stock": ("В наличии", "Қоймада бар", "In stock"),
    "partial_stock": ("Частично в наличии", "Ішінара бар", "Partially available"),
    "out_of_stock": ("Нет в наличии", "Қоймада жоқ", "Out of stock"),
    "estimate_summary": ("Найдено позиций: {count}. Известная часть сметы: {total} ₸. {completeness} Товары в корзину не добавлены.", "Табылған позициялар: {count}. Сметаның белгілі бөлігі: {total} ₸. {completeness} Тауарлар себетке қосылған жоқ.", "Matched items: {count}. Known estimate: {total} ₸. {completeness} No products were added to the cart."),
    "estimate_complete": ("Смета рассчитана по найденным ценам.", "Смета табылған бағалар бойынша есептелді.", "The estimate uses the matched prices."),
    "estimate_incomplete": ("Есть нераспознанные строки, количества или цены; итог неполный.", "Танылмаған жолдар, сандар немесе бағалар бар; қорытынды толық емес.", "Some rows, quantities or prices are unresolved; the total is incomplete."),
    "cart_added": ("✅ Товар добавлен в демонстрационную корзину.", "✅ Тауар демонстрациялық себетке қосылды.", "✅ The product was added to the demo cart."),
    "cart_changed_text": ("Количество «{name}» изменено: {quantity}.", "«{name}» саны өзгертілді: {quantity}.", "Quantity for “{name}” changed to {quantity}."),
    "cart_removed": ("«{name}» удалён из демонстрационной корзины.", "«{name}» демонстрациялық себеттен жойылды.", "“{name}” was removed from the demo cart."),
    "article": ("Артикул", "Артикул", "Product code"),
    "name": ("Наименование", "Атауы", "Name"),
    "quantity": ("Количество", "Саны", "Quantity"),
    "price": ("Цена", "Баға", "Price"),
    "sum": ("Сумма", "Сома", "Amount"),
    "added": ("Добавлено", "Қосылды", "Added"),
    "verified_stock": ("Проверенный остаток", "Тексерілген қор", "Verified stock"),
    "cart_count": ("Всего в корзине", "Себеттегі жалпы саны", "Total quantity in cart"),
    "open_cart": ("Открыть актуальную корзину", "Ағымдағы себетті ашу", "Open the current cart"),
    "cart_title": ("Демонстрационная корзина NEXIS", "NEXIS демонстрациялық себеті", "NEXIS demo cart"),
    "cart_notice": ("Текущее состояние сохранённой корзины. Товары не зарезервированы; заказ на ekt.kz не оформлен.", "Сақталған себеттің ағымдағы күйі. Тауарлар резервтелмеген; ekt.kz сайтында тапсырыс рәсімделмеген.", "The current saved cart. Products are not reserved and no order has been placed on ekt.kz."),
    "cart_empty": ("Корзина пуста", "Себет бос", "The cart is empty"),
    "total": ("Итого", "Барлығы", "Total"),
    "partner_cart_notice": ("Передача этой корзины на сайт партнёра пока не подключена.", "Бұл себетті серіктес сайтына жіберу әлі қосылмаған.", "Transfer of this cart to the partner website is not connected."),
    "partner_cart_open": ("Открыть отдельную корзину на ekt.kz", "ekt.kz сайтындағы бөлек себетті ашу", "Open the separate cart on ekt.kz"),
    "manual_handoff": ("Автоматическая передача в CRM не подключена. Выберите филиал на странице контактов; сообщение не отправлено.", "CRM-ге автоматты жіберу қосылмаған. Байланыс бетінен филиалды таңдаңыз; хабарлама жіберілген жоқ.", "Automatic CRM handoff is not connected. Choose a branch on the contacts page; no message has been sent."),
    "partner_cart_contract": ("Официальный контракт корзины и привязки сессии покупателя", "Себет пен сатып алушы сессиясын байланыстырудың ресми API шарты", "Official cart API contract and buyer session binding"),
    "partner_test_access": ("Тестовый доступ и правила идемпотентности", "Тестілік қолжетімділік және қайталанған сұраулар ережелері", "Test access and idempotency rules"),
    "partner_crm_contract": ("Контракт CRM для реальной передачи заявки", "Өтінішті нақты жіберуге арналған CRM шарты", "CRM contract for submitting a real request"),
    "analogs_found": ("Проверены характеристики и остатки.", "Сипаттамалар мен қор тексерілді.", "Specifications and stock have been checked."),
    "analogs_missing": ("Подтверждённый аналог в доступной выборке не найден; обратитесь к менеджеру.", "Қолжетімді таңдамада расталған балама табылмады; менеджерге хабарласыңыз.", "No verified alternative was found in the available catalog; contact a manager."),
    "current_conflict": ("Ток в названии ({name_current} А) расходится со свойством каталога ({property_current} А). Требуется уточнение.", "Атауындағы ток ({name_current} А) каталог сипаттамасына ({property_current} А) сәйкес келмейді. Нақтылау қажет.", "Current in the name ({name_current} A) differs from the catalog property ({property_current} A). Clarification is required."),
    "data_warning": ("В данных каталога есть расхождение; уточните характеристики у менеджера.", "Каталог деректерінде қайшылық бар; сипаттамаларды менеджерден нақтылаңыз.", "The catalog contains conflicting data; confirm the specifications with a manager."),
    "installation_note": ("Перед монтажом проверьте габариты и условия применения по документации производителя.", "Орнату алдында өндіруші құжаттамасынан өлшемдері мен қолдану шарттарын тексеріңіз.", "Before installation, check dimensions and application conditions in the manufacturer's documentation."),
}

SPEC_LABELS = {
    "OBYEM": ("Тип изделия", "Өнім түрі", "Product type"),
    "KOLICHESTVO_POLYUSOV": ("Число полюсов", "Полюстер саны", "Poles"),
    "NOMINALNYY_TOK": ("Номинальный ток", "Номиналды ток", "Rated current"),
    "NOMINALNOE_NAPRYAZHENIE": ("Напряжение", "Кернеу", "Voltage"),
    "NOMINALNAYA_OTKLYUCHAYUSHCHAYA_SPOSOBNOST": ("Отключающая способность", "Ажырату қабілеті", "Breaking capacity"),
    "TIP_USTANOVKI": ("Монтаж", "Орнату", "Mounting"),
    "TORGOVAYA_MARKA": ("Марка", "Бренд", "Brand"),
    "SECHENIE": ("Сечение", "Қима", "Cross-section"),
    "KOLICHESTVO_ZHIL": ("Число жил", "Талшықтар саны", "Cores"),
    "KHARAKTERISTIKA_SRABATYVANIYA": ("Характеристика", "Іске қосылу сипаттамасы", "Trip curve"),
    "NOMINALNYY_OTKLYUCHAYUSHCHIY_DIFFERENTSIALNYY_TOK": ("Дифференциальный ток", "Дифференциалды ток", "Residual current"),
    "current": ("Ток", "Ток", "Current"), "poles": ("Полюса", "Полюстер", "Poles"),
    "voltage": ("Напряжение", "Кернеу", "Voltage"),
    "breaking_capacity": ("Отключающая способность", "Ажырату қабілеті", "Breaking capacity"),
    "curve": ("Характеристика", "Іске қосылу сипаттамасы", "Trip curve"),
    "leakage_current": ("Дифференциальный ток", "Дифференциалды ток", "Residual current"),
    "cores": ("Число жил", "Талшықтар саны", "Cores"), "section": ("Сечение", "Қима", "Cross-section"),
    "cable_type": ("Тип кабеля", "Кабель түрі", "Cable type"),
}

CATEGORIES = {
    "account": ("Личный кабинет", "Жеке кабинет", "Account"),
    "assistant": ("Возможности ассистента", "Көмекші мүмкіндіктері", "Assistant capabilities"),
    "cart": ("Корзина", "Себет", "Cart"), "catalog": ("Каталог", "Каталог", "Catalog"),
    "certificates": ("Сертификаты", "Сертификаттар", "Certificates"),
    "contacts": ("Контакты", "Байланыс", "Contacts"), "delivery": ("Доставка", "Жеткізу", "Delivery"),
    "files": ("Файлы и спецификации", "Файлдар мен спецификациялар", "Files and specifications"),
    "payment": ("Оплата", "Төлем", "Payment"), "price": ("Цены", "Бағалар", "Prices"),
    "privacy": ("Конфиденциальность", "Құпиялық", "Privacy"),
    "quantity": ("Количество и упаковка", "Саны мен қаптамасы", "Quantity and packaging"),
    "returns": ("Возврат", "Қайтару", "Returns"), "selection": ("Подбор", "Таңдау", "Selection"),
    "stock": ("Наличие", "Қойма қоры", "Stock"), "technical": ("Технические вопросы", "Техникалық сұрақтар", "Technical questions"),
    "warranty": ("Гарантия", "Кепілдік", "Warranty"),
}


def category_title(category, language="ru"):
    return CATEGORIES.get(category, ("Справка", "Анықтама", "Help"))[LANGUAGES.index(normalize_language(language))]


def tr(key, language="ru", **params):
    template = TEXT.get(key, TEXT["unavailable"])[LANGUAGES.index(normalize_language(language))]
    try:
        return template.format(**params)
    except (KeyError, ValueError):
        return TEXT["unavailable"][LANGUAGES.index(normalize_language(language))]


def localize_error(code, language="ru", fallback="", params=None):
    if code in TEXT and normalize_language(language) == "ru" and fallback:
        return fallback
    return tr(code, language, **(params or {}))


def localized_url(url, language="ru"):
    if not url:
        return url
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["language"] = normalize_language(language)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def localize_warnings(warnings, language):
    if normalize_language(language) == "ru":
        return list(warnings or [])
    output = []
    for warning in warnings or []:
        if warning in TEXT:
            output.append(tr(warning, language))
            continue
        match = re.search(r"Ток в названии \(([^ ]+) А\).*каталога \(([^ ]+) А\)", str(warning))
        output.append(tr("current_conflict", language, name_current=match[1], property_current=match[2])
                      if match else tr("data_warning", language))
    return output


def localize_product(product, language="ru"):
    result = copy.deepcopy(product)
    if result.get("display_language") == normalize_language(language):
        return result
    index = LANGUAGES.index(normalize_language(language))
    unit = str(result.get("unit") or "")
    if unit:
        key = unit.lower().strip().rstrip(".")
        result["unit_display"] = (("шт.", "дана", "pcs")[index] if key in {"шт", "штук", "pcs", "pc", "pieces", "дана"}
                                  else ("м", "м", "m")[index] if key in {"м", "m", "метр", "метры", "metres", "meters"} else unit)
    for field in ("specifications", "matched_parameters"):
        for item in result.get(field, []) or []:
            key = item.get("key") or next((key for key, labels in SPEC_LABELS.items() if labels[0] == item.get("name")), None)
            if key in SPEC_LABELS:
                item.update(key=key, name=SPEC_LABELS[key][index])
    if result.get("matched_parameters"):
        result["rationale"] = "; ".join(f"{p['name']}: {p['alternative']}" for p in result["matched_parameters"])
    if result.get("recommendation_note"):
        result["recommendation_note"] = tr("installation_note", language)
    if "data_quality_warnings" in result:
        result["data_quality_warnings"] = localize_warnings(result["data_quality_warnings"], language)
    if "analogs" in result:
        result["analogs"] = [localize_product(item, language) for item in result["analogs"]]
    if result.get("analog"):
        result["analog"] = localize_product(result["analog"], language)
    result["display_language"] = normalize_language(language)
    return result


def localize_cart_result(result, language="ru"):
    result = copy.deepcopy(result)
    result["answer_language"] = normalize_language(language)
    for key in ("cart_url", "checkout_url"):
        if result.get(key):
            result[key] = localized_url(result[key], language)
    result = localize_product(result, language)
    summary = result.get("cart_confirmation")
    if summary:
        summary["cart_url"] = result.get("cart_url") or localized_url(summary.get("cart_url"), language)
        if summary.get("operation") == "set_quantity":
            key = "cart_changed_text" if summary["quantity"] else "cart_removed"
            answer = tr(key, language, name=summary["product_name"], quantity=summary["quantity"])
        else:
            answer = (f"{tr('cart_added', language)}\n\n📦 {summary['product_name']}\n"
                      f"🔢 {tr('article', language)}: {summary['article']}\n"
                      f"💰 {tr('price', language)}: {summary['price']:,.2f} ₸\n"
                      f"📊 {tr('added', language)}: {summary['quantity_added']} · "
                      f"{tr('verified_stock', language)}: {summary['stock_available']}\n"
                      f"🛒 {tr('cart_count', language)}: {summary['cart_items_count']}")
        answer += f"\n🔗 [{tr('open_cart', language)}]({summary['cart_url']})"
        result.update(answer=answer, message=answer)
    return result


def localize_estimate(estimate, language="ru"):
    result = copy.deepcopy(estimate)
    status_keys = {TEXT[key][0]: key for key in ("quantity_unknown", "stock_unknown", "in_stock", "partial_stock", "out_of_stock", "ambiguous_match", "processing_budget_exceeded")}
    for collection in ("matched_items", "unmatched_items"):
        rows = []
        for row in result.get(collection, []):
            row = localize_product(row, language)
            code = row.get("status_code") or status_keys.get(row.get("status"), "ambiguous_match")
            row.update(status_code=code, status=tr(code, language))
            if row.get("quantity_warning"):
                row["quantity_warning"] = tr("quantity_required", language)
            rows.append(row)
        result[collection] = rows
    result["warning_codes"] = list(result.get("warnings", []))
    result["warnings"] = [tr(code, language) for code in result.get("warnings", [])]
    result["summary_text"] = tr("estimate_summary", language, count=result["total_positions_found"],
                                total=f"{result['total_estimate_kzt']:,.2f}",
                                completeness=tr("estimate_complete" if result["estimate_complete"] else "estimate_incomplete", language))
    result["answer_language"] = normalize_language(language)
    return result
