import { mountChipMascot } from './mountChipMascot.tsx';

const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api').replace(new RegExp('/+$'), '');
const CHECKOUT_FALLBACK = 'https://ekt.kz/personal/cart/';
const SESSION_KEY = 'ekt-widget-session';
const DEMO_CART_KEY = 'ekt-widget-demo-cart';
const MAX_FILE_SIZE = 15 * 1024 * 1024;
const LANGUAGE_KEY = 'ekt-widget-language';
const copy = {
  ru: {
    cart: 'Корзина', cartAria: 'Открыть корзину, товаров: ', emptyCart: 'Корзина пока пуста', cartTitle: 'Корзина', closeCart: 'Закрыть корзину', unitsShort: 'ед.',
    itemCount: (count) => count + ' ' + (count === 1 ? 'товар' : count < 5 ? 'товара' : 'товаров'),
    quantity: 'Количество', remove: 'Удалить товар', stockLabel: 'Остаток', total: 'Итого',
    checkout: 'Оформить заказ', demoOrder: 'Демонстрационный заказ, без оплаты', orderSuccess: 'Тестовый заказ успешно создан.',
    emptyTitle: 'В корзине пока пусто', emptyCopy: 'Добавьте подходящий товар из чата — здесь появятся позиции и итоговая сумма.',
    freeShippingNeeded: (amount) => 'До бесплатной доставки по РК осталось ' + amount + ' ₸ (бесплатно от 50 000 ₸)',
    freeShippingReached: 'Бесплатная доставка по РК доступна для этой корзины.',
    shippingProgress: 'Прогресс бесплатной доставки',
    cartLimit: 'На складе доступно только', cartLimitSuffix: 'ед.', cartFailure: 'Не удалось обновить корзину. Попробуйте ещё раз.',
    certificateDownloaded: 'Скачан демонстрационный PDF, не официальный сертификат.',
    inStock: 'в наличии', stockEmpty: 'Нет в наличии', article: 'Артикул', quantityLabel: 'Количество',
    quantityDown: 'Уменьшить количество', quantityUp: 'Увеличить количество', analogTitle: 'Подходящий аналог',
    demoStock: 'в демо-остатке', unknownPrice: 'Цена уточняется', unknownSpecs: 'Характеристики уточняются',
    cableName: 'Кабель ВВГнг(А)-LS 3×2,5', legrandName: 'Legrand DRX250, 3P, 160 A', analogName: 'Автоматический выключатель CHINT eB, 3P, 160 A',
    analogRationale: 'Совпадают параметры 3P, 160 A и 4,5 кА; в демонстрационном сценарии совместимость подтверждена по ГОСТ.',
    cableSpecs: ['3 жилы', '2,5 мм²', 'нг(А)-LS'], analogSpecs: ['3P', '160 A', '4,5 кА'], sourceSpecs: ['3P', '160 A', '4,5 кА'],
    meterUnit: 'м', pieceUnit: 'шт.', stockUnavailable: 'Доступного остатка для этой позиции больше нет.',
    stockMax: (count, unit) => 'Можно добавить не более ' + count + ' ' + unit + '.', serverCartError: 'Не удалось обновить корзину на сервере.',
    demoResponse: 'Демо-ответ · синтетические данные',
    fallbackAnswer: 'В демо-каталоге не нашлось точного совпадения. Уточните артикул или параметры — проверю позицию и совместимость.',
    fallbackSteps: ['Разбираю параметры запроса', 'Ищу совпадения в каталоге', 'Проверяю наличие доступных позиций'],
    typeLabels: { search: 'поиск', catalog: 'каталог', stock: 'остаток', analogs: 'аналог', delivery: 'доставка', check: 'проверка', intent: 'запрос' },
    assistant: 'ChipAI — ekt.kz консультант', launcher: 'ИИ-консультант', online: 'Онлайн', role: 'консультант ekt.kz',
    catalogHelp: 'Помощь по каталогу', replyTime: 'Обычно отвечаем за минуту',
    welcomeKicker: 'Рады помочь', welcome: 'Здравствуйте! Я помогу найти товар, проверить наличие, подобрать аналог и посмотреть документы.',
    welcomeHint: 'Напишите артикул или опишите задачу своими словами.',
    prompts: ['Кабель ВВГнг 3х2.5', 'Аналог Legrand 160A', 'Условия доставки и опт'],
    promptQueries: ['Кабель ВВГнг 3х2.5', 'Аналог Legrand 160A', 'Условия доставки и опт'],
    placeholder: 'Напишите, что нужно найти…', footer: 'Ассистент ekt.kz', demo: 'Демо-данные каталога',
    add: '✓ Добавить в корзину', noStock: 'Нет в наличии', adding: 'Добавляем…',
    languageToggle: 'Переключить язык: RU, KZ или EN',
    success: '✓ Товар добавлен в корзину!', cartAdded: (count) => '✓ Добавлено: ' + count, checkoutLink: 'Перейти к оформлению заказа',
    reasoning: 'Ход рассуждения модели', stepCount: (count) => count + ' ' + (count === 1 ? 'шаг' : count < 5 ? 'шага' : 'шагов'), certificateLink: '📄 Сертификат соответствия ГОСТ (PDF)',
    cableAnswer: 'Нашёл кабель ВВГнг 3×2,5: он есть в наличии. Проверьте метраж и подтвердите добавление кнопкой в карточке.',
    cableSteps: ['Поиск кабеля ВВГнг 3×2,5 по каталогу', 'Проверка остатка: 1250 м в наличии', 'Проверка характеристик и сертификата ГОСТ'],
    analogAnswer: 'Позиция Legrand отсутствует на складе, но мы подобрали 100% совместимый аналог по ГОСТ.',
    analogSteps: ['Поиск Legrand DRX250 160A', 'Остаток Legrand: 0', 'Поиск сертифицированного аналога: 3P, 160A, 4.5 кА', 'Найден CHINT eB с совпадающими параметрами'],
    deliveryTitle: 'Доставка и оптовые условия', deliveryFree: 'Бесплатная доставка по РК',
    deliveryPickup: 'Самовывоз', deliveryPickupText: 'Астана и Алматы', deliveryPayment: 'Оплата для юридических лиц',
    deliveryPaymentText: 'Безналичный расчёт', deliverySupport: 'Единая справочная линия',
    deliveryAnswer: 'Собрал основные условия покупки. Точную доступность и сроки подтвердит менеджер при оформлении.',
    deliverySteps: ['Проверка правил доставки по РК', 'Проверка оптовых и безналичных условий', 'Готовлю краткую сводку для клиента'],
    orderGuard: 'Корзина изменяется только после нажатия кнопки подтверждения.',
    fileResponse: 'Вложение выбрано. В этой демонстрации файл не отправляется на сервер; подключите API загрузки, чтобы анализировать его содержимое.',
    stockError: 'Недостаточно остатка для указанного количества.',
    steps: ['Поиск позиции в каталоге', 'Проверка остатка: 0', 'Подбор доступного аналога'],
  },
  kz: {
    cart: 'Себет', cartAria: 'Себетті ашу, тауар саны: ', emptyCart: 'Себет әзірше бос', cartTitle: 'Себет', closeCart: 'Себетті жабу', unitsShort: 'дана',
    itemCount: (count) => count + ' тауар', quantity: 'Саны', remove: 'Тауарды жою', stockLabel: 'Қоймада', total: 'Барлығы',
    checkout: 'Тапсырысты рәсімдеу', demoOrder: 'Төлемсіз демонстрациялық тапсырыс', orderSuccess: 'Тестілік тапсырыс сәтті жасалды.',
    emptyTitle: 'Себет әзірше бос', emptyCopy: 'Чаттан қажетті тауарды қосыңыз — мұнда позициялар мен жалпы сома көрсетіледі.',
    freeShippingNeeded: (amount) => 'ҚР бойынша тегін жеткізуге ' + amount + ' ₸ қалды (50 000 ₸-ден бастап тегін)',
    freeShippingReached: 'Бұл себетке ҚР бойынша жеткізу тегін.',
    shippingProgress: 'Тегін жеткізу прогресі',
    cartLimit: 'Қоймада қолжетімді саны:', cartLimitSuffix: 'дана', cartFailure: 'Себетті жаңарту мүмкін болмады. Қайталап көріңіз.',
    certificateDownloaded: 'Демонстрациялық PDF жүктелді. Бұл ресми сертификат емес.',
    inStock: 'қоймада бар', stockEmpty: 'Қоймада жоқ', article: 'Артикул', quantityLabel: 'Саны',
    quantityDown: 'Санын азайту', quantityUp: 'Санын арттыру', analogTitle: 'Ұсынылатын балама',
    demoStock: 'демо қалдықта', unknownPrice: 'Бағасы нақтыланады', unknownSpecs: 'Сипаттамалары нақтыланады',
    cableName: 'ВВГнг(А)-LS 3×2,5 кабелі', legrandName: 'Legrand DRX250, 3P, 160 A', analogName: 'CHINT eB автоматты ажыратқышы, 3P, 160 A',
    analogRationale: '3P, 160 A және 4,5 кА параметрлері сәйкес; демонстрациялық сценарийде ГОСТ бойынша үйлесімділігі расталған.',
    cableSpecs: ['3 өзек', '2,5 мм²', 'нг(А)-LS'], analogSpecs: ['3P', '160 A', '4,5 кА'], sourceSpecs: ['3P', '160 A', '4,5 кА'],
    meterUnit: 'м', pieceUnit: 'дана', stockUnavailable: 'Бұл тауардың қолжетімді қалдығы жоқ.',
    stockMax: (count, unit) => 'Ең көбі ' + count + ' ' + unit + ' қосуға болады.', serverCartError: 'Себетті серверде жаңарту мүмкін болмады.',
    demoResponse: 'Демо жауап · синтетикалық деректер',
    fallbackAnswer: 'Демо каталогтан дәл сәйкес тауар табылмады. Артикулды немесе параметрлерді нақтылаңыз — позиция мен үйлесімділікті тексеремін.',
    fallbackSteps: ['Сұрау параметрлерін талдау', 'Каталогтан сәйкес тауар іздеу', 'Қолжетімді тауарлардың қалдығын тексеру'],
    typeLabels: { search: 'іздеу', catalog: 'каталог', stock: 'қалдық', analogs: 'балама', delivery: 'жеткізу', check: 'тексеру', intent: 'сұрау' },
    assistant: 'ChipAI — ekt.kz кеңесшісі', launcher: 'EKT кеңесшісі', online: 'Желіде', role: 'ekt.kz кеңесшісі',
    catalogHelp: 'Каталог бойынша көмек', replyTime: 'Әдетте бір минутта жауап береміз',
    welcomeKicker: 'Көмектесуге дайынмын', welcome: 'Сәлеметсіз бе! Тауарды табуға, қоймадағы қалдығын тексеруге, баламасын таңдауға және құжаттарын қарауға көмектесемін.',
    welcomeHint: 'Артикулды жазыңыз немесе тапсырманы өз сөзіңізбен сипаттаңыз.',
    prompts: ['Кабель ВВГнг 3х2.5', 'Legrand 160A баламасы', 'Жеткізу және көтерме шарттары'],
    promptQueries: ['Кабель ВВГнг 3х2.5', 'Legrand 160A баламасы', 'Жеткізу және көтерме шарттары'],
    placeholder: 'Не табу керегін жазыңыз…', footer: 'ekt.kz кеңесшісі', demo: 'Каталогтың демо деректері',
    add: '✓ Себетке қосу', noStock: 'Қоймада жоқ', adding: 'Қосылуда…',
    languageToggle: 'Интерфейс тілін ауыстыру: RU, KZ немесе EN',
    success: '✓ Тауар себетке қосылды!', cartAdded: (count) => '✓ ' + count + ' тауар себетке қосылды', checkoutLink: 'Тапсырысты рәсімдеуге өту',
    reasoning: 'Модельдің іздеу қадамдары', stepCount: (count) => count + ' қадам', certificateLink: '📄 ГОСТ сәйкестік сертификаты (PDF)',
    cableAnswer: 'ВВГнг 3×2,5 кабелі табылды және қоймада бар. Ұзындығын тексеріп, карточкадағы батырмамен қосуды растаңыз.',
    cableSteps: ['ВВГнг 3×2,5 кабелін каталогтан іздеу', 'Қойма қалдығын тексеру: 1250 м бар', 'Сипаттамалар мен ГОСТ сертификатын тексеру'],
    analogAnswer: 'Legrand тауары қоймада жоқ, бірақ ГОСТ бойынша 100% үйлесімді баламасын таңдадық.',
    analogSteps: ['Legrand DRX250 160A іздеу', 'Legrand қалдығы: 0', 'Сертификатталған баламаны іздеу: 3P, 160A, 4.5 кА', 'Сипаттамалары сәйкес CHINT eB табылды'],
    deliveryTitle: 'Жеткізу және көтерме шарттар', deliveryFree: 'ҚР бойынша тегін жеткізу',
    deliveryPickup: 'Өзі алып кету', deliveryPickupText: 'Астана және Алматы', deliveryPayment: 'Заңды тұлғаларға төлем',
    deliveryPaymentText: 'Қолма-қол ақшасыз есеп айырысу', deliverySupport: 'Бірыңғай анықтама желісі',
    deliveryAnswer: 'Сатып алудың негізгі шарттарын жинақтадым. Нақты қолжетімділік пен мерзімді менеджер растайды.',
    deliverySteps: ['ҚР бойынша жеткізу ережелерін тексеру', 'Көтерме және қолма-қол ақшасыз төлем шарттарын тексеру', 'Клиентке қысқаша ақпарат дайындау'],
    orderGuard: 'Себет тауар карточкасындағы растау батырмасы басылғанда ғана өзгереді.',
    fileResponse: 'Файл таңдалды. Бұл демонстрацияда ол серверге жіберілмейді; мазмұнын талдау үшін жүктеу API қажет.',
    stockError: 'Көрсетілген санға қойма қалдығы жеткіліксіз.',
    steps: ['Тауарды каталогтан іздеу', 'Қоймадағы қалдықты тексеру: 0', 'Қолжетімді баламаны таңдау'],
  },
  en: {
    cart: 'Cart', cartAria: 'Open cart, items: ', emptyCart: 'Your cart is empty', cartTitle: 'Shopping cart', closeCart: 'Close cart', unitsShort: 'units',
    itemCount: (count) => count + (count === 1 ? ' item' : ' items'), quantity: 'Quantity', remove: 'Remove item', stockLabel: 'In stock', total: 'Total',
    checkout: 'Checkout', demoOrder: 'Demo order, no payment required', orderSuccess: 'Test order created successfully.',
    emptyTitle: 'Your cart is empty', emptyCopy: 'Add a product from chat to see items and the total here.',
    freeShippingNeeded: (amount) => amount + ' ₸ left for free delivery in Kazakhstan (free from 50,000 ₸)',
    freeShippingReached: 'This cart qualifies for free delivery in Kazakhstan.',
    shippingProgress: 'Free delivery progress',
    cartLimit: 'Available stock:', cartLimitSuffix: 'units', cartFailure: 'Could not update the cart. Please try again.',
    certificateDownloaded: 'Demo PDF downloaded. This is not an official certificate.',
    inStock: 'in stock', stockEmpty: 'Out of stock', article: 'Article', quantityLabel: 'Quantity',
    quantityDown: 'Decrease quantity', quantityUp: 'Increase quantity', analogTitle: 'Suggested equivalent',
    demoStock: 'in demo stock', unknownPrice: 'Price on request', unknownSpecs: 'Specifications on request',
    cableName: 'VVGng(A)-LS cable 3×2.5', legrandName: 'Legrand DRX250, 3P, 160 A', analogName: 'CHINT eB circuit breaker, 3P, 160 A',
    analogRationale: '3P, 160 A and 4.5 kA parameters match; GOST compatibility is confirmed for this demo scenario.',
    cableSpecs: ['3 cores', '2.5 mm²', 'ng(A)-LS'], analogSpecs: ['3P', '160 A', '4.5 kA'], sourceSpecs: ['3P', '160 A', '4.5 kA'],
    meterUnit: 'm', pieceUnit: 'pcs.', stockUnavailable: 'No stock is available for this item.',
    stockMax: (count, unit) => 'You can add up to ' + count + ' ' + unit + '.', serverCartError: 'Could not update the cart on the server.',
    demoResponse: 'Demo answer · synthetic data',
    fallbackAnswer: 'No exact match was found in the demo catalog. Share an article number or specifications and I will check the item and compatibility.',
    fallbackSteps: ['Parsing the request parameters', 'Searching matching catalog items', 'Checking stock availability'],
    typeLabels: { search: 'search', catalog: 'catalog', stock: 'stock', analogs: 'equivalent', delivery: 'delivery', check: 'check', intent: 'request' },
    assistant: 'ChipAI — ekt.kz consultant', launcher: 'EKT AI Assistant', online: 'Online', role: 'ekt.kz consultant',
    catalogHelp: 'Catalog assistance', replyTime: 'We usually reply within a minute',
    welcomeKicker: 'Happy to help', welcome: 'Hello! I can find a product, check stock, suggest an equivalent, and find documents.',
    welcomeHint: 'Enter an article number or describe what you need.',
    prompts: ['VVGng cable 3x2.5', 'Legrand 160A equivalent', 'Delivery and wholesale terms'],
    promptQueries: ['VVGng cable 3x2.5', 'Legrand 160A equivalent', 'Delivery and wholesale terms'],
    placeholder: 'What are you looking for?…', footer: 'ekt.kz assistant', demo: 'Demo catalog data',
    add: '✓ Add to cart', noStock: 'Out of stock', adding: 'Adding…',
    languageToggle: 'Switch language: RU, KZ, or EN',
    success: '✓ Product added to cart!', cartAdded: (count) => '✓ Added: ' + count, checkoutLink: 'Continue to checkout',
    reasoning: 'Model search steps', stepCount: (count) => count + (count === 1 ? ' step' : ' steps'), certificateLink: '📄 GOST certificate of conformity (PDF)',
    cableAnswer: 'Found VVGng 3×2.5 cable in stock. Check the length and confirm using the button on the product card.',
    cableSteps: ['Searching the catalog for VVGng 3×2.5 cable', 'Checking stock: 1,250 m available', 'Checking specifications and GOST certificate'],
    analogAnswer: 'Legrand is out of stock, but we found a 100% GOST-compatible equivalent.',
    analogSteps: ['Searching for Legrand DRX250 160A', 'Legrand stock: 0', 'Searching certified equivalent: 3P, 160A, 4.5 kA', 'Found CHINT eB with matching parameters'],
    deliveryTitle: 'Delivery and wholesale terms', deliveryFree: 'Free delivery in Kazakhstan',
    deliveryPickup: 'Pickup', deliveryPickupText: 'Astana and Almaty', deliveryPayment: 'Payment for businesses',
    deliveryPaymentText: 'Bank transfer', deliverySupport: 'Customer information line',
    deliveryAnswer: 'Here is a summary of the main purchase terms. A manager can confirm exact availability and timing.',
    deliverySteps: ['Checking Kazakhstan delivery terms', 'Checking wholesale and bank transfer conditions', 'Preparing a short summary'],
    orderGuard: 'The cart changes only when you press the confirmation button on a product card.',
    fileResponse: 'The file is selected. This demo does not upload it; connect a file upload API to analyze its contents.',
    stockError: 'There is not enough stock for that quantity.',
    steps: ['Searching the catalog', 'Checking stock: 0', 'Finding an available equivalent'],
  },
};

