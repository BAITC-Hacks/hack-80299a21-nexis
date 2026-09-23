export type Language = 'ru' | 'kz' | 'en';
export interface ReasoningStep { type?: string; message?: string; tool_name?: string; tool_output?: unknown; status?: string; completed?: boolean }
export interface Specification { name: string; value: unknown }
export interface Store { id?: number; name: string; quantity: number | null }
export interface ProductSource {
  id?: number | string; product_id?: number | string; name?: string; article?: string; brand?: string;
  price?: number | null; quantity?: number | null; price_verified?: boolean; stock_verified?: boolean;
  unit?: string; specifications?: (Specification | string)[]; certificate_url?: string | null;
  image?: string | null; url?: string | null; rationale?: string; analogs?: ProductSource[];
  stores?: Store[]; last_checked_at?: string | null; data_quality_warnings?: string[];
  min_order_quantity?: number | null; order_multiple?: number | null;
}
export interface Product {
  id: number; name: string; article: string; brand: string; price: number | null; stock: number | null;
  priceVerified: boolean; stockVerified: boolean; unit: string; specifications: string[];
  certificateUrl: string | null; image: string | null; url: string | null; rationale: string; analogs: Product[];
  stores: Store[]; checkedAt: string | null; warnings: string[]; minimum: number; multiple: number;
}
export interface CartItem { product_id: number; name: string; article?: string; price: number; quantity: number; unit?: string; stock?: number | null; stock_available?: number | null }
export interface Cart { items: CartItem[]; checkout_url: string | null; total_items?: number; total_sum?: number; cart_mode?: string; stock_reserved?: boolean }
export interface Offer {
  offer_token: string; product_id: number; product_name: string; article: string; quantity: number; price: number;
  stock_available: number | null; expires_in_seconds: number; cart_mode: string; data_quality_warnings?: string[];
  operation?: 'set_quantity'; previous_quantity?: number;
}
export interface KnowledgeSource { title: string; source_url: string; verified_at?: string }
export interface ChatResponse {
  answer: string; cart_updated?: boolean; reasoning_steps?: ReasoningStep[]; sources?: ProductSource[];
  pending_offer?: Offer | null; cart_url?: string; knowledge_sources?: KnowledgeSource[]; warnings?: string[];
}
export interface CartResult { answer?: string; message?: string; cart: CartItem[] | Cart; cart_url: string; success: boolean }
export interface HistoryMessage { role: 'user' | 'assistant'; content: string }
export interface EstimateMatch extends Omit<ProductSource, 'quantity'> {
  query_line: string; quantity: number | null; quantity_warning?: string | null; unit_price: number | null;
  subtotal: number | null; stock_available: number | null; status: string; analog?: ProductSource | null;
}
export interface EstimateUnmatched { query_line: string; status: string; quantity?: number | null; quantity_warning?: string | null; candidates?: { id: number; name: string }[] }
export interface UploadResponse {
  filename: string; estimate: { summary_text: string; estimate_complete: boolean; total_estimate_kzt: number;
    matched_items: EstimateMatch[]; unmatched_items: EstimateUnmatched[]; ignored_lines: string[]; warnings: string[] };
}
