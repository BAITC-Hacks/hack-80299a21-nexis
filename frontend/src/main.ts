import { mountChipMascot } from './mountChipMascot';
import type { ChipMascotState } from './components/ChipMascot';
import { copy } from './chat/i18n';
import { element as $, escapeHtml, safeExternalUrl } from './chat/dom';
import { renderReasoningTimeline } from './chat/reasoning';
import type { AssistantReply, Cart, CartItem, CartResponse, ChatResponse, HistoryMessage, Language, Product, ProductSource, ReasoningStep, Scenario } from './chat/types';

const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api').replace(new RegExp('/+$'), '');
const CHECKOUT_FALLBACK = 'https://ekt.kz/personal/cart/';
const SESSION_KEY = 'ekt-widget-session';
const DEMO_CART_KEY = 'ekt-widget-demo-cart';
const MAX_FILE_SIZE = 15 * 1024 * 1024;
const LANGUAGE_KEY = 'ekt-widget-language';

const ui = {
  launcher: $<HTMLButtonElement>('#chat-launcher'),
  widget: $('#chat-widget'),
  close: $<HTMLButtonElement>('#close-chat'),
  minimize: $<HTMLButtonElement>('#minimize-chat'),
  messages: $('#messages'),
  quickPrompts: $('#quick-prompts'),
  form: $<HTMLFormElement>('#chat-form'),
  input: $<HTMLTextAreaElement>('#message-input'),
  send: $<HTMLButtonElement>('#send-button'),
  attach: $<HTMLButtonElement>('#attach-button'),
  fileInput: $<HTMLInputElement>('#file-input'),
  attachmentPreview: $('#attachment-preview'),
  cartCount: $('#header-cart-count'),
  cartLink: $<HTMLAnchorElement>('#store-cart-link'),
  drawerBackdrop: $('#cart-drawer-backdrop'),
  drawer: $('#cart-drawer'),
  drawerClose: $<HTMLButtonElement>('#cart-drawer-close'),
  drawerItems: $('#cart-drawer-items'),
  shippingCopy: $('#shipping-progress-copy'),
  shippingBar: $('#shipping-progress-bar'),
  cartTotal: $('#cart-total'),
  checkoutButton: $<HTMLButtonElement>('#cart-checkout-button'),
  toasts: $('#toast-region'),
};

const mascotMounts = [
  mountChipMascot($('#launcher-chip-mascot'), 58),
  mountChipMascot($('#header-chip-mascot'), 48),
  mountChipMascot(document.querySelector('#welcome-chip-mascot'), 88),
];
let mascotState: ChipMascotState = 'idle';
let mascotStateTimer: number | undefined;