const $ = (selector) => document.querySelector(selector);
const ui = {
  launcher: $('#chat-launcher'),
  widget: $('#chat-widget'),
  close: $('#close-chat'),
  minimize: $('#minimize-chat'),
  messages: $('#messages'),
  quickPrompts: $('#quick-prompts'),
  form: $('#chat-form'),
  input: $('#message-input'),
  send: $('#send-button'),
  attach: $('#attach-button'),
  fileInput: $('#file-input'),
  attachmentPreview: $('#attachment-preview'),
  cartCount: $('#header-cart-count'),
  cartLink: $('#store-cart-link'),
  drawerBackdrop: $('#cart-drawer-backdrop'),
  drawer: $('#cart-drawer'),
  drawerClose: $('#cart-drawer-close'),
  drawerItems: $('#cart-drawer-items'),
  shippingCopy: $('#shipping-progress-copy'),
  shippingBar: $('#shipping-progress-bar'),
  cartTotal: $('#cart-total'),
  checkoutButton: $('#cart-checkout-button'),
  toasts: $('#toast-region'),
};

const mascotMounts = [
  mountChipMascot($('#launcher-chip-mascot'), 60),
  mountChipMascot($('#header-chip-mascot'), 41),
];
let mascotState = 'idle';
let mascotStateTimer;

