import type { Language } from './types';

export function apiLanguage(language: Language): 'ru' | 'kk' {
  return language === 'kz' ? 'kk' : 'ru';
}

export class ApiError extends Error {
  status: number;
  code: string;
  constructor(message: string, status = 0, code = 'network_error') {
    super(message);
    this.status = status;
    this.code = code;
  }
}

interface StorageLike { getItem(key: string): string | null; setItem(key: string, value: string): void; removeItem(key: string): void }
const SESSION_KEY = 'ekt-widget-session-v2';

/** One shared session creation promise. Expired writes are never automatically replayed. */
export class ApiClient {
  base: string;
  private fetcher: typeof fetch;
  private storage?: StorageLike;
  private token: string | null = null;
  private creating: Promise<string> | null = null;
  onSessionReset?: () => void;

  constructor(base: string, fetcher: typeof fetch = fetch, storage?: StorageLike) {
    this.base = base.replace(/\/+$/, '');
    this.fetcher = fetcher;
    this.storage = storage;
    try { this.token = storage?.getItem(SESSION_KEY) || null; } catch { /* Private browsing. */ }
  }

  private async fetchTimed(path: string, options: RequestInit, timeout: number): Promise<Response> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeout);
    // Native browser fetch must not receive the ApiClient instance as its receiver.
    const fetcher = this.fetcher;
    try { return await fetcher(this.base + path, { ...options, signal: controller.signal }); }
    catch (error) {
      throw new ApiError(error instanceof Error && error.name === 'AbortError'
        ? 'Ответ задерживается. Проверьте корзину перед повторным подтверждением.'
        : 'Не удалось подключиться к консультанту. Проверьте соединение и повторите запрос.');
    } finally { clearTimeout(timer); }
  }

  private async error(response: Response): Promise<ApiError> {
    const data = await response.json().catch(() => ({})) as { detail?: unknown; code?: string };
    const message = typeof data.detail === 'string' ? data.detail : response.status === 422
      ? 'Проверьте запрос: количество должно быть целым, сообщение — не длиннее 4000 символов.'
      : response.status === 429 ? `Слишком много запросов. Повторите через ${response.headers.get('Retry-After') || '60'} сек.`
      : 'Не удалось выполнить запрос. Повторите позже.';
    return new ApiError(message, response.status, data.code);
  }

  async session(): Promise<string> {
    if (this.token) return this.token;
    if (!this.creating) {
      this.creating = (async () => {
        const response = await this.fetchTimed('/session', { method: 'POST' }, 15000);
        if (!response.ok) throw await this.error(response);
        const data = await response.json() as { session_id?: string };
        if (!data.session_id) throw new ApiError('Не удалось открыть сессию консультанта.');
        this.token = data.session_id;
        try { this.storage?.setItem(SESSION_KEY, this.token); } catch { /* Keep in memory. */ }
        return this.token;
      })().finally(() => { this.creating = null; });
    }
    return this.creating;
  }

  async request<T>(path: string, options: RequestInit = {}, timeout = 30000, retryRead = true): Promise<T> {
    const token = await this.session();
    const headers = new Headers(options.headers);
    headers.set('X-Session-Id', token);
    const response = await this.fetchTimed(path, { ...options, headers }, timeout);
    if (response.status === 401) {
      // Concurrent failures for an old session must not discard a newly created one.
      if (this.token === token) {
        this.token = null;
        try { this.storage?.removeItem(SESSION_KEY); } catch { /* Keep in memory. */ }
        this.onSessionReset?.();
      }
      await this.session();
      if ((options.method || 'GET').toUpperCase() === 'GET' && retryRead) {
        return this.request<T>(path, options, timeout, false);
      }
      throw new ApiError('Сессия истекла. Открыта новая корзина. Повторите запрос и подтвердите товар заново.', 401, 'session_expired');
    }
    if (!response.ok) throw await this.error(response);
    return response.json() as Promise<T>;
  }

  post<T>(path: string, body: unknown, timeout = 30000): Promise<T> {
    return this.request<T>(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }, timeout);
  }
}
