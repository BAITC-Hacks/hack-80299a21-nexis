const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api').replace(new RegExp('/+$'), '');
const CHECKOUT_FALLBACK = 'https://ekt.kz/personal/cart/';
const SESSION_KEY = 'ekt-widget-session';
const DEMO_CART_KEY = 'ekt-widget-demo-cart';
const MAX_FILE_SIZE = 15 * 1024 * 1024;

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
  toasts: $('#toast-region'),
};

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
      brand: 'EKF',
      name: 'Выключатель силовой PROxima, 3P, 160 А',
      article: 'mccb-160-3p',
      price: 52800,
      stock: 23,
      unit: 'шт.',
      specifications: ['3 полюса', '160 А', '25 кА'],
      certificate: true,
      rationale: 'Совпадают номинальный ток и число полюсов; отключающая способность выше в демо-каталоге.',
    }],
  },
  cable: {
    id: 515303,
    brand: 'КАЗЭНЕРГОКАБЕЛЬ',
    name: 'Кабель ВВГнг(А)-LS 3×2,5',
    article: 'vvgng-ls-3x2.5',
    price: 890,
    stock: 420,
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
  if (!Number.isFinite(amount)) return 'Цена уточняется';
  return new Intl.NumberFormat('ru-KZ', { maximumFractionDigits: 0 }).format(amount) + ' ₸';
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
  ui.cartLink.setAttribute('aria-label', 'Открыть корзину, товаров: ' + count);
  ui.cartLink.title = count ? String(count) + ' ед. · ' + money(totalSum(cart.items)) : 'Корзина пока пуста';
}

function setCartItems(items, checkoutUrl) {
  cart = {
    items: Array.isArray(items) ? items : [],
    checkout_url: safeExternalUrl(checkoutUrl) || CHECKOUT_FALLBACK,
  };
  updateCartHeader();
}

function saveDemoCart() {
  try {
    localStorage.setItem(DEMO_CART_KEY, JSON.stringify({ items: cart.items, checkout_url: CHECKOUT_FALLBACK }));
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
      setCartItems(data.items, data.checkout_url);
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
  return new Intl.DateTimeFormat('ru-RU', { hour: '2-digit', minute: '2-digit' }).format(new Date());
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
    const label = step.message || step.tool_name || step.type || 'Обработка запроса';
    const type = step.type
      ? '<span class="reasoning-type">' + escapeHtml(String(step.type).replaceAll('_', ' ')) + '</span>'
      : '';
    return '<li>' + type + escapeHtml(label) + '</li>';
  }).join('');
  const word = steps.length === 1 ? 'шаг' : (steps.length < 5 ? 'шага' : 'шагов');
  return '<details class="reasoning"><summary><svg class="icon"><use href="#i-spark"></use></svg>' +
    '<span>Ход поиска ИИ</span><span class="reasoning-count">' + steps.length + ' ' + word + '</span>' +
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
  const disabled = stock < 1 ? ' disabled' : '';
  return '<div class="quantity-row"><span class="quantity-label">Количество</span>' +
    '<div class="quantity-control" data-quantity-control data-product-id="' + escapeHtml(product.id) + '" data-stock="' + stock + '">' +
      '<button type="button" data-quantity-action="minus" aria-label="Уменьшить количество"' + disabled + '><svg class="icon"><use href="#i-minus"></use></svg></button>' +
      '<input type="number" min="1" max="' + Math.max(1, stock) + '" value="1" inputmode="numeric" aria-label="Количество товара"' + disabled + '>' +
      '<button type="button" data-quantity-action="plus" aria-label="Увеличить количество"' + disabled + '><svg class="icon"><use href="#i-plus"></use></svg></button>' +
    '</div></div><button class="add-cart-button" type="button" data-add-cart data-product-id="' + escapeHtml(product.id) + '"' + disabled + '>' +
    '<svg class="icon"><use href="#i-cart"></use></svg>' + (stock ? 'Добавить в корзину' : 'Нет в наличии') +
    '</button><div class="cart-confirmation" data-cart-confirmation hidden></div>';
}

function renderAnalog(analog) {
  const stock = Number(analog.stock) || 0;
  const price = analog.price ? money(analog.price) : 'Цена уточняется';
  const rationale = analog.rationale || 'Схожие номинальный ток и число полюсов.';
  return '<div class="analog-block"><div class="analog-heading"><svg class="icon"><use href="#i-spark"></use></svg>Подходящий аналог</div>' +
    '<p class="analog-reason">' + escapeHtml(rationale) + '</p>' +
    '<div class="analog-offer" data-product-card="' + escapeHtml(analog.id) + '">' +
      '<div class="analog-product"><span class="product-visual"><svg class="icon"><use href="#i-bolt"></use></svg></span>' +
        '<span class="analog-copy"><strong>' + escapeHtml(analog.name) + '</strong><small>' + escapeHtml(analog.article) + ' · ' + price + ' · ' + stock + ' ' + escapeHtml(analog.unit) + ' в демо-остатке</small></span></div>' +
      renderQuantityControl(analog) +
    '</div></div>';
}