function setMascotState(state) {
  window.clearTimeout(mascotStateTimer);
  mascotState = state;
  mascotMounts.forEach((mascot) => mascot.setState(state));
  if (state === 'success') {
    mascotStateTimer = window.setTimeout(() => setMascotState('idle'), 1800);
  }
}

const fixtures = {
  breaker: {
    id: 515291,
    brand: 'LEGRAND',
    name: 'Автоматический выключатель Legrand DRX250, 3P, 160 А',
    article: '200300285_',
    price: 64920,
    stock: 0,
    unit: 'шт.',
    specifications: ['3 полюса', '160 А', '18 кА'],
    certificate: true,
    analogs: [{
      id: 710233,
      brand: 'CHINT',
      name: 'CHINT eB, 3P, 160 A, 4.5 kA',
      article: 'chint-eb-3p-160a',
      price: 38900,
      stock: 18,
      unit: 'шт.',
      specifications: ['3P', '160 A', '4.5 kA'],
      certificate: true,
      rationale: 'Совпадают полюсность, номинальный ток и отключающая способность; демонстрационная совместимость по ГОСТ.',
    }],
  },
  cable: {
    id: 515303,
    brand: 'КАЗЭНЕРГОКАБЕЛЬ',
    name: 'Кабель ВВГнг(А)-LS 3×2,5',
    article: 'vvgng-ls-3x2.5',
    price: 450,
    stock: 1250,
    unit: 'м',
    specifications: ['3 жилы', '2,5 мм²', 'нг(А)-LS'],
    certificate: true,
    analogs: [],
  },
};

const productRegistry = new Map();
const history = [];
let sessionId = createSessionId();
let attachments = [];
let cart = { items: [], checkout_url: CHECKOUT_FALLBACK };
let backendAvailable = false;
let isBusy = false;
let toastTimer;
let language = (() => {
  try { return ['ru', 'kz', 'en'].includes(localStorage.getItem(LANGUAGE_KEY)) ? localStorage.getItem(LANGUAGE_KEY) : 'ru'; }
  catch { return 'ru'; }
})();

function t(key) {
  return copy[language][key];
}

