import { mountChipMascot } from './mountChipMascot';
import type { ChipMascotState } from './components/ChipMascot';
import { copy } from './chat/i18n';
import { element as $, escapeHtml as esc, safeExternalUrl } from './chat/dom';
import { renderReasoningTimeline } from './chat/reasoning';
import { ApiClient, apiLanguage } from './chat/api';
import { canOffer, normaliseProduct, offeredQuantity } from './chat/products';
import type { Cart, CartResult, ChatResponse, HistoryMessage, Language, Offer, Product, ProductSource, ReasoningStep, UploadResponse } from './chat/types';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';
let storage: Storage | undefined;
try { storage = localStorage; } catch { /* Private browsing keeps the session in memory. */ }
const api = new ApiClient(API_BASE, fetch, storage);
const LANGUAGE_KEY = 'ekt-widget-language';
const ui = {
  launcher: $<HTMLButtonElement>('#chat-launcher'), widget: $('#chat-widget'), close: $('#close-chat'),
  minimize: $('#minimize-chat'), messages: $('#messages'), quickPrompts: $('#quick-prompts'),
  form: $<HTMLFormElement>('#chat-form'), input: $<HTMLTextAreaElement>('#message-input'),
  send: $<HTMLButtonElement>('#send-button'), attach: $<HTMLButtonElement>('#attach-button'),
  fileInput: $<HTMLInputElement>('#file-input'), attachmentPreview: $('#attachment-preview'),
  cartCount: $('#header-cart-count'), cartLink: $<HTMLAnchorElement>('#store-cart-link'),
  drawerBackdrop: $('#cart-drawer-backdrop'), drawer: $('#cart-drawer'), drawerClose: $('#cart-drawer-close'),
  drawerItems: $('#cart-drawer-items'), checkout: $<HTMLButtonElement>('#cart-checkout-button'),
  toasts: $('#toast-region'),
};
const mascots = [mountChipMascot($('#launcher-chip-mascot'), 58), mountChipMascot($('#header-chip-mascot'), 48),
  mountChipMascot(document.querySelector('#welcome-chip-mascot'), 88)];
let mascotTimer: number | undefined;
function setMascot(state: ChipMascotState) {
  clearTimeout(mascotTimer);
  mascots.forEach((m) => m.setState(state));
  if (state === 'success') mascotTimer = window.setTimeout(() => setMascot('idle'), 1800);
}
function isLanguage(value: unknown): value is Language { return value === 'ru' || value === 'kz' || value === 'en'; }
let language: Language = (() => { try { const value = storage?.getItem(LANGUAGE_KEY); return isLanguage(value) ? value : 'ru'; } catch { return 'ru'; } })();
const l = (ru: string, kk: string, en: string) => language === 'kz' ? kk : language === 'en' ? en : ru;
const t = () => copy[language];
let cart: Cart = { items: [], checkout_url: null };
let cartLoaded = false;
let attachments: File[] = [];
const history: HistoryMessage[] = [];
const products = new Map<number, Product>();
let busy = false;
let cartBusy = false;
let pending: Offer | null = null;
let pendingDeadline = 0;
let pendingEpoch = 0;
let confirmationBusy = false;
let toastTimer: number | undefined;
let focusTimer: number | undefined;

