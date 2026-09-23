export type Language = 'ru' | 'kz' | 'en';
export type ApiLanguage = 'ru' | 'kk' | 'en';
export interface ReasoningStep { type?: string; message?: string; tool_name?: string; tool_output?: unknown; status?: string; completed?: boolean; step_code?: string; params?: Record<string, unknown> }
export interface Specification { key?: string; name: string; value: unknown }
export interface Store { id?: number; name: string; quantity: number | null }
export interface ProductSource {
  id?: number | string; product_id?: number | string; name?: string; article?: string; brand?: string;
  price?: number | null; quantity?: number | null; price_verified?: boolean; stock_verified?: boolean;
  unit?: string; unit_display?: string | null; specifications?: (Specification | string)[]; certificate_url?: string | null;
  image?: string | null; url?: string | null; rationale?: string; analogs?: ProductSource[];
  stores?: Store[]; last_checked_at?: string | null; data_quality_warnings?: string[];
  min_order_quantity?: number | null; order_multiple?: number | null;
}
export interface Product {
  id: number; name: string; article: string; brand: string; price: number | null; stock: number | null;
  priceVerified: boolean; stockVerified: boolean; unit: string; originalUnit: string | null; specifications: string[];
  specificationEntries: (Specification | string)[];
  certificateUrl: string | null; image: string | null; url: string | null; rationale: string; analogs: Product[];
  stores: Store[]; checkedAt: string | null; warnings: string[]; minimum: number | null; multiple: number | null;
}
export interface CartItem { product_id: number; name: string; article?: string; price: number; quantity: number; unit?: string; stock?: number | null; stock_available?: number | null }
export interface Cart { items: CartItem[]; checkout_url: string | null; total_items?: number; total_sum?: number; cart_mode?: string; stock_reserved?: boolean }
export interface Offer {
  offer_token: string; product_id: number; product_name: string; article: string; quantity: number; price: number;
  stock_available: number | null; expires_in_seconds: number; cart_mode: string; data_quality_warnings?: string[];
  operation?: 'set_quantity'; previous_quantity?: number;
}
export interface KnowledgeSource { id?: string; source_id?: string; chunk_id?: string; title: string; source_url?: string | null; verified_at?: string | null; verification_status?: string; language?: ApiLanguage; version?: string; page?: number | null; score?: number }
export interface Clarification { kind: string; missing_fields: string[]; message: string }
export interface ChatResponse {
  answer: string; cart_updated?: boolean; reasoning_steps?: ReasoningStep[]; sources?: ProductSource[];
  pending_offer?: Offer | null; cart_url?: string; knowledge_sources?: KnowledgeSource[]; warnings?: string[]; warning_codes?: string[];
  answer_language?: ApiLanguage; request_id?: string; clarification?: Clarification | null;
  diagnostics?: { mode?: string; elapsed_ms?: number; fallback_reason?: string | null; retrieval_mode?: string; retrieval?: { mode?: string } };
}
export interface CartResult { answer?: string; message?: string; cart: CartItem[] | Cart; cart_url: string; success: boolean }
export interface HistoryMessage { role: 'user' | 'assistant'; content: string }
export interface EstimateMatch extends Omit<ProductSource, 'quantity'> {
  query_line: string; quantity: number | null; quantity_warning?: string | null; unit_price: number | null;
  subtotal: number | null; stock_available: number | null; status: string; status_code?: string; analog?: ProductSource | null;
}
export interface EstimateUnmatched { query_line: string; status: string; status_code?: string; quantity?: number | null; quantity_warning?: string | null; candidates?: { id: number; name: string }[] }
export interface UploadResponse {
  filename: string; estimate: { summary_text: string; estimate_complete: boolean; total_estimate_kzt: number;
    matched_items: EstimateMatch[]; unmatched_items: EstimateUnmatched[]; ignored_lines: string[]; warnings: string[] };
}
