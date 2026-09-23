export type Language = 'ru' | 'kz' | 'en';
export type Scenario = 'cable' | 'analog' | 'delivery';

export interface ReasoningStep {
  type?: string;
  message?: string;
  tool_name?: string;
  tool_output?: unknown;
  status?: string;
  completed?: boolean;
}

export interface ProductSource {
  id?: number | string;
  product_id?: number | string;
  brand?: string;
  manufacturer?: string;
  name?: string;
  title?: string;
  article?: string;
  sku?: string;
  price?: number | string;
  stock?: number | string;
  quantity?: number | string;
  available_quantity?: number | string;
  unit?: string;
  specifications?: string[] | string;
  certificate_url?: string;
  certificate_link?: string;
  certificate?: string | boolean;
  has_certificate?: boolean;
  certificate_available?: boolean;
  image?: string | null;
  rationale?: string;
  analogs?: ProductSource[];
}

export interface Product {
  id: number;
  brand: string;
  name: string;
  article: string;
  price: number;
  stock: number;
  unit: string;
  specifications: string[];
  certificateUrl: string | null;
  certificate: boolean;
  image: string | null;
  rationale: string;
  analogs: Product[];
}

export interface CartItem {
  product_id: number;
  id?: number;
  article?: string;
  sku?: string;
  name?: string;
  title?: string;
  price: number;
  quantity: number;
  stock?: number;
  available_quantity?: number;
  image?: string | null;
  unit?: string;
  brand?: string;
}

export interface Cart {
  items: CartItem[];
  checkout_url: string;
}

export interface AssistantReply {
  isDemo: boolean;
  answer: string;
  steps: ReasoningStep[];
  products: Product[];
  scenario?: Scenario;
  delivery?: boolean;
}

export interface ChatResponse {
  answer?: string;
  cart_updated?: boolean;
  reasoning_steps?: ReasoningStep[];
  sources?: ProductSource[];
}

export interface CartResponse {
  items?: CartItem[];
  cart?: CartItem[];
  checkout_url?: string;
}

export interface HistoryMessage {
  role: 'user' | 'assistant';
  content: string;
}