const offerDialog = document.createElement('dialog');
offerDialog.className = 'offer-dialog';
offerDialog.setAttribute('aria-labelledby', 'offer-title');
document.body.append(offerDialog);
api.onSessionReset = () => {
  cart = { items: [], checkout_url: null };
  cartLoaded = false;
  history.length = 0;
  clearOffers();
  renderCart();
};
function money(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return t().unknownPrice;
  return new Intl.NumberFormat(language === 'kz' ? 'kk-KZ' : language === 'en' ? 'en-KZ' : 'ru-KZ', { maximumFractionDigits: 2 }).format(value) + ' ₸';
}
function errorText(error: unknown): string { return error instanceof Error ? error.message : t().requestError; }
function toast(message: string, error = false) {
  clearTimeout(toastTimer);
  ui.toasts.innerHTML = '<div class="toast ' + (error ? 'toast-error' : '') + '">' + esc(message) + '</div>';
  toastTimer = window.setTimeout(() => { ui.toasts.innerHTML = ''; }, error ? 9000 : 4000);
}
function safeLink(url: string | null | undefined, label: string, className = ''): string {
  const safe = safeExternalUrl(url);
  return safe ? '<a class="' + className + '" href="' + esc(safe) + '" target="_blank" rel="noopener noreferrer">' + esc(label) + '</a>' : '';
}
function renderText(text: string): string {
  // Escape prose; turn only explicit http(s) Markdown links into anchors.
  return text.split('\n').map((line) => {
    let cursor = 0;
    let html = '';
    for (const match of line.matchAll(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g)) {
      html += esc(line.slice(cursor, match.index));
      html += safeLink(match[2], match[1]);
      cursor = (match.index || 0) + match[0].length;
    }
    return '<p>' + html + esc(line.slice(cursor)).replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>') + '</p>';
  }).join('');
}
function warnings(items: string[] = []): string {
  return items.length ? '<ul class="data-warnings">' + items.map((item) => '<li>' + esc(item) + '</li>').join('') + '</ul>' : '';
}
function timeNow(): string { return new Intl.DateTimeFormat(language === 'en' ? 'en-KZ' : 'ru-KZ', { hour: '2-digit', minute: '2-digit' }).format(new Date()); }
function scrollBottom() { ui.messages.scrollTop = ui.messages.scrollHeight; }
function appendMessage(html: string, user = false): HTMLElement {
  const row = document.createElement('div');
  row.className = 'message-row ' + (user ? 'user-row' : 'assistant-row');
  row.innerHTML = '<span class="message-avatar" aria-hidden="true"><svg class="icon"><use href="#i-bolt"></use></svg></span>' +
    '<div class="message-stack"><div class="message-bubble ' + (user ? 'user-bubble' : 'assistant-bubble') + '">' + html +
    '</div><time class="message-time">' + timeNow() + '</time></div>';
  ui.messages.append(row);
  scrollBottom();
  return row;
}
function reasoning(steps: ReasoningStep[], live = false): string {
  return renderReasoningTimeline(steps, { title: t().reasoning, fallback: t().processing,
    count: (n) => String(n), types: {}, stateLabels: t().reasoningStates }, live);
}
function register(source: ProductSource): Product | null {
  const product = normaliseProduct(source);
  if (product) { products.set(product.id, product); product.analogs.forEach((a) => products.set(a.id, a)); }
  return product;
}
function quantityControl(product: Product, requested?: number | null): string {
  if (!canOffer(product)) return '';
  const initial = requested && requested >= product.minimum ? requested : product.minimum;
  return '<div class="quantity-row"><span class="quantity-label">' + t().quantity + '</span><div class="quantity-control" data-quantity-control>' +
    '<button type="button" data-quantity-action="minus" aria-label="' + t().quantityDown + '">−</button>' +
    '<input type="number" min="' + product.minimum + '" step="' + product.multiple + '" max="' + product.stock + '" value="' + initial + '" inputmode="numeric" aria-label="' + t().quantity + '">' +
    '<button type="button" data-quantity-action="plus" aria-label="' + t().quantityUp + '">+</button></div></div>' +
    '<button type="button" class="add-cart-button" data-add-cart data-product-id="' + product.id + '">' + t().add + '</button>';
}
function renderProduct(product: Product, requested?: number | null): string {
  const stock = product.stockVerified && product.stock !== null ? product.stock + ' ' + product.unit : t().unknownStock;
  const date = product.checkedAt && !Number.isNaN(Date.parse(product.checkedAt))
    ? new Date(product.checkedAt).toLocaleString(language === 'kz' ? 'kk-KZ' : language === 'en' ? 'en-KZ' : 'ru-KZ') : '';
  return '<article class="product-card" data-product-card="' + product.id + '">' +
    '<div class="product-topline"><span class="product-brand">' + esc(product.brand) + '</span><span class="stock-badge' + (!product.stock ? ' out-of-stock' : '') + '">' + esc(stock) + '</span></div>' +
    '<div class="product-body"><h3>' + esc(product.name) + '</h3><p class="product-article">' + t().article + ': ' + esc(product.article) + '</p>' +
    '<div class="product-specs">' + product.specifications.map((spec) => '<span>' + esc(spec) + '</span>').join('') + '</div>' +
    '<strong class="product-price">' + money(product.priceVerified ? product.price : null) + '</strong>' +
    (product.rationale ? '<p class="analog-reason">' + esc(product.rationale) + '</p>' : '') +
    warnings(product.warnings) + (date ? '<small class="checked-at">' + t().checkedAt + ': ' + esc(date) + '</small>' : '') +
    (product.stores.length ? '<details class="stock-details"><summary>' + t().stores + '</summary><ul>' +
      product.stores.map((store) => '<li>' + esc(store.name) + ': ' + (store.quantity === null ? t().unknownStock : store.quantity) + '</li>').join('') + '</ul></details>' : '') +
    safeLink(product.certificateUrl, t().certificateLink, 'certificate-link') + safeLink(product.url, t().productLink, 'certificate-link') +
    quantityControl(product, requested) + product.analogs.map((a) => renderProduct(a)).join('') + '</div></article>';
}
function countCart() { return cart.items.reduce((sum, item) => sum + item.quantity, 0); }
function renderCart() {
  const count = countCart();
  ui.cartCount.textContent = count > 99 ? '99+' : String(count);
  ui.cartLink.href = safeExternalUrl(cart.checkout_url) || '#';
  ui.cartLink.setAttribute('aria-label', t().cart + ': ' + count);
  $('#cart-drawer-count').textContent = count + ' ' + t().units;
  $('#cart-total').textContent = money(cart.total_sum ?? cart.items.reduce((sum, item) => sum + item.quantity * item.price, 0));
  ui.checkout.disabled = !cartLoaded || !cart.items.length || cartBusy;
  ui.drawerItems.innerHTML = !cartLoaded ? '<p class="cart-state">' + t().cartLoading + '</p>' : !cart.items.length
    ? '<div class="cart-empty-state"><strong>' + t().emptyCart + '</strong><p>' + t().emptyCopy + '</p></div>'
    : cart.items.map((item) => '<article class="cart-line" data-cart-item="' + item.product_id + '"><div class="cart-line-top"><div class="cart-line-copy"><h3>' + esc(item.name) + '</h3>' +
      '<span class="cart-line-article">' + esc(item.article) + '</span></div><button class="cart-remove-button" type="button" data-cart-action="remove" aria-label="' + t().remove + '"' + (cartBusy ? ' disabled' : '') + '>×</button></div>' +
      '<div class="cart-line-bottom"><div class="cart-line-price"><strong>' + money(item.price) + '</strong><span>× ' + item.quantity + ' = ' + money(item.price * item.quantity) + '</span></div>' +
      '<div class="cart-quantity-control"><button type="button" data-cart-action="minus" aria-label="' + t().quantityDown + '"' + (cartBusy ? ' disabled' : '') + '>−</button><span>' + item.quantity + '</span>' +
      '<button type="button" data-cart-action="plus" aria-label="' + t().quantityUp + '"' + (cartBusy ? ' disabled' : '') + '>+</button></div></div></article>').join('');
}
async function refreshCart() {
  cart = await api.request<Cart>('/cart');
  cartLoaded = true;
  renderCart();
}
async function openCart() {
  ui.drawerBackdrop.hidden = false;
  ui.drawer.inert = false;
  ui.drawer.setAttribute('aria-hidden', 'false');
  document.body.classList.add('cart-drawer-open');
  cartLoaded = false;
  renderCart();
  ui.drawerClose.focus();
  try { await refreshCart(); }
  catch (error) {
    ui.drawerItems.innerHTML = '<p class="data-warnings">' + esc(errorText(error)) + '</p><button type="button" class="add-cart-button" data-refresh-cart>' + t().retry + '</button>';
  }
}
function closeCart() {
  ui.drawerBackdrop.hidden = true;
  ui.drawer.inert = true;
  ui.drawer.setAttribute('aria-hidden', 'true');
  document.body.classList.remove('cart-drawer-open');
  ui.cartLink.focus();
}
function clearOffers() {
  pending = null;
  pendingEpoch++;
  if (offerDialog.open) offerDialog.close();
  ui.messages.querySelectorAll<HTMLButtonElement>('[data-review-offer]').forEach((button) => { button.disabled = true; });
}
function acceptOffer(offer: Offer): number {
  clearOffers();
  pending = offer;
  pendingDeadline = Date.now() + offer.expires_in_seconds * 1000;
  return pendingEpoch;
}
function offerMarkup(offer: Offer): string {
  const change = offer.operation === 'set_quantity';
  return '<h2 id="offer-title">' + (change ? t().confirmChange : t().confirmAdd) + '</h2><p><strong>' + esc(offer.product_name) + '</strong></p>' +
    '<p>' + t().article + ': ' + esc(offer.article) + '</p><p>' + t().quantity + ': <strong>' +
    (change ? offer.previous_quantity + ' → ' : '') + offer.quantity + '</strong></p>' +
    '<p>' + t().price + ': ' + money(offer.price) + ' · ' + t().total + ': ' + money(offer.quantity * offer.price) + '</p>' +
    (offer.stock_available !== null ? '<p>' + t().stock + ': ' + offer.stock_available + '</p>' : '') +
    warnings(offer.data_quality_warnings) + '<p class="cart-demo-note">' + t().demoOrder + '</p>';
}
function reviewOffer() {
  if (!pending) return;
  if (Date.now() >= pendingDeadline) { clearOffers(); toast(t().offerExpired, true); return; }
  offerDialog.innerHTML = offerMarkup(pending) + '<div class="offer-actions"><button class="add-cart-button" type="button" data-confirm-offer>' + t().confirm + '</button>' +
    '<button class="offer-cancel" type="button" data-cancel-offer>' + t().cancel + '</button></div>';
  offerDialog.showModal();
}
function inlineOffer(offer: Offer): string {
  const epoch = acceptOffer(offer);
  return '<section class="pending-offer"><strong>' + t().offered + '</strong><p>' + esc(offer.product_name) + ' · ' + offer.quantity + ' × ' + money(offer.price) + '</p>' +
    warnings(offer.data_quality_warnings) + '<button class="add-cart-button" type="button" data-review-offer="' + epoch + '">' + t().review + '</button></section>';
}
async function prepareOffer(productId: number, quantity: number, change = false) {
  if (cartBusy || busy || confirmationBusy) return;
  if (!Number.isSafeInteger(quantity) || quantity < (change ? 0 : 1)) { toast(t().quantityError, true); return; }
  cartBusy = true;
  renderCart();
  clearOffers();
  try {
    const offer = await api.post<Offer>(change ? '/cart/change-offer' : '/cart/offer', { product_id: productId, quantity });
    acceptOffer(offer);
    reviewOffer();
  } catch (error) { toast(errorText(error), true); }
  finally { cartBusy = false; renderCart(); }
}
async function confirmOffer() {
  if (!pending || confirmationBusy) return;
  if (Date.now() >= pendingDeadline) { clearOffers(); toast(t().offerExpired, true); return; }
  const offer = pending;
  confirmationBusy = true;
  offerDialog.querySelectorAll<HTMLButtonElement>('button').forEach((button) => { button.disabled = true; });
  try {
    const result = await api.post<CartResult>(offer.operation === 'set_quantity' ? '/cart/change' : '/cart/add', {
      product_id: offer.product_id, quantity: offer.quantity, confirmed: true, offer_token: offer.offer_token,
    });
    cart = Array.isArray(result.cart) ? { items: result.cart, checkout_url: result.cart_url } : result.cart;
    cartLoaded = true;
    renderCart();
    clearOffers();
    appendMessage(renderText(result.answer || result.message || t().success) + safeLink(result.cart_url, t().checkout, 'certificate-link'));
    setMascot('success');
  } catch (error) {
    clearOffers();
    toast(errorText(error), true);
    // A timed-out write may have committed. Read once; never replay the write.
    try { await refreshCart(); } catch { cartLoaded = false; renderCart(); }
  } finally { confirmationBusy = false; }
}
async function showChat(text: string) {
  const sessionId = await api.session();
  const data = await api.post<ChatResponse>('/agent/chat', {
    session_id: sessionId, message: text, history: history.slice(-10), language: apiLanguage(language),
  }, 60000);
  clearOffers();
  const cards = (data.sources || []).map(register).filter((p): p is Product => !!p);
  let content = reasoning(data.reasoning_steps || []) + renderText(data.answer) + warnings(data.warnings) +
    cards.map((product) => renderProduct(product, offeredQuantity(product, data.pending_offer))).join('') +
    (data.knowledge_sources || []).map((source) => safeLink(source.source_url, source.title, 'certificate-link')).join('');
  if (data.pending_offer) content += inlineOffer(data.pending_offer);
  if (data.cart_updated && data.cart_url) content += safeLink(data.cart_url, t().checkout, 'certificate-link');
  appendMessage(content);
  history.push({ role: 'user', content: text }, { role: 'assistant', content: data.answer.slice(0, 4000) });
  if (history.length > 10) history.splice(0, history.length - 10);
  if (data.cart_updated) {
    try { await refreshCart(); }
    catch (error) { cartLoaded = false; renderCart(); toast(errorText(error), true); }
  }
}
function renderEstimate(data: UploadResponse): string {
  const estimate = data.estimate;
  let html = '<section class="spec-estimate"><h3>' + esc(data.filename) + '</h3>' + renderText(estimate.summary_text) +
    '<strong>' + (estimate.estimate_complete ? t().total : t().partialTotal) + ': ' + money(estimate.total_estimate_kzt) + '</strong>' +
    warnings(estimate.warnings) + '<p class="cart-demo-note">' + t().uploadGuard + '</p>';
  for (const match of estimate.matched_items) {
    const product = register({ ...match, price: match.unit_price, quantity: match.stock_available,
      analogs: match.analog ? [match.analog] : [] });
    html += '<section class="estimate-row"><p><strong>' + esc(match.query_line) + '</strong></p><p>' +
      t().quantity + ': ' + (match.quantity === null ? t().clarify : match.quantity) + ' · ' + t().subtotal + ': ' + money(match.subtotal) + '</p><p>' + esc(match.status) + '</p>' +
      warnings(match.quantity_warning ? [match.quantity_warning] : []) + (product ? renderProduct(product, match.quantity) : '') + '</section>';
  }
  if (estimate.unmatched_items.length) html += '<h4>' + t().unmatched + '</h4><ul class="unmatched-lines">' + estimate.unmatched_items.map((line) =>
    '<li><strong>' + esc(line.query_line) + '</strong><p>' + esc(line.status) + '</p>' + warnings(line.quantity_warning ? [line.quantity_warning] : []) +
    (line.candidates?.length ? '<p>' + line.candidates.map((candidate) => esc(candidate.name) + ' (ID ' + candidate.id + ')').join('; ') + '</p>' : '') + '</li>').join('') + '</ul>';
  if (estimate.ignored_lines.length) html += '<details><summary>' + t().ignored + '</summary><ul>' + estimate.ignored_lines.map((line) => '<li>' + esc(line) + '</li>').join('') + '</ul></details>';
  return html + '</section>';
}
async function upload(file: File) {
  const body = new FormData();
  body.append('file', file);
  const result = await api.request<UploadResponse>('/agent/upload-spec', { method: 'POST', body }, 180000);
  appendMessage(renderEstimate(result));
}
function attachmentPreview() {
  ui.attachmentPreview.hidden = !attachments.length;
  ui.attachmentPreview.innerHTML = attachments.map((file, index) => '<span class="attachment-chip"><span>' + esc(file.name) +
    '</span><button type="button" data-remove-attachment="' + index + '" aria-label="' + t().remove + '">×</button></span>').join('');
}
function addFiles(list: FileList | null) {
  for (const file of Array.from(list || [])) {
    if (!/\.(pdf|txt|docx|xlsx|xls|jpe?g|png|webp)$/i.test(file.name)) { toast(t().fileFormats, true); continue; }
    if (!file.size || file.size > 15 * 1024 * 1024) { toast(file.name + ': ' + t().fileSize, true); continue; }
    if (!attachments.some((f) => f.name === file.name && f.size === file.size)) attachments.push(file);
  }
  attachmentPreview();
}
async function submitMessage(event?: Event) {
  event?.preventDefault();
  if (busy || cartBusy || confirmationBusy) return;
  const text = ui.input.value.trim();
  const files = [...attachments];
  if (!text && !files.length) return;
  if (text.length > 4000) { toast(t().messageLimit, true); return; }
  appendMessage(renderText(text) + files.map((file) => '<p>📎 ' + esc(file.name) + '</p>').join(''), true);
  ui.input.value = '';
  ui.input.style.height = 'auto';
  attachments = [];
  attachmentPreview();
  busy = true;
  ui.send.disabled = true;
  ui.attach.disabled = true;
  ui.quickPrompts.querySelectorAll<HTMLButtonElement>('button').forEach((button) => { button.disabled = true; });
  setMascot('thinking');
  const typing = appendMessage(reasoning([{ type: 'intent', status: 'running', message: t().processing }], true));
  try {
    // Keep attachment results separate from a free-text request: file rows never authorize a cart write.
    if (text) await showChat(text);
    for (const file of files) {
      try { await upload(file); }
      catch (error) {
        appendMessage('<p class="data-warnings">' + esc(file.name + ': ' + errorText(error)) + '</p>');
        attachments.push(file);
      }
    }
    attachmentPreview();
    setMascot('success');
  } catch (error) {
    appendMessage('<p class="data-warnings" role="alert">' + esc(errorText(error)) + '</p>');
    ui.input.value = text;
    attachments = files;
    attachmentPreview();
    setMascot('idle');
  } finally {
    typing.remove();
    busy = false;
    ui.send.disabled = false;
    ui.attach.disabled = false;
    ui.quickPrompts.querySelectorAll<HTMLButtonElement>('button').forEach((button) => { button.disabled = false; });
    scrollBottom();
    if (ui.widget.getAttribute('aria-hidden') === 'false') ui.input.focus();
  }
}
function openChat() {
  clearTimeout(focusTimer);
  ui.widget.inert = false;
  ui.widget.setAttribute('aria-hidden', 'false');
  ui.launcher.setAttribute('aria-expanded', 'true');
  document.body.classList.add('chat-open');
  updateLauncher();
  focusTimer = window.setTimeout(() => ui.input.focus(), 70);
}
function closeChat() {
  clearTimeout(focusTimer);
  ui.launcher.focus();
  ui.widget.inert = true;
  ui.widget.setAttribute('aria-hidden', 'true');
  ui.launcher.setAttribute('aria-expanded', 'false');
  document.body.classList.remove('chat-open');
  updateLauncher();
}
function updateLauncher() {
  ui.launcher.setAttribute('aria-label', ui.widget.getAttribute('aria-hidden') === 'false' ? t().closeChat : t().openChat);
}
function applyLanguage() {
  document.documentElement.lang = language === 'kz' ? 'kk' : language;
  for (const [selector, value] of Object.entries({
    '#cart-label': t().cart, '#assistant-name-text': 'ChipAI', '#launcher-label-text': 'ChipAI',
    '#online-label': t().consultant, '#assistant-role': t().role, '#catalog-help': t().catalogHelp,
    '#reply-time-label': t().replyTime, '#welcome-kicker': t().welcomeKicker, '#welcome-copy': t().welcome,
    '#welcome-hint': t().welcomeHint, '#welcome-time': t().welcomeTime, '#composer-send-hint': t().composerSendHint,
    '#composer-newline-hint': t().composerNewlineHint, '#footer-assistant-label': t().footer,
    '#demo-data-label': language === 'en' ? 'Replies in Russian' : t().catalogData,
    '#cart-drawer-title': t().cart, '#cart-total-label': t().total, '#cart-checkout-button': t().checkout,
    '#cart-demo-note': t().demoOrder, '#shipping-progress-copy': t().deliveryNote,
  })) $(selector).textContent = value;
  ui.widget.setAttribute('aria-label', t().assistant);
  ui.input.placeholder = t().placeholder;
  ui.input.setAttribute('aria-label', t().messageLabel);
  ui.send.setAttribute('aria-label', t().send);
  ui.attach.setAttribute('aria-label', t().attach);
  ui.attach.title = t().fileFormats;
  ui.close.setAttribute('aria-label', t().closeChat);
  ui.minimize.setAttribute('aria-label', t().closeChat);
  ui.drawerClose.setAttribute('aria-label', t().closeCart);
  $('#language-toggle').setAttribute('aria-label', 'RU / KZ / EN');
  document.querySelectorAll<HTMLElement>('[data-language-option]').forEach((option) => option.classList.toggle('is-current', option.dataset.languageOption === language));
  document.querySelectorAll<HTMLButtonElement>('[data-chat-language]').forEach((button) => {
    button.classList.toggle('is-current', button.dataset.chatLanguage === language);
    button.setAttribute('aria-pressed', String(button.dataset.chatLanguage === language));
  });
  ui.quickPrompts.querySelectorAll('[data-prompt-label]').forEach((label, index) => {
    label.textContent = t().prompts[index];
    if (label.parentElement) label.parentElement.dataset.prompt = t().promptQueries[index];
  });
  $('#shipping-progress-bar').parentElement?.setAttribute('hidden', '');
  renderCart();
  updateLauncher();
}
function setLanguage(value: Language) {
  language = value;
  try { storage?.setItem(LANGUAGE_KEY, value); } catch { /* Keep this tab's preference. */ }
  applyLanguage();
}
ui.launcher.addEventListener('click', () => ui.widget.getAttribute('aria-hidden') === 'false' ? closeChat() : openChat());
ui.close.addEventListener('click', closeChat);
ui.minimize.addEventListener('click', closeChat);
ui.form.addEventListener('submit', (event) => { void submitMessage(event); });
ui.input.addEventListener('input', () => { ui.input.style.height = 'auto'; ui.input.style.height = Math.min(ui.input.scrollHeight, 96) + 'px'; });
ui.attach.addEventListener('click', () => ui.fileInput.click());
ui.fileInput.addEventListener('change', () => { addFiles(ui.fileInput.files); ui.fileInput.value = ''; });
ui.attachmentPreview.addEventListener('click', (event) => {
  const button = event.target instanceof Element ? event.target.closest<HTMLElement>('[data-remove-attachment]') : null;
  if (button) { attachments.splice(Number(button.dataset.removeAttachment), 1); attachmentPreview(); }
});
ui.quickPrompts.addEventListener('click', (event) => {
  const button = event.target instanceof Element ? event.target.closest<HTMLButtonElement>('[data-prompt]') : null;
  if (button && !button.disabled) { ui.input.value = button.dataset.prompt || ''; void submitMessage(); }
});
$('#chat-languages').addEventListener('click', (event) => {
  const value = event.target instanceof Element ? event.target.closest<HTMLElement>('[data-chat-language]')?.dataset.chatLanguage : undefined;
  if (isLanguage(value)) setLanguage(value);
});
$('#language-toggle').addEventListener('click', () => { const all: Language[] = ['ru', 'kz', 'en']; setLanguage(all[(all.indexOf(language) + 1) % all.length]); });
ui.cartLink.addEventListener('click', (event) => { event.preventDefault(); void openCart(); });
ui.drawerClose.addEventListener('click', closeCart);
ui.drawerBackdrop.addEventListener('click', (event) => { if (event.target === ui.drawerBackdrop) closeCart(); });
ui.drawerItems.addEventListener('click', (event) => {
  if (!(event.target instanceof Element)) return;
  if (event.target.closest('[data-refresh-cart]')) { void openCart(); return; }
  const button = event.target.closest<HTMLButtonElement>('[data-cart-action]');
  if (!button || button.disabled) return;
  const id = Number(button.closest<HTMLElement>('[data-cart-item]')?.dataset.cartItem);
  const item = cart.items.find((i) => i.product_id === id);
  if (item) void prepareOffer(id, button.dataset.cartAction === 'remove' ? 0 : item.quantity + (button.dataset.cartAction === 'plus' ? 1 : -1), true);
});
ui.checkout.addEventListener('click', async () => {
  ui.checkout.disabled = true;
  try {
    await refreshCart();
    const url = safeExternalUrl(cart.checkout_url);
    if (url && cart.items.length) window.location.assign(url);
  } catch (error) { toast(errorText(error), true); }
  finally { renderCart(); }
});
ui.messages.addEventListener('click', (event) => {
  if (!(event.target instanceof Element)) return;
  const review = event.target.closest<HTMLButtonElement>('[data-review-offer]');
  if (review && !review.disabled && Number(review.dataset.reviewOffer) === pendingEpoch) { reviewOffer(); return; }
  const quantityButton = event.target.closest<HTMLButtonElement>('[data-quantity-action]');
  if (quantityButton) {
    const input = quantityButton.closest('[data-quantity-control]')?.querySelector('input');
    if (input) input.value = String(Math.max(Number(input.min), Math.min(Number(input.max), Number(input.value) + (quantityButton.dataset.quantityAction === 'plus' ? 1 : -1) * Number(input.step))));
    return;
  }
  const add = event.target.closest<HTMLButtonElement>('[data-add-cart]');
  if (add) {
    const input = add.closest('[data-product-card]')?.querySelector<HTMLInputElement>('[data-quantity-control] input');
    if (input) void prepareOffer(Number(add.dataset.productId), Number(input.value));
  }
});
offerDialog.addEventListener('click', (event) => {
  if (!(event.target instanceof Element)) return;
  if (event.target.closest('[data-confirm-offer]')) void confirmOffer();
  if (event.target.closest('[data-cancel-offer]')) clearOffers();
});
offerDialog.addEventListener('cancel', (event) => {
  if (confirmationBusy) event.preventDefault();
  else clearOffers();
});
document.addEventListener('keydown', (event) => {
  if (offerDialog.open) return;
  if (event.key === 'Escape') {
    if (!ui.drawerBackdrop.hidden) closeCart();
    else if (ui.widget.getAttribute('aria-hidden') === 'false') closeChat();
  }
  if (event.key === 'Tab' && !ui.drawerBackdrop.hidden) {
    const focusable = [...ui.drawer.querySelectorAll<HTMLElement>('button:not([disabled]),a[href],input')];
    const first = focusable[0], last = focusable.at(-1);
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
  }
  if (event.key === 'Enter' && !event.shiftKey && document.activeElement === ui.input) { event.preventDefault(); ui.form.requestSubmit(); }
});
ui.widget.inert = ui.widget.getAttribute('aria-hidden') !== 'false';
ui.drawer.inert = true;
applyLanguage();
void refreshCart().catch(() => {
  cartLoaded = false;
  renderCart();
  $('#online-label').textContent = l('Нет соединения', 'Байланыс жоқ', 'Disconnected');
});
