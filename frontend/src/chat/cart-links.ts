import { apiLanguage } from './localization.ts';
import type { Language } from './types';

/** Change presentation language only: keep the saved cart's read token and other parameters. */
export function localizedCartUrl(value: string | null | undefined, language: Language): string | null {
  if (!value) return null;
  try {
    const url = new URL(value);
    if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password) return null;
    // Partner checkout and product/document links are separate from our saved-cart pages.
    if (!/\/cart\/[^/]+\/?$/.test(url.pathname)) return value;
    url.searchParams.set('language', apiLanguage(language));
    return url.href;
  } catch { return null; }
}

export function updateCartLinkLanguages(links: Iterable<{ href: string }>, language: Language): void {
  for (const link of links) {
    const localized = localizedCartUrl(link.href, language);
    if (localized && localized !== link.href) link.href = localized;
  }
}