function renderProductCard(product) {
  const inStock = Number(product.stock) > 0;
  const stockText = inStock ? String(product.stock) + ' ' + (product.unit || 'шт.') + ' в наличии' : 'Нет в наличии';
  let certificate = '';
  if (product.certificateUrl) {
    certificate = '<a class="certificate-link" href="' + escapeHtml(product.certificateUrl) + '" target="_blank" rel="noreferrer"><svg class="icon"><use href="#i-file"></use></svg>Сертификат · PDF</a>';
  } else if (product.certificate) {
    certificate = '<a class="certificate-link" href="#demo-certificate" data-certificate-download data-article="' + escapeHtml(product.article) + '"><svg class="icon"><use href="#i-file"></use></svg>Демо-сертификат · PDF</a>';
  }
  const analogs = !inStock ? product.analogs.map(renderAnalog).join('') : '';
  const specs = product.specifications.length
    ? product.specifications.slice(0, 4).map((spec) => '<span>' + escapeHtml(spec) + '</span>').join('')
    : '<span>Характеристики уточняются</span>';
  const price = product.price ? money(product.price) + (product.unit === 'м' ? ' / м' : '') : 'Цена уточняется';
  return '<article class="product-card" data-product-card="' + escapeHtml(product.id) + '">' +
    '<div class="product-topline"><span class="product-brand">' + escapeHtml(product.brand) + '</span>' +
      '<span class="stock-badge ' + (inStock ? '' : 'out-of-stock') + '">' + stockText + '</span></div>' +
    '<div class="product-body"><div class="product-title-row"><span class="product-visual"><svg class="icon"><use href="#i-bolt"></use></svg></span>' +
      '<span class="product-title-group"><h3>' + escapeHtml(product.name) + '</h3><span class="product-article">Артикул ' + escapeHtml(product.article) + '</span></span></div>' +
      '<div class="product-specs">' + specs + '</div><div class="product-meta"><strong class="product-price">' + price + '</strong>' +
      '<span class="product-stock">' + Number(product.stock) + ' ' + escapeHtml(product.unit || 'шт.') + '</span></div>' +
      certificate + analogs + (inStock ? renderQuantityControl(product) : '') +
    '</div></article>';
}

function appendAssistantMessage(reply) {
  const paragraphs = String(reply.answer || 'Чем ещё помочь по каталогу?').split(/\n+/).filter(Boolean)
    .map((line) => '<p>' + escapeHtml(line) + '</p>').join('');
  const demoLabel = reply.isDemo
    ? '<span class="demo-response-label"><svg class="icon"><use href="#i-spark"></use></svg>Демо-ответ · синтетические данные</span>'
    : '';
  const cards = (reply.products || []).map(renderProductCard).join('');
  ui.messages.insertAdjacentHTML('beforeend',
    '<div class="message-row assistant-row"><span class="message-avatar"><svg class="icon"><use href="#i-bolt"></use></svg></span>' +
    '<div class="message-stack"><div class="message-bubble assistant-bubble">' + demoLabel +
      renderReasoning(reply.steps || []) + '<div class="answer-copy">' + paragraphs + '</div>' + cards +
    '</div><time class="message-time">' + timeNow() + '</time></div></div>',
  );
  scrollToBottom();
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
  if (query.includes('достав') || query.includes('оплат') || query.includes('партия')) {
    return {
      isDemo: true,
      answer: 'Условия доставки, оплаты и минимальная партия зависят от города, наличия и конкретной позиции. Напишите город и артикул — проверю условия для вашего заказа. Данные в этом прототипе демонстрационные.',
      steps: [
        { type: 'intent', message: 'Определяю вопрос об условиях покупки' },
        { type: 'search', message: 'Ищу правила доставки и оплаты по городу' },
        { type: 'check', message: 'Для точного ответа нужны город и выбранные позиции' },
      ],
      products: [],
    };
  }
  if (query.includes('кабел') || query.includes('ввг') || query.includes('провод') || query.includes('сечени')) {
    return {
      isDemo: true,
      answer: 'Нашёл позицию в демонстрационном каталоге. Сверьте сечение и исполнение кабеля с проектом. Сертификат-пример можно скачать по ссылке в карточке.',
      steps: [
        { type: 'search', message: 'Ищу кабель по марке и сечению' },
        { type: 'catalog', message: 'Сопоставляю артикул и технические характеристики' },
        { type: 'stock', message: 'Проверяю остаток и документы на позицию' },
      ],
      products: [normaliseProduct(fixtures.cable)],
    };
  }
  if (query.includes('сертификат') || query.includes('документ') || query.includes('паспорт')) {
    return {
      isDemo: true,
      answer: 'В карточке товара есть ссылка на демо-сертификат PDF. В рабочей интеграции она будет вести на документ из каталога ekt.kz.',
      steps: [
        { type: 'search', message: 'Определяю товар, к которому нужен документ' },
        { type: 'documents', message: 'Проверяю наличие сертификата в карточке товара' },
      ],
      products: [normaliseProduct(fixtures.cable)],
    };
  }
  return {
    isDemo: true,
    answer: 'В демо-каталоге автомат на 160 А сейчас без остатка. Нашёл аналог с таким же номинальным током и числом полюсов; сравните характеристики перед заказом.',
    steps: [
      { type: 'search', message: 'Ищу автоматический выключатель на 160 А' },
      { type: 'stock', message: 'Проверяю остаток по складам: у исходной позиции нулевой остаток' },
      { type: 'analogs', message: 'Подбираю доступный аналог по току и числу полюсов' },
      { type: 'documents', message: 'Проверяю сертификат для карточки товара' },
    ],
    products: [normaliseProduct(fixtures.breaker)],
  };
}

