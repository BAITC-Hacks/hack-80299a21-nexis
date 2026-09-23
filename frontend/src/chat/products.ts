import type { Offer, Product, ProductSource } from './types';

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
export function normaliseProduct(source: ProductSource): Product | null {
  const id = Number(source.product_id ?? source.id);
  if (!Number.isSafeInteger(id) || id <= 0) return null;
  const price = nullableNumber(source.price);
  const stock = nullableNumber(source.quantity);
  return {
    id, name: source.name || 'Товар ekt.kz', article: source.article || '—', brand: source.brand || 'ekt.kz',
    price, stock, priceVerified: source.price_verified === true && price !== null,
    stockVerified: source.stock_verified === true && stock !== null, unit: source.unit || 'шт.',
    specifications: (Array.isArray(source.specifications) ? source.specifications : []).flatMap((spec) => {
      if (typeof spec === 'string') return [spec];
      if (!spec || typeof spec.name !== 'string') return [];
      const value = Array.isArray(spec.value) ? spec.value.join(', ') : spec.value;
      return typeof value === 'string' || typeof value === 'number' ? [`${spec.name}: ${value}`] : [];
    }),
    certificateUrl: productUrl(source.certificate_url), image: productUrl(source.image), url: productUrl(source.url),
    rationale: source.rationale || '', analogs: (source.analogs || []).map(normaliseProduct).filter((p): p is Product => !!p),
    stores: (source.stores || []).map((store) => ({ ...store, quantity: nullableNumber(store.quantity) })),
    checkedAt: source.last_checked_at || null, warnings: source.data_quality_warnings || [],
    minimum: Math.max(1, nullableNumber(source.min_order_quantity) || 1),
    multiple: Math.max(1, nullableNumber(source.order_multiple) || 1),
  };
}

export function canOffer(product: Product): boolean {
  return product.priceVerified && product.stockVerified && product.price !== null && product.price > 0 && product.stock !== null && product.stock >= product.minimum;
}

/** Keep a product card aligned with the exact quantity proposed by the agent. */
export function offeredQuantity(product: Product, offer?: Offer | null): number | undefined {
  return offer?.product_id === product.id && Number.isSafeInteger(offer.quantity) && offer.quantity > 0
    ? offer.quantity : undefined;
}
