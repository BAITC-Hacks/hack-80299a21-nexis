import type { Language } from './types';
import { apiLanguage, localizedError } from './localization.ts';
export { apiLanguage } from './localization.ts';

export class ApiError extends Error {
  status: number;
  code: string;
  params: Record<string, unknown>;
  constructor(message: string, status = 0, code = 'network_error', params: Record<string, unknown> = {}) {
    super(message);
    this.status = status;
    this.code = code;
    this.params = params;
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
  private language: Language = 'ru';
  onSessionReset?: () => void;

  constructor(base: string, fetcher: typeof fetch = fetch, storage?: StorageLike) {
    this.base = base.replace(/\/+$/, '');
    this.fetcher = fetcher;
    this.storage = storage;
    try { this.token = storage?.getItem(SESSION_KEY) || null; } catch { /* Private browsing. */ }
  }

  setLanguage(language: Language): void { this.language = language; }

  private async fetchTimed(path: string, options: RequestInit, timeout: number, language: Language): Promise<Response> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeout);
    // Native browser fetch must not receive the ApiClient instance as its receiver.
    const fetcher = this.fetcher;
    const headers = new Headers(options.headers);
    headers.set('X-Language', apiLanguage(language));
    try { return await fetcher(this.base + path, { ...options, headers, signal: controller.signal }); }
    catch (error) {
      const code = error instanceof Error && error.name === 'AbortError' ? 'request_timeout' : 'network_error';
      throw new ApiError(localizedError(code, language), 0, code);
    } finally { clearTimeout(timer); }
  }

  private async error(response: Response, language: Language): Promise<ApiError> {
    const data = await response.json().catch(() => ({})) as { detail?: unknown; code?: string; params?: Record<string, unknown>; answer_language?: string };
    const code = data.code || (response.status === 422 ? 'validation_error' : response.status === 429 ? 'rate_limited' : 'request_error');
    const params = { ...data.params, seconds: response.headers.get('Retry-After') || data.params?.seconds || '60' };
    // v3 prose is rendered only in the language actually requested. Older Russian APIs remain readable in RU.
    const localizedDetail = data.answer_language === apiLanguage(language) || (!data.answer_language && language === 'ru');
    const message = localizedDetail && typeof data.detail === 'string' ? data.detail : localizedError(code, language, params);
    return new ApiError(message, response.status, code, params);
  }

  async session(): Promise<string> {
    if (this.token) return this.token;
    if (!this.creating) {
      const language = this.language;
      this.creating = (async () => {
        const response = await this.fetchTimed('/session', { method: 'POST' }, 15000, language);
        if (!response.ok) throw await this.error(response, language);
        const data = await response.json() as { session_id?: string };
        if (!data.session_id) throw new ApiError(localizedError('session_failed', language), 0, 'session_failed');
        this.token = data.session_id;
        try { this.storage?.setItem(SESSION_KEY, this.token); } catch { /* Keep in memory. */ }
        return this.token;
      })().finally(() => { this.creating = null; });
    }
    return this.creating;
  }

  async request<T>(path: string, options: RequestInit = {}, timeout = 30000, retryRead = true): Promise<T> {
    const language = this.language;
    const token = await this.session();
    const headers = new Headers(options.headers);
    headers.set('X-Session-Id', token);
    const response = await this.fetchTimed(path, { ...options, headers }, timeout, language);
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
      throw new ApiError(localizedError('session_expired', language), 401, 'session_expired');
    }
    if (!response.ok) throw await this.error(response, language);
    return response.json() as Promise<T>;
  }

  post<T>(path: string, body: unknown, timeout = 30000): Promise<T> {
    return this.request<T>(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }, timeout);
  }
}