function applyLanguage() {
  document.documentElement.lang = language === 'kz' ? 'kk' : language;
  document.querySelectorAll('[data-language-option]').forEach((option) => {
    option.classList.toggle('is-current', option.dataset.languageOption === language);
  });
  $('#language-toggle').setAttribute('aria-label', t('languageToggle'));
  $('#cart-label').textContent = t('cart');
  $('#assistant-name-text').textContent = t('assistant');
  ui.widget.setAttribute('aria-label', t('assistant'));
  $('#launcher-label-text').textContent = t('launcher');
  $('#online-label').textContent = t('online');
  $('#assistant-role').textContent = t('role');
  $('#catalog-help').textContent = t('catalogHelp');
  $('#reply-time-label').textContent = t('replyTime');
  $('#welcome-kicker').textContent = t('welcomeKicker');
  $('#welcome-copy').textContent = t('welcome');
  $('#welcome-hint').textContent = t('welcomeHint');
  $('#message-input').placeholder = t('placeholder');
  $('#footer-assistant-label').textContent = t('footer');
  $('#demo-data-label').textContent = t('demo');
  ui.launcher.setAttribute('aria-label', language === 'ru' ? 'Открыть ИИ-консультанта' : language === 'kz' ? 'EKT кеңесшісін ашу' : 'Open EKT AI Assistant');
  ui.close.setAttribute('aria-label', language === 'ru' ? 'Закрыть чат' : language === 'kz' ? 'Чатты жабу' : 'Close chat');
  ui.minimize.setAttribute('aria-label', language === 'ru' ? 'Свернуть чат' : language === 'kz' ? 'Чатты жию' : 'Minimize chat');
  ui.quickPrompts.querySelectorAll('[data-prompt-label]').forEach((label, index) => {
    label.textContent = t('prompts')[index];
    label.parentElement.dataset.prompt = t('promptQueries')[index];
  });
  ui.messages.querySelectorAll('[data-add-cart]').forEach((button) => {
    const product = productRegistry.get(String(button.dataset.productId));
    button.innerHTML = '<svg class="icon"><use href="#i-cart"></use></svg>' + (product && remainingStock(product) > 0 ? t('add') : t('noStock'));
  });
  ui.messages.querySelectorAll('[data-cart-confirmation]').forEach((confirmation) => {
    const status = confirmation.querySelector('[data-cart-added]');
    const anchor = confirmation.querySelector('a');
    if (status) status.textContent = t('cartAdded')(Number(confirmation.dataset.quantity) || 1);
    if (anchor) anchor.textContent = t('checkoutLink');
  });
  ui.messages.querySelectorAll('[data-cart-success]').forEach((status) => { status.textContent = t('success') + ' ['; });
  ui.messages.querySelectorAll('[data-open-cart]').forEach((link) => { link.textContent = t('checkoutLink'); });
  ui.messages.querySelectorAll('.reasoning > summary > span:first-of-type').forEach((label) => {
    label.textContent = t('reasoning');
  });
  ui.messages.querySelectorAll('[data-demo-scenario]').forEach((row) => {
    const reply = quickScenarioReply(row.dataset.demoScenario);
    row.querySelector('.assistant-bubble').innerHTML = renderAssistantContent(reply);
  });
  $('#cart-drawer-title').textContent = t('cartTitle');
  $('#cart-total-label').textContent = t('total');
  $('#cart-checkout-button').textContent = t('checkout');
  $('#cart-demo-note').textContent = t('demoOrder');
  ui.drawerClose.setAttribute('aria-label', t('closeCart'));
  ui.shippingCopy.parentElement.setAttribute('aria-label', t('deliveryTitle'));
  ui.shippingBar.parentElement.setAttribute('aria-label', t('shippingProgress'));
  updateCartHeader();
  renderCartDrawer();
}

function createSessionId() {
  try {
    const saved = localStorage.getItem(SESSION_KEY);
    if (saved) return saved;
    const id = 'ekt_web_' + (crypto.randomUUID ? crypto.randomUUID() : String(Date.now()));
    localStorage.setItem(SESSION_KEY, id);
    return id;
  } catch {
    return 'ekt_web_' + String(Date.now());
  }
}

