import type { Language, Offer, Product, ProductSource, Specification } from './types';
import { productFallback, specificationLabel, unitFallback } from './localization.ts';

export function nullableNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) && value >= 0 ? value : null;
}
export function productUrl(value: unknown): string | null {
  if (typeof value !== 'string') return null;
  try {
    const url = new URL(value);
    return ['http:', 'https:'].includes(url.protocol) && !url.username && !url.password ? url.href : null;
  } catch { return null; }
}
export function formatSpecifications(specifications: (Specification | string)[], language: Language = 'ru'): string[] {
  return specifications.flatMap((spec) => {
    if (typeof spec === 'string') return [spec];
    if (!spec || typeof spec.name !== 'string') return [];
    const value = Array.isArray(spec.value) ? spec.value.join(', ') : spec.value;
    return typeof value === 'string' || typeof value === 'number' ? [`${specificationLabel(spec.key, spec.name, language)}: ${value}`] : [];
  });
}
export function normaliseProduct(source: ProductSource, language: Language = 'ru'): Product | null {
  const id = Number(source.product_id ?? source.id);
  if (!Number.isSafeInteger(id) || id <= 0) return null;
  const price = nullableNumber(source.price);
  const stock = nullableNumber(source.quantity);
  return {
    id, name: source.name || productFallback(language), article: source.article || '—', brand: source.brand || 'ekt.kz',
    price, stock, priceVerified: source.price_verified === true && price !== null,
    stockVerified: source.stock_verified === true && stock !== null,
    unit: source.unit_display || source.unit || unitFallback(language), originalUnit: source.unit || null,
    specifications: formatSpecifications(Array.isArray(source.specifications) ? source.specifications : [], language),
    specificationEntries: Array.isArray(source.specifications) ? source.specifications : [],
    certificateUrl: productUrl(source.certificate_url), image: productUrl(source.image), url: productUrl(source.url),
    rationale: source.rationale || '', analogs: (source.analogs || []).map((item) => normaliseProduct(item, language)).filter((p): p is Product => !!p),
    stores: (source.stores || []).map((store) => ({ ...store, quantity: nullableNumber(store.quantity) })),
    checkedAt: source.last_checked_at || null, warnings: source.data_quality_warnings || [],
    minimum: nullableNumber(source.min_order_quantity) || null,
    multiple: nullableNumber(source.order_multiple) || null,
  };
}

export function canOffer(product: Product): boolean {
  return product.priceVerified && product.stockVerified && product.price !== null && product.price > 0 && product.stock !== null && product.stock >= Math.max(1, product.minimum ?? 1);
}

/** Keep a product card aligned with the exact quantity proposed by the agent. */
export function offeredQuantity(product: Product, offer?: Offer | null): number | undefined {
  return offer?.product_id === product.id && Number.isSafeInteger(offer.quantity) && offer.quantity > 0
    ? offer.quantity : undefined;
}