function isCartIntent(text) {
  const query = String(text || '').trim().toLocaleLowerCase('ru');
  return query.includes('корзин') || query.includes('добав') || query.includes('оформ') || query.includes('заказ') || query.includes('закаж');
}

async function assistantReply(text, files) {
  if (files.length) {
    return {
      isDemo: true,
      answer: 'Файл прикреплён к сообщению. В текущем API-контракте пока нет передачи содержимого файла — для разбора PDF, Excel или фото нужно подключить endpoint загрузки. Сейчас интерфейс проверяет тип и размер и показывает выбранные вложения.',
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
      answer: 'Чтобы корзина изменилась только с вашего согласия, нажмите «Добавить в корзину» на карточке нужного товара. Одного сообщения в чате недостаточно.',
      steps: [{ type: 'guardrail', message: 'Изменение корзины доступно только по отдельному нажатию кнопки подтверждения' }],
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
        body: JSON.stringify({ message: message, session_id: sessionId, history: history.slice(-10), language: 'ru' }),
      }, 5000);
      if (!response.ok) throw new Error('Chat API returned ' + response.status);
      const data = await response.json();
      if (data.cart_updated) {
        return {
          isDemo: false,
          answer: 'Для изменения корзины нажмите отдельную кнопку подтверждения в карточке товара.',
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
    const saved = JSON.parse(localStorage.getItem(DEMO_CART_KEY) || 'null');
    return saved && Array.isArray(saved.items) ? saved.items : [];
  } catch {
    return [];
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
  confirmation.innerHTML = '<span>Добавлено: ' + quantity + ' · корзина обновлена</span>' +
    '<a href="' + escapeHtml(checkout) + '" target="_blank" rel="noreferrer">Оформить <svg class="icon"><use href="#i-external"></use></svg></a>';
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
    toast(available < 1 ? 'Доступного остатка для этой позиции больше нет.' : 'Можно добавить не более ' + available + ' ' + (product.unit || 'шт.') + '.', true);
    input.value = String(Math.max(1, available));
    return;
  }

  button.disabled = true;
  const originalLabel = button.innerHTML;
  button.textContent = 'Добавляем…';
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
      if (!response.ok) throw new Error('Не удалось обновить корзину на сервере.');
      const data = await response.json();
      if (Array.isArray(data.cart)) setCartItems(data.cart, cart.checkout_url);
      else await refreshServerCart();
    } else {
      const items = readDemoCart();
      const existing = items.find((item) => Number(item.product_id) === payload.product_id);
      if (existing) existing.quantity += quantity;
      else items.push(payload);
      setCartItems(items, CHECKOUT_FALLBACK);
      saveDemoCart();
    }
    showConfirmation(card, quantity);
    toast(product.name + ' добавлен в корзину.');
  } catch (error) {
    toast(error.message || 'Не удалось обновить корзину. Попробуйте ещё раз.', true);
  } finally {
    button.innerHTML = originalLabel;
    button.disabled = remainingStock(product) < 1;
  }
}

async function refreshServerCart() {
  const response = await fetchTimeout(API_BASE + '/cart?session_id=' + encodeURIComponent(sessionId), {}, 2500);
  if (!response.ok) throw new Error('Не удалось прочитать корзину.');
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
  toast('Скачан пример PDF. Это не официальный сертификат.');
}

async function submitMessage(event) {
  if (event) event.preventDefault();
  if (isBusy) return;
  const text = ui.input.value.trim();
  const files = attachments.slice();
  if (!text && !files.length) return;
  ui.quickPrompts.hidden = true;
  appendUserMessage(text, files);
  history.push({ role: 'user', content: text + (files.length ? '\nВложения: ' + files.map((file) => file.name).join(', ') : '') });
  ui.input.value = '';
  ui.input.style.height = 'auto';
  attachments = [];
  updateAttachmentPreview();
  isBusy = true;
  ui.send.disabled = true;
  const typingId = appendTyping();
  try {
    const reply = await assistantReply(text, files);
    document.getElementById(typingId)?.remove();
    appendAssistantMessage(reply);
    history.push({ role: 'assistant', content: reply.answer });
  } finally {
    document.getElementById(typingId)?.remove();
    isBusy = false;
    ui.send.disabled = false;
    ui.input.focus();
  }
}

ui.launcher.addEventListener('click', openChat);
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
  ui.form.requestSubmit();
});
document.addEventListener('keydown', (event) => {
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

updateCartHeader();
connectBackend();