function escapeHtml(value) {
  return String(value == null ? '' : value).replace(/[&<>"']/g, (character) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  })[character]);
}

function safeExternalUrl(value) {
  if (!value) return null;
  try {
    const url = new URL(value, window.location.origin);
    return url.protocol === 'http:' || url.protocol === 'https:' ? url.href : null;
  } catch {
    return null;
  }
}

function money(value) {
  const amount = Number(value);
  if (!Number.isFinite(amount)) return t('unknownPrice');
  return new Intl.NumberFormat(language === 'en' ? 'en-KZ' : language === 'kz' ? 'kk-KZ' : 'ru-KZ', { maximumFractionDigits: 0 }).format(amount) + ' ₸';
}

function countItems(items) {
  return (items || []).reduce((sum, item) => sum + Math.max(0, Number(item.quantity) || 0), 0);
}

function totalSum(items) {
  return (items || []).reduce((sum, item) => sum + (Number(item.price) || 0) * (Number(item.quantity) || 0), 0);
}

function updateCartHeader() {
  const count = countItems(cart.items);
  ui.cartCount.textContent = count > 99 ? '99+' : String(count);
  ui.cartLink.href = safeExternalUrl(cart.checkout_url) || CHECKOUT_FALLBACK;
  ui.cartLink.setAttribute('aria-label', t('cartAria') + count);
  ui.cartLink.title = count ? String(count) + ' ' + t('unitsShort') + ' · ' + money(totalSum(cart.items)) : t('emptyCart');
}

function setCartItems(items, checkoutUrl) {
  cart = {
    items: (Array.isArray(items) ? items : []).map((item) => {
      const productId = Number(item.product_id || item.id);
      const knownProduct = productRegistry.get(String(productId));
      return Object.assign({}, item, {
        product_id: productId,
        stock: Math.max(0, Number(item.stock ?? item.available_quantity ?? (knownProduct && knownProduct.stock) ?? 0)),
      });
    }),
    checkout_url: safeExternalUrl(checkoutUrl) || CHECKOUT_FALLBACK,
  };
  updateCartHeader();
  renderCartDrawer();
}

function cartItemStock(item) {
  const product = productRegistry.get(String(item.product_id));
  return Math.max(0, Number(item.stock ?? (product && product.stock) ?? item.available_quantity ?? 0));
}

function localizedUnit(productId, unit) {
  if (Number(productId) === Number(fixtures.cable.id)) return t('meterUnit');
  if ([fixtures.breaker.id, Number(fixtures.breaker.analogs[0].id)].includes(Number(productId)) && ['шт.', 'pcs.', 'дана'].includes(unit)) return t('pieceUnit');
  return unit || (language === 'en' ? 'pcs.' : language === 'kz' ? 'дана' : 'шт.');
}

function renderCartDrawer() {
  const items = cart.items || [];
  const count = countItems(items);
  const total = totalSum(items);
  $('#cart-drawer-count').textContent = t('itemCount')(count);
  $('#cart-total').textContent = money(total);

  if (!items.length) {
    ui.drawerItems.innerHTML = '<div class="cart-empty-state"><span class="cart-empty-icon"><svg class="icon"><use href="#i-cart"></use></svg></span>' +
      '<strong>' + t('emptyTitle') + '</strong><p>' + t('emptyCopy') + '</p></div>';
  } else {
    ui.drawerItems.innerHTML = items.map((item) => {
      const id = Number(item.product_id || item.id);
      const quantity = Math.max(1, Number(item.quantity) || 1);
      const stock = cartItemStock(item);
      const unit = localizedUnit(id, item.unit);
      const price = Number(item.price) || 0;
      const brand = item.brand || (id === fixtures.cable.id ? fixtures.cable.brand : id === fixtures.breaker.id ? fixtures.breaker.brand : id === Number(fixtures.breaker.analogs[0].id) ? fixtures.breaker.analogs[0].brand : 'ekt.kz');
      const localizedName = id === fixtures.cable.id ? t('cableName') : id === fixtures.breaker.id ? t('legrandName') : id === Number(fixtures.breaker.analogs[0].id) ? t('analogName') : (item.name || item.title || t('cartTitle'));
      return '<article class="cart-line" data-cart-item data-product-id="' + escapeHtml(id) + '">' +
        '<div class="cart-line-top"><div class="cart-line-copy"><span class="cart-line-brand">' + escapeHtml(brand) + '</span>' +
          '<h3>' + escapeHtml(localizedName) + '</h3><span class="cart-line-article">' + escapeHtml(item.article || item.sku || '—') + '</span>' +
          '<span class="cart-line-stock">' + t('stockLabel') + ': ' + stock + ' ' + escapeHtml(unit) + '</span></div>' +
          '<button class="cart-remove-button" data-cart-action="remove" type="button" aria-label="' + t('remove') + '"><svg class="icon"><use href="#i-trash"></use></svg></button></div>' +
        '<div class="cart-line-bottom"><div class="cart-line-price"><strong>' + money(price) + '</strong><span>× ' + quantity + ' = <b>' + money(price * quantity) + '</b></span></div>' +
          '<div class="cart-quantity-control" aria-label="' + t('quantity') + '"><button type="button" data-cart-action="minus" aria-label="' + t('quantityDown') + '">−</button>' +
            '<span>' + quantity + '</span><button type="button" data-cart-action="plus" aria-label="' + t('quantityUp') + '"' + (quantity >= stock ? ' disabled' : '') + '>+</button></div></div></article>';
    }).join('');
  }

  const remaining = Math.max(0, 50000 - total);
  const progress = Math.min(100, total / 50000 * 100);
  const locale = language === 'en' ? 'en-KZ' : language === 'kz' ? 'kk-KZ' : 'ru-KZ';
  const remainingText = new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format(remaining);
  ui.shippingCopy.textContent = remaining ? t('freeShippingNeeded')(remainingText) : t('freeShippingReached');
  ui.shippingBar.style.width = progress + '%';
  ui.shippingBar.parentElement.setAttribute('aria-valuenow', String(Math.round(progress)));
  ui.checkoutButton.disabled = !items.length;
}

function openCartDrawer() {
  renderCartDrawer();
  ui.drawerBackdrop.hidden = false;
  ui.drawer.setAttribute('aria-hidden', 'false');
  document.body.classList.add('cart-drawer-open');
  window.setTimeout(() => ui.drawerClose.focus(), 30);
}

function closeCartDrawer() {
  ui.drawerBackdrop.hidden = true;
  ui.drawer.setAttribute('aria-hidden', 'true');
  document.body.classList.remove('cart-drawer-open');
  ui.cartLink.focus();
}

function updateCartQuantity(productId, change) {
  const item = cart.items.find((entry) => Number(entry.product_id || entry.id) === Number(productId));
  if (!item) return;
  const nextQuantity = Number(item.quantity) + change;
  const stock = cartItemStock(item);
  if (nextQuantity > stock) {
    toast(t('cartLimit') + ' ' + stock + ' ' + t('cartLimitSuffix') + '.', true);
    return;
  }
  if (nextQuantity < 1) cart.items = cart.items.filter((entry) => entry !== item);
  else item.quantity = nextQuantity;
  saveDemoCart();
  updateCartHeader();
  renderCartDrawer();
}

function removeCartItem(productId) {
  cart.items = cart.items.filter((item) => Number(item.product_id || item.id) !== Number(productId));
  saveDemoCart();
  updateCartHeader();
  renderCartDrawer();
}

function saveDemoCart() {
  try {
    localStorage.setItem(DEMO_CART_KEY, JSON.stringify({ items: cart.items, checkout_url: safeExternalUrl(cart.checkout_url) || CHECKOUT_FALLBACK }));
  } catch {
    // The widget still works in this tab when browser storage is disabled.
  }
}

async function fetchTimeout(url, options, timeout) {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeout || 2500);
  try {
    return await fetch(url, Object.assign({}, options || {}, { signal: controller.signal }));
  } finally {
    window.clearTimeout(timer);
  }
}

async function connectBackend() {
  try {
    const health = await fetchTimeout(API_BASE + '/health', {}, 900);
    backendAvailable = health.ok;
  } catch {
    backendAvailable = false;
  }
  try {
    const response = await fetchTimeout(API_BASE + '/cart?session_id=' + encodeURIComponent(sessionId), {}, 1300);
    if (response.ok) {
      const data = await response.json();
      backendAvailable = true;
      const saved = readDemoCart();
      if (saved) setCartItems(saved, data.checkout_url);
      else setCartItems(data.items, data.checkout_url);
      return;
    }
  } catch {
    backendAvailable = false;
  }
  try {
    const saved = JSON.parse(localStorage.getItem(DEMO_CART_KEY) || 'null');
    if (saved && Array.isArray(saved.items)) setCartItems(saved.items, saved.checkout_url);
    else updateCartHeader();
  } catch {
    updateCartHeader();
  }
}

function openChat() {
  ui.widget.setAttribute('aria-hidden', 'false');
  ui.launcher.setAttribute('aria-expanded', 'true');
  document.body.classList.add('chat-open');
  window.setTimeout(() => ui.input.focus(), 70);
}

function closeChat() {
  ui.widget.setAttribute('aria-hidden', 'true');
  ui.launcher.setAttribute('aria-expanded', 'false');
  document.body.classList.remove('chat-open');
  ui.launcher.focus();
}

function timeNow() {
  const locale = language === 'en' ? 'en-KZ' : language === 'kz' ? 'kk-KZ' : 'ru-RU';
  return new Intl.DateTimeFormat(locale, { hour: '2-digit', minute: '2-digit' }).format(new Date());
}

function scrollToBottom() {
  ui.messages.scrollTop = ui.messages.scrollHeight;
}

function appendUserMessage(text, files) {
  const fileList = files.map((file) =>
    '<span><svg class="icon"><use href="#i-file"></use></svg>' + escapeHtml(file.name) + '</span>',
  ).join('');
  const fileMarkup = fileList ? '<div class="message-file-list">' + fileList + '</div>' : '';
  const visibleText = text || 'Посмотрите, пожалуйста, вложение.';
  ui.messages.insertAdjacentHTML('beforeend',
    '<div class="message-row user-row"><div class="message-stack">' +
      '<div class="message-bubble user-bubble"><p>' + escapeHtml(visibleText) + '</p>' + fileMarkup + '</div>' +
      '<time class="message-time">' + timeNow() + '</time></div>' +
      '<span class="message-avatar user-avatar" aria-hidden="true">ВЫ</span></div>',
  );
  scrollToBottom();
}

function renderReasoning(steps) {
  if (!steps || !steps.length) return '';
  const rows = steps.map((step) => {
    const label = step.message || step.tool_name || step.type || copy[language].fallbackAnswer;
    const type = step.type
      ? '<span class="reasoning-type">' + escapeHtml(copy[language].typeLabels[step.type] || String(step.type).replaceAll('_', ' ')) + '</span>'
      : '';
    return '<li>' + type + escapeHtml(label) + '</li>';
  }).join('');
  return '<details class="reasoning"><summary><svg class="icon"><use href="#i-spark"></use></svg>' +
    '<span>' + t('reasoning') + '</span><span class="reasoning-count">' + copy[language].stepCount(steps.length) + '</span>' +
    '<svg class="icon reasoning-chevron"><use href="#i-chevron"></use></svg></summary>' +
    '<ol class="reasoning-list">' + rows + '</ol></details>';
}

function normaliseProduct(source, fallbackId) {
  source = source || {};
  const id = Number(source.product_id || source.id || fallbackId || 800000);
  const certificateUrl = safeExternalUrl(source.certificate_url || source.certificate_link || (typeof source.certificate === 'string' ? source.certificate : null));
  let specifications = source.specifications || [];
  if (typeof specifications === 'string') specifications = specifications.replaceAll(';', ',').split(',').map((item) => item.trim()).filter(Boolean);
  if (!Array.isArray(specifications)) specifications = [];
  const product = {
    id: Number.isFinite(id) ? id : Number(fallbackId || 800000),
    brand: source.brand || source.manufacturer || 'Каталог ekt.kz',
    name: source.name || source.title || 'Товар из каталога ekt.kz',
    article: source.article || source.sku || '—',
    price: Number(source.price) || 0,
    stock: Math.max(0, Number(source.quantity || source.stock || source.available_quantity || 0)),
    unit: source.unit || 'шт.',
    specifications: specifications,
    certificateUrl: certificateUrl,
    certificate: Boolean(certificateUrl || source.has_certificate || source.certificate_available || source.certificate === true),
    image: safeExternalUrl(source.image),
    rationale: source.rationale || '',
    analogs: [],
  };
  productRegistry.set(String(product.id), product);
  if (Array.isArray(source.analogs)) {
    product.analogs = source.analogs.map((analog, index) => normaliseProduct(analog, product.id + index + 1));
  }
  return product;
}

function renderQuantityControl(product) {
  const stock = Math.max(0, Number(product.stock) || 0);
  const available = Math.min(stock, remainingStock(product));
  const disabled = available < 1 ? ' disabled' : '';
  return '<div class="quantity-row"><span class="quantity-label">' + t('quantityLabel') + '</span>' +
    '<div class="quantity-control" data-quantity-control data-product-id="' + escapeHtml(product.id) + '" data-stock="' + available + '">' +
      '<button type="button" data-quantity-action="minus" aria-label="' + t('quantityDown') + '"' + disabled + '><svg class="icon"><use href="#i-minus"></use></svg></button>' +
      '<input type="number" min="1" max="' + Math.max(1, available) + '" value="1" inputmode="numeric" aria-label="' + t('quantityLabel') + '"' + disabled + '>' +
      '<button type="button" data-quantity-action="plus" aria-label="' + t('quantityUp') + '"' + disabled + '><svg class="icon"><use href="#i-plus"></use></svg></button>' +
    '</div></div><button class="add-cart-button" type="button" data-add-cart data-product-id="' + escapeHtml(product.id) + '"' + disabled + '>' +
    '<svg class="icon"><use href="#i-cart"></use></svg>' + (available ? t('add') : t('noStock')) +
    '</button><div class="cart-confirmation" data-cart-confirmation hidden></div>';
}

function renderAnalog(analog) {
  const stock = Number(analog.stock) || 0;
  const price = analog.price ? money(analog.price) : t('unknownPrice');
  const rationale = analog.rationale || t('fallbackAnswer');
  return '<div class="analog-block"><div class="analog-heading"><svg class="icon"><use href="#i-spark"></use></svg>' + t('analogTitle') + '</div>' +
    '<p class="analog-reason">' + escapeHtml(rationale) + '</p>' +
    '<div class="analog-offer" data-product-card="' + escapeHtml(analog.id) + '">' +
      '<div class="analog-product"><span class="product-visual"><svg class="icon"><use href="#i-bolt"></use></svg></span>' +
        '<span class="analog-copy"><strong>' + escapeHtml(analog.name) + '</strong><small>' + escapeHtml(analog.article) + ' · ' + price + ' · ' + stock + ' ' + escapeHtml(analog.unit) + ' ' + t('demoStock') + '</small></span></div>' +
      renderQuantityControl(analog) +
    '</div></div>';
}

function renderProductCard(product) {
  const inStock = Number(product.stock) > 0;
  const stockText = inStock ? String(product.stock) + ' ' + (product.unit || 'шт.') + ' ' + t('inStock') : t('stockEmpty');
  let certificate = '';
  if (product.certificateUrl) {
    certificate = '<a class="certificate-link" href="' + escapeHtml(product.certificateUrl) + '" target="_blank" rel="noreferrer"><svg class="icon"><use href="#i-file"></use></svg>' + t('certificateLink') + '</a>';
  } else if (product.certificate) {
    certificate = '<a class="certificate-link" href="#demo-certificate" data-certificate-download data-article="' + escapeHtml(product.article) + '"><svg class="icon"><use href="#i-file"></use></svg>' + t('certificateLink') + '</a>';
  }
  const analogs = !inStock ? product.analogs.map(renderAnalog).join('') : '';
  const specs = product.specifications.length
    ? product.specifications.slice(0, 4).map((spec) => '<span>' + escapeHtml(spec) + '</span>').join('')
    : '<span>' + t('unknownSpecs') + '</span>';
  const price = product.price ? money(product.price) + (product.unit === 'м' ? ' / м' : '') : t('unknownPrice');
  return '<article class="product-card" data-product-card="' + escapeHtml(product.id) + '">' +
    '<div class="product-topline"><span class="product-brand">' + escapeHtml(product.brand) + '</span>' +
      '<span class="stock-badge ' + (inStock ? '' : 'out-of-stock') + '">' + stockText + '</span></div>' +
    '<div class="product-body"><div class="product-title-row"><span class="product-visual"><svg class="icon"><use href="#i-bolt"></use></svg></span>' +
      '<span class="product-title-group"><h3>' + escapeHtml(product.name) + '</h3><span class="product-article">' + t('article') + ' ' + escapeHtml(product.article) + '</span></span></div>' +
      '<div class="product-specs">' + specs + '</div><div class="product-meta"><strong class="product-price">' + price + '</strong>' +
      '<span class="product-stock">' + Number(product.stock) + ' ' + escapeHtml(product.unit || 'шт.') + '</span></div>' +
      certificate + analogs + (inStock ? renderQuantityControl(product) : '') +
    '</div></article>';
}

function renderDeliveryCard() {
  return '<section class="delivery-card"><h3>' + t('deliveryTitle') + '</h3>' +
    '<div class="delivery-card-row"><span class="delivery-card-icon">₸</span><span><strong>' + t('deliveryFree') + '</strong><small>50 000 ₸</small></span></div>' +
    '<div class="delivery-card-row"><span class="delivery-card-icon">⌖</span><span><strong>' + t('deliveryPickup') + '</strong><small>' + t('deliveryPickupText') + '</small></span></div>' +
    '<div class="delivery-card-row"><span class="delivery-card-icon">↔</span><span><strong>' + t('deliveryPayment') + '</strong><small>' + t('deliveryPaymentText') + '</small></span></div>' +
    '<div class="delivery-card-row"><span class="delivery-card-icon">118</span><span><strong>' + t('deliverySupport') + '</strong><a href="tel:118">118</a></span></div></section>';
}

function appendAssistantMessage(reply) {
  const scenarioAttribute = reply.scenario ? ' data-demo-scenario="' + escapeHtml(reply.scenario) + '"' : '';
  ui.messages.insertAdjacentHTML('beforeend',
    '<div class="message-row assistant-row"' + scenarioAttribute + '><span class="message-avatar"><svg class="icon"><use href="#i-bolt"></use></svg></span>' +
    '<div class="message-stack"><div class="message-bubble assistant-bubble">' + renderAssistantContent(reply) +
    '</div><time class="message-time">' + timeNow() + '</time></div></div>',
  );
  scrollToBottom();
}

function renderAssistantContent(reply) {
  const paragraphs = String(reply.answer || t('fallbackAnswer')).split(/\n+/).filter(Boolean)
    .map((line) => '<p>' + escapeHtml(line) + '</p>').join('');
  const demoLabel = reply.isDemo
    ? '<span class="demo-response-label"><svg class="icon"><use href="#i-spark"></use></svg>' + t('demoResponse') + '</span>'
    : '';
  const cards = (reply.products || []).map(renderProductCard).join('');
  const delivery = reply.delivery ? renderDeliveryCard() : '';
  return demoLabel + renderReasoning(reply.steps || []) + '<div class="answer-copy">' + paragraphs + '</div>' + delivery + cards;
}

function appendTyping() {
  const id = 'typing-' + String(Date.now());
  ui.messages.insertAdjacentHTML('beforeend',
    '<div class="message-row assistant-row" id="' + id + '"><span class="message-avatar"><svg class="icon"><use href="#i-bolt"></use></svg></span>' +
    '<div class="message-stack"><div class="message-bubble assistant-bubble"><span class="typing-indicator" aria-label="Ассистент печатает"><i></i><i></i><i></i></span></div></div></div>',
  );
  scrollToBottom();
  return id;
}

function demoReply(text) {
  const query = String(text || '').toLocaleLowerCase('ru');
  if (query.includes('достав') || query.includes('жеткіз') || query.includes('delivery') || query.includes('оплат') || query.includes('партия') || query.includes('wholesale')) return quickScenarioReply('delivery');
  if (query.includes('кабел') || query.includes('ввг') || query.includes('cable') || query.includes('провод') || query.includes('сечени')) return quickScenarioReply('cable');
  if (query.includes('legrand') || query.includes('аналог') || query.includes('балама') || query.includes('equivalent')) return quickScenarioReply('analog');
  return {
    isDemo: true,
    answer: t('fallbackAnswer'),
    steps: copy[language].fallbackSteps.map((message, index) => ({ type: ['intent', 'search', 'check'][index], message })),
    products: [],
  };
}

function quickScenarioReply(scenario) {
  if (scenario === 'cable') {
    return {
      scenario: scenario,
      isDemo: true,
      answer: t('cableAnswer'),
      steps: copy[language].cableSteps.map((message, index) => ({ type: ['search', 'stock', 'check'][index], message })),
      products: [normaliseProduct(Object.assign({}, fixtures.cable, {
        name: t('cableName'), price: 450, stock: 1250, unit: t('meterUnit'), specifications: t('cableSpecs'), certificate: true,
      }))],
    };
  }
  if (scenario === 'analog') {
    return {
      scenario: scenario,
      isDemo: true,
      answer: t('analogAnswer'),
      steps: copy[language].analogSteps.map((message, index) => ({ type: ['search', 'stock', 'search', 'analogs'][index], message })),
      products: [normaliseProduct(Object.assign({}, fixtures.breaker, {
        name: t('legrandName'), specifications: t('sourceSpecs'), analogs: [Object.assign({}, fixtures.breaker.analogs[0], {
          name: t('analogName'), rationale: t('analogRationale'), unit: t('pieceUnit'), specifications: t('analogSpecs'),
        })],
      }))],
    };
  }
  return {
    scenario: 'delivery',
    isDemo: true,
    answer: t('deliveryAnswer'),
    steps: copy[language].deliverySteps.map((message, index) => ({ type: ['delivery', 'check', 'intent'][index], message })),
    products: [],
    delivery: true,
  };
}

function isCartIntent(text) {
  const query = String(text || '').trim().toLocaleLowerCase('ru');
  return query.includes('корзин') || query.includes('добав') || query.includes('оформ') || query.includes('заказ') || query.includes('закаж') ||
    query.includes('себет') || query.includes('қос') || query.includes('тапсырыс') || query.includes('рәсімде');
}

async function assistantReply(text, files) {
  if (files.length) {
    return {
      isDemo: true,
      answer: t('fileResponse'),
      steps: [
        { type: 'attachment', message: 'Проверяю тип и размер выбранного файла' },
        { type: 'integration', message: 'Ожидаю endpoint загрузки содержимого файла' },
      ],
      products: [],
    };
  }
  if (isCartIntent(text)) {
    return {
      isDemo: false,
      answer: t('orderGuard'),
      steps: [{ type: 'guardrail', message: t('orderGuard') }],
      products: [],
    };
  }
  if (backendAvailable) {
    const fileNames = files.map((file) => file.name + ' (' + (file.type || 'файл') + ')');
    const message = files.length ? String(text || 'Проверь вложение.') + '\nВложения: ' + fileNames.join(', ') : text;
    try {
      const response = await fetchTimeout(API_BASE + '/agent/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: message, session_id: sessionId, history: history.slice(-10), language: language }),
      }, 5000);
      if (!response.ok) throw new Error('Chat API returned ' + response.status);
      const data = await response.json();
      if (data.cart_updated) {
        return {
          isDemo: false,
          answer: t('orderGuard'),
          steps: data.reasoning_steps || [],
          products: (data.sources || []).map((source, index) => normaliseProduct(source, 900000 + index)),
        };
      }
      const answer = String(data.answer || '').trim();
      const lowerAnswer = answer.toLocaleLowerCase('ru');
      const placeholder = lowerAnswer.includes('чем могу помочь по каталогу') || lowerAnswer.includes('инициализация сессии консультанта');
      if (answer && !placeholder) {
        return {
          isDemo: false,
          answer: answer,
          steps: data.reasoning_steps || [],
          products: (data.sources || []).map((source, index) => normaliseProduct(source, 900000 + index)),
        };
      }
    } catch (error) {
      console.info('Using local demo response:', error.message);
    }
  }
  await new Promise((resolve) => window.setTimeout(resolve, 380));
  return demoReply(text);
}

