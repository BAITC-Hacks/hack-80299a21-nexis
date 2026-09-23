"""72 named scenarios: 24 equivalent tasks in each supported language.

These are a regression/development set, not an independent held-out quality benchmark.
Catalog facts are synthetic and fixed; wording and multi-turn behavior are explicit.
"""


QUESTIONS = {
    "greeting": ("Привет", "Сәлем", "Hello"),
    "specifications": ("TEST-1001 характеристики", "TEST-1001 сипаттамалары", "TEST-1001 specifications"),
    "certificate": ("TEST-1001 сертификат", "TEST-1001 сертификат", "TEST-1001 certificate"),
    "city": ("А в Астане?", "Астанада бар ма?", "Is it in stock in Astana?"),
    "quantity_number": ("2 шт", "2 дана", "2 pieces"),
    "quantity_words": ("Нужно пять", "Бес дана керек", "I need five"),
    "quantity_zero": ("0 шт", "0 дана", "0 pieces"),
    "quantity_fraction": ("1.5 шт", "1.5 дана", "1.5 pieces"),
    "quantity_excess": ("6 шт", "6 дана", "6 pieces"),
    "confirm": ("Да, добавь", "Иә, қос", "Yes, add"),
    "quoted_confirmation": ("«Да, добавь»", "«Иә, қос»", "“Yes, add”"),
    "ordinal": ("Второй, 2 шт", "Екінші, 2 дана", "The second one, 2 pieces"),
    "compare": ("Сравни TEST-1001 и TEST-1003", "TEST-1001 және TEST-1003 салыстыр", "Compare TEST-1001 and TEST-1003"),
    "clarify": ("Нужно 2 автомата", "Автомат керек, 2 дана", "I need 2 breakers"),
    "vague": ("Нужен автомат", "Автомат керек", "I need a circuit breaker"),
    "terms": ("Условия оплаты и доставки", "Төлем және жеткізу шарттары", "Payment and delivery terms"),
    "returns": ("Как вернуть кабель?", "Кабельді қалай қайтаруға болады?", "How can I return a cable?"),
    "educational": ("Чем автомат отличается от УЗО?", "Автомат пен УЗО айырмашылығы қандай?", "What is the difference between a circuit breaker and an RCD?"),
    "unknown": ("Расскажи о космических марсианах", "Марстағы тіршілік туралы айтып бер", "Tell me about Martian civilizations"),
    "barcode": ("Штрихкод 3414970344526", "Штрихкод 3414970344526", "EAN 3414970344526"),
}


def build_cases():
    cases = []
    for index, lang in enumerate(("ru", "kk", "en")):
        def q(key): return QUESTIONS[key][index]
        def turn(message, **expect): return {"message": message, "expect": expect}
        def case(name, turns, setup=None):
            cases.append({"id": f"{lang}.{name}", "language": lang, "turns": turns, "setup": setup or {}})
        case("greeting", [turn(q("greeting"), no_sources=True, no_offer=True)])
        case("exact_product", [turn("TEST-1001", sources=[1001], pending_quantity=1, stock=5, price=1000)])
        case("specifications", [turn(q("specifications"), sources=[1001], no_offer=True)])
        case("certificate", [turn(q("certificate"), sources=[1001], contains="https://ekt.kz/test-certificate.pdf", no_offer=True)])
        case("zero_stock_analog", [turn("TEST-1002", sources=[1002], analogs=[1001], pending_product=1001)])
        case("city_followup", [turn("TEST-1001"), turn(q("city"), sources=[1001], city="астана", no_offer=True)])
        case("quantity_number", [turn("TEST-1001"), turn(q("quantity_number"), pending_quantity=2, updated=False)])
        case("quantity_words", [turn("TEST-1001"), turn(q("quantity_words"), pending_quantity=5, updated=False)])
        case("quantity_zero", [turn("TEST-1001"), turn(q("quantity_zero"), warning="invalid_quantity", no_offer=True)])
        case("quantity_fraction", [turn("TEST-1001"), turn(q("quantity_fraction"), warning="invalid_quantity", no_offer=True)])
        case("quantity_excess", [turn("TEST-1001"), turn(q("quantity_excess"), warning="insufficient_stock", no_offer=True)])
        case("missing_offer", [turn(q("confirm"), updated=False, no_offer=True)])
        case("confirmation", [turn("TEST-1001"), turn(q("confirm"), updated=True, cart_count=1)])
        case("quoted_not_consent", [turn("TEST-1001"), turn(q("quoted_confirmation"), updated=False), turn(q("confirm"), updated=False, cart_count=0)])
        case("confirmation_replay", [turn("TEST-1001"), turn(q("confirm"), updated=True), turn(q("confirm"), updated=False, cart_count=1)])
        case("ordinal_selection", [turn(q("compare")), turn(q("ordinal"), pending_product=1003, pending_quantity=2)])
        case("product_comparison", [turn(q("compare"), sources=[1001, 1003], no_offer=True)])
        case("quantity_not_current", [turn(q("clarify"), clarification="electrical_parameters", no_sources=True, no_offer=True)])
        case("parameter_followup", [turn(q("vague"), clarification="electrical_parameters"), turn("16А 3P 400В", sources=[1001, 1002], no_offer=True)])
        case("purchase_terms", [turn(q("terms"), knowledge=True, no_sources=True, no_offer=True)])
        case("return_cable", [turn(q("returns"), knowledge=True, no_sources=True, no_offer=True)])
        case("technical_explanation", [turn(q("educational"), knowledge=True, no_sources=True, no_offer=True)])
        case("unknown_topic", [turn(q("unknown"), warning="knowledge_unavailable", no_sources=True, no_offer=True)])
        case("barcode_not_payment", [turn(q("barcode"), sources=[1001], stock=5)], setup={"barcode": "3414970344526"})
    return cases


CASES = build_cases()