function setMascotState(state: ChipMascotState) {
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

const productRegistry = new Map<string, Product>();
const history: HistoryMessage[] = [];
const sessionId = createSessionId();
let attachments: File[] = [];
let cart: Cart = { items: [], checkout_url: CHECKOUT_FALLBACK };
let backendAvailable = false;
let isBusy = false;
let toastTimer: number | undefined;
let chatFocusTimer: number | undefined;
function isLanguage(value: string | null | undefined): value is Language {
  return value === 'ru' || value === 'kz' || value === 'en';
}

let language: Language = (() => {
  try {
    const saved = localStorage.getItem(LANGUAGE_KEY);
    return isLanguage(saved) ? saved : 'ru';
  } catch { return 'ru'; }
})();

function t<Key extends keyof typeof copy.ru>(key: Key): (typeof copy.ru)[Key] {
  return copy[language][key];
}

function setLanguage(value: Language) {
  language = value;
  try { localStorage.setItem(LANGUAGE_KEY, language); } catch { /* Keep this tab's choice. */ }
  applyLanguage();
}

function applyLanguage() {
  document.documentElement.lang = language === 'kz' ? 'kk' : language;
  document.querySelectorAll<HTMLElement>('[data-language-option]').forEach((option) => {
    option.classList.toggle('is-current', option.dataset.languageOption === language);
  });
  $('#chat-languages').setAttribute('aria-label', t('languageToggle'));
  document.querySelectorAll<HTMLButtonElement>('[data-chat-language]').forEach((button) => {
    const selected = button.dataset.chatLanguage === language;
    button.classList.toggle('is-current', selected);
    button.setAttribute('aria-pressed', String(selected));
  });
  $('#language-toggle').setAttribute('aria-label', t('languageToggle'));
  $('#cart-label').textContent = t('cart');
  $('#assistant-name-text').textContent = 'ChipAI';
  ui.widget.setAttribute('aria-label', t('assistant'));
  $('#launcher-label-text').textContent = 'ChipAI ' + t('online');
  $('#online-label').textContent = t('online');
  $('#assistant-role').textContent = t('role');
  $('#catalog-help').textContent = t('catalogHelp');
  $('#reply-time-label').textContent = t('replyTime');
  $('#welcome-kicker').textContent = t('welcomeKicker');
  $('#welcome-copy').textContent = t('welcome');
  $('#welcome-hint').textContent = t('welcomeHint');
  $('#welcome-time').textContent = t('welcomeTime');
  $('#composer-send-hint').textContent = t('composerSendHint');
  $('#composer-newline-hint').textContent = t('composerNewlineHint');
  ui.input.placeholder = t('placeholder');
  ui.input.setAttribute('aria-label', t('messageLabel'));
  ui.send.setAttribute('aria-label', t('sendMessage'));
  ui.attach.setAttribute('aria-label', t('attachFile'));
  ui.attach.title = t('attachFileTitle');
  ui.quickPrompts.setAttribute('aria-label', t('promptExamples'));
  $('#footer-assistant-label').textContent = t('footer');
  $('#demo-data-label').textContent = t('demo');
  updateLauncherLabel();
  const closeLabel = language === 'ru' ? 'Закрыть чат' : language === 'kz' ? 'Чатты жабу' : 'Close chat';
  const minimizeLabel = language === 'ru' ? 'Свернуть чат' : language === 'kz' ? 'Чатты жию' : 'Minimize chat';
  ui.close.setAttribute('aria-label', closeLabel);
  ui.close.title = closeLabel;
  ui.minimize.setAttribute('aria-label', minimizeLabel);
  ui.minimize.title = minimizeLabel;
  ui.quickPrompts.querySelectorAll('[data-prompt-label]').forEach((label, index) => {
    label.textContent = t('prompts')[index];
    if (label.parentElement) label.parentElement.dataset.prompt = t('promptQueries')[index];
  });
  ui.messages.querySelectorAll<HTMLButtonElement>('[data-add-cart]').forEach((button) => {
    const product = productRegistry.get(String(button.dataset.productId));
    button.innerHTML = '<svg class="icon"><use href="#i-cart"></use></svg>' + (product && remainingStock(product) > 0 ? t('add') : t('noStock'));
  });
  ui.messages.querySelectorAll<HTMLElement>('[data-cart-confirmation]').forEach((confirmation) => {
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
  ui.messages.querySelectorAll<HTMLDetailsElement>('.reasoning-live').forEach((timeline) => {
    const template = document.createElement('template');
    template.innerHTML = renderProcessingReasoning();
    const localized = template.content.querySelector('details');
    // Keep the existing details element so the user's expanded state survives.
    if (localized) timeline.replaceChildren(...localized.childNodes);
  });
  ui.messages.querySelectorAll<HTMLElement>('[data-demo-scenario]').forEach((row) => {
    const reply = quickScenarioReply(scenarioFromValue(row.dataset.demoScenario) || 'delivery');
    const bubble = row.querySelector('.assistant-bubble');
    if (bubble) bubble.innerHTML = renderAssistantContent(reply);
  });
  $('#cart-drawer-title').textContent = t('cartTitle');
  $('#cart-total-label').textContent = t('total');
  $('#cart-checkout-button').textContent = t('checkout');
  $('#cart-demo-note').textContent = t('demoOrder');
  ui.drawerClose.setAttribute('aria-label', t('closeCart'));
  ui.shippingCopy.parentElement?.setAttribute('aria-label', t('deliveryTitle'));
  ui.shippingBar.parentElement?.setAttribute('aria-label', t('shippingProgress'));
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

function money(value: number | string) {
  const amount = Number(value);
  if (!Number.isFinite(amount)) return t('unknownPrice');
  return new Intl.NumberFormat(language === 'en' ? 'en-KZ' : language === 'kz' ? 'kk-KZ' : 'ru-KZ', { maximumFractionDigits: 0 }).format(amount) + ' ₸';
}

function countItems(items: CartItem[]) {
  return (items || []).reduce((sum, item) => sum + Math.max(0, Number(item.quantity) || 0), 0);
}

function totalSum(items: CartItem[]) {
  return (items || []).reduce((sum, item) => sum + (Number(item.price) || 0) * (Number(item.quantity) || 0), 0);
}

function updateCartHeader() {
  const count = countItems(cart.items);
  ui.cartCount.textContent = count > 99 ? '99+' : String(count);
  ui.cartLink.href = safeExternalUrl(cart.checkout_url) || CHECKOUT_FALLBACK;
  ui.cartLink.setAttribute('aria-label', t('cartAria') + count);
  ui.cartLink.title = count ? String(count) + ' ' + t('unitsShort') + ' · ' + money(totalSum(cart.items)) : t('emptyCart');
}

function setCartItems(items: CartItem[] | undefined, checkoutUrl?: string) {
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

function cartItemStock(item: CartItem) {
  const product = productRegistry.get(String(item.product_id));
  return Math.max(0, Number(item.stock ?? (product && product.stock) ?? item.available_quantity ?? 0));
}

function localizedUnit(productId: number, unit?: string) {
  if (Number(productId) === Number(fixtures.cable.id)) return t('meterUnit');
  if ([fixtures.breaker.id, Number(fixtures.breaker.analogs[0].id)].includes(Number(productId)) && ['шт.', 'pcs.', 'дана'].includes(unit || '')) return t('pieceUnit');
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
  ui.shippingBar.style.transform = 'scaleX(' + progress / 100 + ')';
  ui.shippingBar.parentElement?.setAttribute('aria-valuenow', String(Math.round(progress)));
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

function updateCartQuantity(productId: number, change: number) {
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

function removeCartItem(productId: number) {
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

async function fetchTimeout(url: string, options: RequestInit = {}, timeout = 2500) {
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
      const data = await response.json() as CartResponse;
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
    const saved = JSON.parse(localStorage.getItem(DEMO_CART_KEY) || 'null') as Partial<Cart> | null;
    if (saved && Array.isArray(saved.items)) setCartItems(saved.items, saved.checkout_url);
    else updateCartHeader();
  } catch {
    updateCartHeader();
  }
}

function updateLauncherLabel() {
  const isOpen = ui.widget.getAttribute('aria-hidden') === 'false';
  const labels = {
    ru: ['Открыть чат ChipAI', 'Закрыть чат ChipAI'],
    kz: ['ChipAI чатын ашу', 'ChipAI чатын жабу'],
    en: ['Open ChipAI chat', 'Close ChipAI chat'],
  };
  ui.launcher.setAttribute('aria-label', labels[language][isOpen ? 1 : 0]);
}

function openChat() {
  window.clearTimeout(chatFocusTimer);
  ui.widget.inert = false;
  ui.widget.setAttribute('aria-hidden', 'false');
  ui.launcher.setAttribute('aria-expanded', 'true');
  document.body.classList.add('chat-open');
  updateLauncherLabel();
  chatFocusTimer = window.setTimeout(() => ui.input.focus(), 70);
}

function closeChat() {
  window.clearTimeout(chatFocusTimer);
  ui.launcher.focus();
  ui.widget.inert = true;
  ui.widget.setAttribute('aria-hidden', 'true');
  ui.launcher.setAttribute('aria-expanded', 'false');
  document.body.classList.remove('chat-open');
  updateLauncherLabel();
}

function timeNow() {
  const locale = language === 'en' ? 'en-KZ' : language === 'kz' ? 'kk-KZ' : 'ru-RU';
  return new Intl.DateTimeFormat(locale, { hour: '2-digit', minute: '2-digit' }).format(new Date());
}

function scrollToBottom() {
  ui.messages.scrollTop = ui.messages.scrollHeight;
}

function appendUserMessage(text: string, files: File[]) {
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

function renderReasoning(steps: ReasoningStep[], live = false) {
  return renderReasoningTimeline(steps, {
    title: t('reasoning'), fallback: t('fallbackAnswer'), count: t('stepCount'), types: t('typeLabels'),
    stateLabels: t('reasoningStates'),
  }, live);
}

function renderProcessingReasoning() {
  return renderReasoning([{ type: 'intent', status: 'running', message: t('processing') }], true);
}

function normaliseProduct(source: ProductSource, fallbackId?: number): Product {
  source = source || {};
  const id = Number(source.product_id || source.id || fallbackId || 800000);
  const certificateUrl = safeExternalUrl(source.certificate_url || source.certificate_link || (typeof source.certificate === 'string' ? source.certificate : null));
  let specifications = source.specifications || [];
  if (typeof specifications === 'string') specifications = specifications.replaceAll(';', ',').split(',').map((item) => item.trim()).filter(Boolean);
  if (!Array.isArray(specifications)) specifications = [];
  const product: Product = {
    id: Number.isFinite(id) ? id : Number(fallbackId || 800000),
    brand: source.brand || source.manufacturer || 'Каталог ekt.kz',
    name: source.name || source.title || 'Товар из каталога ekt.kz',
    article: source.article || source.sku || '—',
    price: Number(source.price) || 0,
    stock: Math.max(0, Number(source.quantity ?? source.stock ?? source.available_quantity ?? 0)),
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

function renderQuantityControl(product: Product) {
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

function renderAnalog(analog: Product) {
  const stock = Number(analog.stock) || 0;
  const price = analog.price ? money(analog.price) : t('unknownPrice');
  const rationale = analog.rationale || t('fallbackAnswer');
  return '<div class="analog-block"><div class="analog-heading"><svg class="icon"><use href="#i-spark"></use></svg>' + t('analogTitle') + '</div>' +
    '<p class="analog-reason">' + escapeHtml(rationale) + '</p>' +
    '<div class="analog-offer" data-product-card="' + escapeHtml(analog.id) + '">' +
      '<div class="analog-product"><span class="product-visual"><svg class="icon"><use href="#i-bolt"></use></svg></span>' +
        '<span class="analog-copy"><strong>' + escapeHtml(analog.name) + '</strong><small>' + escapeHtml(analog.article) + ' · ' + price + ' · ' + stock + ' ' + escapeHtml(analog.unit) + ' ' + t('demoStock') + '</small></span></div>' +
      renderSpecs(analog) + renderQuantityControl(analog) +
    '</div></div>';
}

function renderSpecs(product: Product): string {
  const specs = product.specifications.slice(0, 4).map((spec) => '<span>' + escapeHtml(spec) + '</span>').join('');
  const certificate = product.certificate ? '<span class="spec-certificate"><svg class="icon"><use href="#i-shield"></use></svg>ГОСТ</span>' : '';
  return '<div class="product-specs">' + certificate + (specs || '<span>' + t('unknownSpecs') + '</span>') + '</div>';
}

function renderProductCard(product: Product) {
  const inStock = Number(product.stock) > 0;
  const stockText = inStock ? String(product.stock) + ' ' + (product.unit || 'шт.') + ' ' + t('inStock') : t('stockEmpty');
  let certificate = '';
  if (product.certificateUrl) {
    certificate = '<a class="certificate-link" href="' + escapeHtml(product.certificateUrl) + '" target="_blank" rel="noreferrer"><svg class="icon"><use href="#i-file"></use></svg>' + t('certificateLink') + '</a>';
  } else if (product.certificate) {
    certificate = '<a class="certificate-link" href="#demo-certificate" data-certificate-download data-article="' + escapeHtml(product.article) + '"><svg class="icon"><use href="#i-file"></use></svg>' + t('certificateLink') + '</a>';
  }
  const analogs = !inStock ? product.analogs.map(renderAnalog).join('') : '';
  const price = product.price ? money(product.price) + (product.unit === 'м' ? ' / м' : '') : t('unknownPrice');
  return '<article class="product-card" data-product-card="' + escapeHtml(product.id) + '">' +
    '<div class="product-topline"><span class="product-brand">' + escapeHtml(product.brand) + '</span>' +
      '<span class="stock-badge ' + (inStock ? '' : 'out-of-stock') + '">' + escapeHtml(stockText) + '</span></div>' +
    '<div class="product-body"><div class="product-title-row"><span class="product-visual"><svg class="icon"><use href="#i-bolt"></use></svg></span>' +
      '<span class="product-title-group"><h3>' + escapeHtml(product.name) + '</h3><span class="product-article">' + t('article') + ' ' + escapeHtml(product.article) + '</span></span></div>' +
      renderSpecs(product) + '<div class="product-meta"><strong class="product-price">' + price + '</strong>' +
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

function appendAssistantMessage(reply: AssistantReply) {
  const scenarioAttribute = reply.scenario ? ' data-demo-scenario="' + escapeHtml(reply.scenario) + '"' : '';
  ui.messages.insertAdjacentHTML('beforeend',
    '<div class="message-row assistant-row"' + scenarioAttribute + '><span class="message-avatar"><svg class="icon"><use href="#i-bolt"></use></svg></span>' +
    '<div class="message-stack"><div class="message-bubble assistant-bubble">' + renderAssistantContent(reply) +
    '</div><time class="message-time">' + timeNow() + '</time></div></div>',
  );
  scrollToBottom();
}

function renderAssistantContent(reply: AssistantReply) {
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
    '<div class="message-stack"><div class="message-bubble assistant-bubble">' + renderProcessingReasoning() + '<span class="typing-indicator" aria-hidden="true"><i></i><i></i><i></i></span></div></div></div>',
  );
  scrollToBottom();
  return id;
}

function demoReply(text: string): AssistantReply {
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

function quickScenarioReply(scenario: Scenario): AssistantReply {
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

function isCartIntent(text: string) {
  const query = String(text || '').trim().toLocaleLowerCase('ru');
  return query.includes('корзин') || query.includes('добав') || query.includes('оформ') || query.includes('заказ') || query.includes('закаж') ||
    query.includes('себет') || query.includes('қос') || query.includes('тапсырыс') || query.includes('рәсімде');
}

async function assistantReply(text: string, files: File[]): Promise<AssistantReply> {
  if (files.length) {
    return {
      isDemo: true,
      answer: t('fileResponse'),
      steps: [
        { type: 'attachment', status: 'completed', message: t('attachmentChecked') },
        { type: 'integration', status: 'pending', message: t('uploadPending') },
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
      const data = await response.json() as ChatResponse;
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
      console.info('Using local demo response:', error instanceof Error ? error.message : String(error));
    }
  }
  await new Promise((resolve) => window.setTimeout(resolve, 380));
  return demoReply(text);
}

function toast(message: string, isError = false) {
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

function addFiles(list: FileList | null) {
  const allowed = ['pdf', 'xls', 'xlsx', 'jpg', 'jpeg', 'png', 'webp'];
  Array.from(list || []).forEach((file) => {
    const extension = (file.name.split('.').pop() || '').toLowerCase();
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

function readDemoCart(): CartItem[] | null {
  try {
    const raw = localStorage.getItem(DEMO_CART_KEY);
    if (!raw) return null;
    const saved = JSON.parse(raw) as Partial<Cart> | null;
    return saved && Array.isArray(saved.items) ? saved.items : null;
  } catch {
    return null;
  }
}

function remainingStock(product: Product) {
  const existing = cart.items.find((item) => Number(item.product_id) === Number(product.id));
  return Math.max(0, Number(product.stock) - (Number(existing ? existing.quantity : 0) || 0));
}

function showConfirmation(card: HTMLElement, quantity: number) {
  const confirmation = card.querySelector<HTMLElement>('[data-cart-confirmation]');
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

async function addToCart(button: HTMLButtonElement) {
  if (button.disabled) return;
  const product = productRegistry.get(String(button.dataset.productId));
  const card = button.closest<HTMLElement>('[data-product-card]');
  const input = card && card.querySelector<HTMLInputElement>('[data-quantity-control] input');
  if (!product || !input || !card) return;
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
      const data = await response.json() as CartResponse;
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
  const data = await response.json() as CartResponse;
  setCartItems(data.items, data.checkout_url);
}

function clampQuantity(input: HTMLInputElement) {
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

async function submitMessage(event: Event | null, promptScenario?: Scenario) {
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
      ? await new Promise<AssistantReply>((resolve) => window.setTimeout(() => resolve(quickScenarioReply(promptScenario)), 800))
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
    if (ui.widget.getAttribute('aria-hidden') === 'false') ui.input.focus();
  }
}

ui.launcher.addEventListener('click', () => {
  if (ui.widget.getAttribute('aria-hidden') === 'false') closeChat();
  else openChat();
});
$('#chat-languages').addEventListener('click', (event) => {
  const selected = event.target instanceof Element ? event.target.closest<HTMLElement>('[data-chat-language]')?.dataset.chatLanguage : undefined;
  if (isLanguage(selected)) setLanguage(selected);
});
$('#language-toggle').addEventListener('click', () => {
  const languages: Language[] = ['ru', 'kz', 'en'];
  setLanguage(languages[(languages.indexOf(language) + 1) % languages.length]);
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
  if (!(event.target instanceof Element)) return;
  const actionButton = event.target.closest<HTMLButtonElement>('[data-cart-action]');
  if (!actionButton) return;
  const item = actionButton.closest<HTMLElement>('[data-cart-item]');
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
ui.fileInput.addEventListener('change', () => {
  addFiles(ui.fileInput.files);
  ui.fileInput.value = '';
});
ui.quickPrompts.addEventListener('click', (event) => {
  if (!(event.target instanceof Element)) return;
  const button = event.target.closest<HTMLButtonElement>('[data-prompt]');
  if (!button) return;
  ui.input.value = button.dataset.prompt || '';
  void submitMessage(null, scenarioFromValue(button.dataset.scenario));
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
  if (!(event.target instanceof Element)) return;
  const button = event.target.closest<HTMLButtonElement>('[data-remove-attachment]');
  if (!button) return;
  attachments.splice(Number(button.dataset.removeAttachment), 1);
  updateAttachmentPreview();
});
ui.messages.addEventListener('click', (event) => {
  if (!(event.target instanceof Element)) return;
  const checkoutLink = event.target.closest<HTMLAnchorElement>('[data-open-cart]');
  if (checkoutLink) {
    event.preventDefault();
    openCartDrawer();
    return;
  }
  const certificate = event.target.closest<HTMLAnchorElement>('[data-certificate-download]');
  if (certificate) {
    event.preventDefault();
    downloadDemoCertificate();
    return;
  }
  const quantityButton = event.target.closest<HTMLButtonElement>('[data-quantity-action]');
  if (quantityButton) {
    const input = quantityButton.closest('[data-quantity-control]')?.querySelector('input');
    if (!input || quantityButton.disabled) return;
    const delta = quantityButton.dataset.quantityAction === 'plus' ? 1 : -1;
    input.value = String(Math.min(Number(input.max) || 1, Math.max(1, (Number(input.value) || 1) + delta)));
    return;
  }
  const addButton = event.target.closest<HTMLButtonElement>('[data-add-cart]');
  if (addButton) addToCart(addButton);
});
ui.messages.addEventListener('change', (event) => {
  if (event.target instanceof HTMLInputElement && event.target.matches('[data-quantity-control] input')) clampQuantity(event.target);
});

function scenarioFromValue(value: string | undefined): Scenario | undefined {
  return value === 'cable' || value === 'analog' || value === 'delivery' ? value : undefined;
}

ui.widget.inert = ui.widget.getAttribute('aria-hidden') !== 'false';
normaliseProduct(fixtures.breaker);
normaliseProduct(fixtures.cable);
updateCartHeader();
applyLanguage();
connectBackend();