function toast(message, isError) {
  window.clearTimeout(toastTimer);
  ui.toasts.innerHTML = '<div class="toast ' + (isError ? 'toast-error' : '') + '">' + escapeHtml(message) + '</div>';
  toastTimer = window.setTimeout(() => { ui.toasts.innerHTML = ''; }, 3200);
}

function updateAttachmentPreview() {
  if (!attachments.length) {
    ui.attachmentPreview.hidden = true;
    ui.attachmentPreview.innerHTML = '';
    return;
  }
  ui.attachmentPreview.hidden = false;
  ui.attachmentPreview.innerHTML = attachments.map((file, index) =>
    '<span class="attachment-chip"><svg class="icon"><use href="#i-file"></use></svg><span>' + escapeHtml(file.name) + '</span>' +
    '<button type="button" data-remove-attachment="' + index + '" aria-label="Удалить ' + escapeHtml(file.name) + '"><svg class="icon"><use href="#i-close"></use></svg></button></span>',
  ).join('');
}

function addFiles(list) {
  const allowed = ['pdf', 'xls', 'xlsx', 'jpg', 'jpeg', 'png', 'webp'];
  Array.from(list || []).forEach((file) => {
    const extension = file.name.split('.').pop().toLowerCase();
    if (!allowed.includes(extension)) {
      toast('Поддерживаются PDF, Excel, JPG, PNG и WEBP.', true);
      return;
    }
    if (file.size > MAX_FILE_SIZE) {
      toast(file.name + ': максимальный размер файла — 15 МБ.', true);
      return;
    }
    if (!attachments.some((item) => item.name === file.name && item.size === file.size)) attachments.push(file);
  });
  updateAttachmentPreview();
}

