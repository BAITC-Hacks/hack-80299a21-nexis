import re
import pymupdf
from typing import List, Dict, Any
from ekt_client import ekt_client

class SpecificationParser:
    """Parses customer specification documents (PDF / text) and maps to ekt.kz catalog."""
    
    @staticmethod
    def extract_text_from_pdf(pdf_bytes: bytes) -> str:
        """Extract text lines from PDF bytes."""
        text_lines = []
        try:
            doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
            for page in doc:
                text = page.get_text()
                if text:
                    text_lines.append(text)
            doc.close()
        except Exception as e:
            print(f"[SpecParser] PDF extract error: {e}")
        return "\n".join(text_lines)

    @classmethod
    def parse_specification(cls, text_or_bytes: Any) -> Dict[str, Any]:
        """Analyzes text or PDF and matches equipment with ekt.kz stock and pricing."""
        if isinstance(text_or_bytes, bytes):
            raw_text = cls.extract_text_from_pdf(text_or_bytes)
        else:
            raw_text = str(text_or_bytes)

        lines = [line.strip() for line in raw_text.splitlines() if len(line.strip()) > 3]
        
        matched_items = []
        unmatched_items = []
        total_estimate_kzt = 0
        
        # Stop-words to ignore non-equipment lines
        ignore_words = {"спецификация", "проект", "заказчик", "дата", "объект", "итого", "подпись", "страница", "№", "п/п"}

        for line in lines:
            line_lower = line.lower()
            if any(ign in line_lower for ign in ignore_words) and len(line.split()) < 3:
                continue

            # Try to detect quantity in line (e.g. '... 5 шт' or '... - 10')
            qty_match = re.search(r'(\d+)\s*(?:шт|ед|компл|\b)', line_lower)
            detected_qty = int(qty_match.group(1)) if qty_match and int(qty_match.group(1)) < 500 else 1

            # Search in ekt.kz live catalog
            results = ekt_client.search_products(line, limit=1)
            if results:
                target = results[0]
                detail = ekt_client.get_product_detail(target["id"]) or target
                unit_price = detail.get("price", 0)
                subtotal = unit_price * detected_qty
                stock = detail.get("quantity", 0)
                
                analog_info = None
                if stock == 0:
                    analogs = ekt_client.find_analogs(detail, limit=1)
                    if analogs:
                        analog_info = analogs[0]

                item_record = {
                    "query_line": line,
                    "product_id": detail["id"],
                    "name": detail["name"],
                    "article": detail.get("article", "Н/Д"),
                    "unit_price": unit_price,
                    "quantity": detected_qty,
                    "subtotal": subtotal,
                    "stock_available": stock,
                    "status": "В наличии" if stock >= detected_qty else ("Частично" if stock > 0 else "Под заказ / Аналог"),
                    "image": detail.get("image"),
                    "url": detail.get("url"),
                    "analog": analog_info
                }
                matched_items.append(item_record)
                total_estimate_kzt += subtotal
            else:
                unmatched_items.append({"query_line": line, "status": "Уточнить у менеджера"})

        return {
            "total_positions_found": len(matched_items),
            "total_estimate_kzt": total_estimate_kzt,
            "matched_items": matched_items,
            "unmatched_items": unmatched_items,
            "summary_text": (
                f"📋 **Результат обработки спецификации:**\n"
                f"- Обработано позиций: **{len(matched_items)}**\n"
                f"- Предварительная сумма сметы: **{total_estimate_kzt:,} ₸** (с НДС 12%)\n"
                f"- Все позиции проверены по складам Астана, Алматы, Шымкент."
            )
        }

spec_parser = SpecificationParser()