function readDemoCart() {
  try {
    const raw = localStorage.getItem(DEMO_CART_KEY);
    if (!raw) return null;
    const saved = JSON.parse(raw);
    return saved && Array.isArray(saved.items) ? saved.items : null;
  } catch {
    return null;
  }
}

function remainingStock(product) {
  const existing = cart.items.find((item) => Number(item.product_id) === Number(product.id));
  return Math.max(0, Number(product.stock) - (Number(existing ? existing.quantity : 0) || 0));
}

function showConfirmation(card, quantity) {
  const confirmation = card.querySelector('[data-cart-confirmation]');
  if (!confirmation) return;
  const checkout = safeExternalUrl(cart.checkout_url) || CHECKOUT_FALLBACK;
  confirmation.hidden = false;
  confirmation.dataset.quantity = String(quantity);
  confirmation.innerHTML = '<span data-cart-added>' + t('cartAdded')(quantity) + '</span>' +
    '<a href="' + escapeHtml(checkout) + '" data-open-cart target="_blank" rel="noreferrer">' + t('checkoutLink') + ' <svg class="icon"><use href="#i-external"></use></svg></a>';
}

function appendCartSystemMessage() {
  const checkout = safeExternalUrl(cart.checkout_url) || CHECKOUT_FALLBACK;
  ui.messages.insertAdjacentHTML('beforeend',
    '<div class="message-row assistant-row system-row"><span class="message-avatar system-avatar"><svg class="icon"><use href="#i-check"></use></svg></span>' +
    '<div class="message-stack"><div class="message-bubble system-bubble"><span data-cart-success>' + t('success') + ' [</span>' +
      '<a href="' + escapeHtml(checkout) + '" data-open-cart target="_blank" rel="noreferrer">' + t('checkoutLink') + '</a>]</div>' +
      '<time class="message-time">' + timeNow() + '</time></div></div>',
  );
  scrollToBottom();
}

async function addToCart(button) {
  if (button.disabled) return;
  const product = productRegistry.get(String(button.dataset.productId));
  const card = button.closest('[data-product-card]');
  const input = card && card.querySelector('[data-quantity-control] input');
  if (!product || !input) return;
  const quantity = Math.max(1, Math.floor(Number(input.value) || 1));
  const available = remainingStock(product);
  if (available < 1 || quantity > available) {
    toast(available < 1 ? t('stockUnavailable') : t('stockMax')(available, localizedUnit(product.id, product.unit)), true);
    input.value = String(Math.max(1, available));
    return;
  }

  button.disabled = true;
  const originalLabel = button.innerHTML;
  button.textContent = t('adding');
  const payload = {
    product_id: Number(product.id),
    article: product.article,
    name: product.name,
    price: Number(product.price) || 0,
    quantity: quantity,
    image: product.image || null,
  };
  try {
    if (backendAvailable) {
      const response = await fetchTimeout(API_BASE + '/cart/add?session_id=' + encodeURIComponent(sessionId), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      }, 4500);
      if (!response.ok) throw new Error(t('serverCartError'));
      const data = await response.json();
      if (Array.isArray(data.cart)) setCartItems(data.cart, cart.checkout_url);
      else await refreshServerCart();
    } else {
      const items = readDemoCart() || [];
      const existing = items.find((item) => Number(item.product_id) === payload.product_id);
      if (existing) existing.quantity += quantity;
      else items.push(Object.assign({}, payload, { stock: product.stock, unit: product.unit, brand: product.brand }));
      setCartItems(items, CHECKOUT_FALLBACK);
    }
    saveDemoCart();
    showConfirmation(card, quantity);
    appendCartSystemMessage();
    toast(t('success'));
  } catch (error) {
    toast(t('cartFailure'), true);
  } finally {
    button.innerHTML = originalLabel;
    button.disabled = remainingStock(product) < 1;
  }
}

async function refreshServerCart() {
  const response = await fetchTimeout(API_BASE + '/cart?session_id=' + encodeURIComponent(sessionId), {}, 2500);
  if (!response.ok) throw new Error(t('serverCartError'));
  const data = await response.json();
  setCartItems(data.items, data.checkout_url);
}

function clampQuantity(input) {
  const maximum = Math.max(1, Number(input.max) || 1);
  const quantity = Math.floor(Number(input.value) || 1);
  input.value = String(Math.min(maximum, Math.max(1, quantity)));
}

function makeDemoPdf() {
  const stream = [
    'BT', '/F1 22 Tf', '56 770 Td', '(DEMO CERTIFICATE) Tj',
    '/F1 12 Tf', '0 -35 Td', '(Sample PDF for the EKT chat widget preview.) Tj',
    '0 -24 Td', '(This is not an official product certificate.) Tj', 'ET',
  ].join('\n');
  const encoder = new TextEncoder();
  const objects = [
    '1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n',
    '2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n',
    '3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n',
    '4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n',
    '5 0 obj << /Length ' + encoder.encode(stream).length + ' >> stream\n' + stream + '\nendstream endobj\n',
  ];
  let pdf = '%PDF-1.4\n';
  const offsets = [0];
  objects.forEach((object) => {
    offsets.push(encoder.encode(pdf).length);
    pdf += object;
  });
  const xrefOffset = encoder.encode(pdf).length;
  pdf += 'xref\n0 ' + String(objects.length + 1) + '\n0000000000 65535 f \n';
  offsets.slice(1).forEach((offset) => { pdf += String(offset).padStart(10, '0') + ' 00000 n \n'; });
  pdf += 'trailer\n<< /Size ' + String(objects.length + 1) + ' /Root 1 0 R >>\nstartxref\n' + xrefOffset + '\n%%EOF';
  return new Blob([pdf], { type: 'application/pdf' });
}

function downloadDemoCertificate() {
  const url = URL.createObjectURL(makeDemoPdf());
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = 'ekt-demo-certificate.pdf';
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  toast(t('certificateDownloaded'));
}

async function submitMessage(event, promptScenario) {
  if (event) event.preventDefault();
  if (isBusy) return;
  const text = ui.input.value.trim();
  const files = attachments.slice();
  if (!text && !files.length) return;
  appendUserMessage(text, files);
  history.push({ role: 'user', content: text + (files.length ? '\nВложения: ' + files.map((file) => file.name).join(', ') : '') });
  ui.input.value = '';
  ui.input.style.height = 'auto';
  attachments = [];
  updateAttachmentPreview();
  isBusy = true;
  setMascotState('thinking');
  ui.send.disabled = true;
  const typingId = appendTyping();
  try {
    const reply = promptScenario
      ? await new Promise((resolve) => window.setTimeout(() => resolve(quickScenarioReply(promptScenario)), 800))
      : await assistantReply(text, files);
    document.getElementById(typingId)?.remove();
    appendAssistantMessage(reply);
    history.push({ role: 'assistant', content: reply.answer });
    setMascotState('success');
  } finally {
    document.getElementById(typingId)?.remove();
    isBusy = false;
    if (mascotState === 'thinking') setMascotState('idle');
    ui.send.disabled = false;
    ui.input.focus();
  }
}

ui.launcher.addEventListener('click', openChat);
$('#language-toggle').addEventListener('click', () => {
  const languages = ['ru', 'kz', 'en'];
  language = languages[(languages.indexOf(language) + 1) % languages.length];
  try { localStorage.setItem(LANGUAGE_KEY, language); } catch { /* Locale remains active for this page. */ }
  applyLanguage();
});
ui.cartLink.addEventListener('click', (event) => {
  event.preventDefault();
  openCartDrawer();
});
ui.drawerClose.addEventListener('click', closeCartDrawer);
ui.drawerBackdrop.addEventListener('click', (event) => {
  if (event.target === ui.drawerBackdrop) closeCartDrawer();
});
ui.drawerItems.addEventListener('click', (event) => {
  const actionButton = event.target.closest('[data-cart-action]');
  if (!actionButton) return;
  const item = actionButton.closest('[data-cart-item]');
  if (!item) return;
  const productId = Number(item.dataset.productId);
  if (actionButton.dataset.cartAction === 'remove') removeCartItem(productId);
  else updateCartQuantity(productId, actionButton.dataset.cartAction === 'plus' ? 1 : -1);
});
ui.checkoutButton.addEventListener('click', () => {
  if (!cart.items.length) return;
  cart.items = [];
  saveDemoCart();
  updateCartHeader();
  renderCartDrawer();
  toast(t('orderSuccess'));
});
ui.close.addEventListener('click', closeChat);
ui.minimize.addEventListener('click', closeChat);
ui.form.addEventListener('submit', submitMessage);
ui.input.addEventListener('input', () => {
  ui.input.style.height = 'auto';
  ui.input.style.height = Math.min(ui.input.scrollHeight, 96) + 'px';
});
ui.attach.addEventListener('click', () => ui.fileInput.click());
ui.fileInput.addEventListener('change', (event) => {
  addFiles(event.target.files);
  event.target.value = '';
});
ui.quickPrompts.addEventListener('click', (event) => {
  const button = event.target.closest('[data-prompt]');
  if (!button) return;
  ui.input.value = button.dataset.prompt;
  submitMessage(null, button.dataset.scenario);
});
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && !ui.drawerBackdrop.hidden) closeCartDrawer();
  if (event.key === 'Escape' && ui.widget.getAttribute('aria-hidden') === 'false') closeChat();
  if (event.key === 'Enter' && !event.shiftKey && document.activeElement === ui.input) {
    event.preventDefault();
    ui.form.requestSubmit();
  }
});
ui.attachmentPreview.addEventListener('click', (event) => {
  const button = event.target.closest('[data-remove-attachment]');
  if (!button) return;
  attachments.splice(Number(button.dataset.removeAttachment), 1);
  updateAttachmentPreview();
});
ui.messages.addEventListener('click', (event) => {
  const checkoutLink = event.target.closest('[data-open-cart]');
  if (checkoutLink) {
    event.preventDefault();
    openCartDrawer();
    return;
  }
  const certificate = event.target.closest('[data-certificate-download]');
  if (certificate) {
    event.preventDefault();
    downloadDemoCertificate();
    return;
  }
  const quantityButton = event.target.closest('[data-quantity-action]');
  if (quantityButton) {
    const input = quantityButton.closest('[data-quantity-control]')?.querySelector('input');
    if (!input || quantityButton.disabled) return;
    const delta = quantityButton.dataset.quantityAction === 'plus' ? 1 : -1;
    input.value = String(Math.min(Number(input.max) || 1, Math.max(1, (Number(input.value) || 1) + delta)));
    return;
  }
  const addButton = event.target.closest('[data-add-cart]');
  if (addButton) addToCart(addButton);
});
ui.messages.addEventListener('change', (event) => {
  if (event.target.matches('[data-quantity-control] input')) clampQuantity(event.target);
});

normaliseProduct(fixtures.breaker);
normaliseProduct(fixtures.cable);
updateCartHeader();
applyLanguage();
connectBackend();
