import io
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from ekt_client import ekt_client


MAX_SPEC_LINES = 250
MIN_MATCH_SCORE = 2


class SpecificationParser:
    """Extract text from common specification files and match only credible catalog hits."""

    @staticmethod
    def extract_text(content: bytes, filename: str) -> str:
        extension = os.path.splitext(filename.lower())[1]
        if extension == ".pdf":
            import pymupdf
            with pymupdf.open(stream=content, filetype="pdf") as document:
                return "\n".join(page.get_text() for page in document)
        if extension == ".txt":
            return content.decode("utf-8-sig", errors="replace")
        if extension == ".docx":
            from docx import Document
            document = Document(io.BytesIO(content))
            values = [paragraph.text for paragraph in document.paragraphs if paragraph.text.strip()]
            for table in document.tables:
                for row in table.rows:
                    values.append("\t".join(cell.text.strip() for cell in row.cells))
            return "\n".join(values)
        if extension == ".xlsx":
            from openpyxl import load_workbook
            workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
            values = []
            for sheet in workbook.worksheets:
                for row in sheet.iter_rows(values_only=True):
                    cells = [str(value).strip() for value in row if value is not None and str(value).strip()]
                    if cells:
                        values.append("\t".join(cells))
            workbook.close()
            return "\n".join(values)
        if extension == ".xls":
            import xlrd
            workbook = xlrd.open_workbook(file_contents=content)
            values = []
            for sheet in workbook.sheets():
                for row_index in range(sheet.nrows):
                    cells = [str(value).strip() for value in sheet.row_values(row_index) if str(value).strip()]
                    if cells:
                        values.append("\t".join(cells))
            return "\n".join(values)
        if extension in {".jpg", ".jpeg", ".png", ".webp"}:
            from PIL import Image
            import pytesseract
            image = Image.open(io.BytesIO(content))
            try:
                return pytesseract.image_to_string(image, lang="rus+eng")
            except pytesseract.TesseractNotFoundError as exc:
                raise ValueError("Для распознавания фото на сервере нужен установленный Tesseract OCR с языками rus и eng.") from exc
        raise ValueError("Поддерживаются PDF, TXT, DOCX, XLSX, XLS и изображения JPG, PNG, WEBP.")

    @staticmethod
    def _quantity(line: str) -> Tuple[int, Optional[str]]:
        # Prefer a quantity explicitly followed by a unit so article numbers are not
        # mistaken for order quantities.
        match = re.search(r"(?<![\w/])([1-9]\d{0,3})\s*(шт\.?|штук|ед\.?|компл\.?|м(?:етр(?:ов|а)?)?)(?![а-я])", line.lower())
        if match:
            unit = "м" if match.group(2).startswith("м") else "шт."
            return int(match.group(1)), unit
        # Spreadsheet tables often put a quantity in the final tab-separated column.
        cells = [cell.strip() for cell in line.split("\t") if cell.strip()]
        if len(cells) > 1 and re.fullmatch(r"[1-9]\d{0,3}", cells[-1]):
            return int(cells[-1]), "шт."
        return 1, None

    @staticmethod
    def _credible_match(line: str, candidate: Dict[str, Any]) -> bool:
        if candidate.get("_match_type") == "exact":
            return True
        return int(candidate.get("_match_score", 0)) >= MIN_MATCH_SCORE

    @classmethod
    def parse_specification(cls, content: bytes, filename: str = "specification.pdf") -> Dict[str, Any]:
        try:
            raw_text = cls.extract_text(content, filename)
        except Exception as exc:
            return {"error": f"Не удалось прочитать файл: {exc}", "lines": []}

        lines = [line.strip() for line in raw_text.splitlines() if len(line.strip()) > 3]
        ignored = ("спецификация", "проект", "заказчик", "дата", "объект", "подпись", "страница")
        candidate_lines = [line for line in lines if not (line.lower().startswith(ignored) and len(line.split()) < 5)]
        if len(candidate_lines) > MAX_SPEC_LINES:
            return {"error": f"В файле больше {MAX_SPEC_LINES} строк. Разделите спецификацию на части.", "lines": lines[:MAX_SPEC_LINES]}

        matched_items: List[Dict[str, Any]] = []
        unmatched_items: List[Dict[str, Any]] = []
        total_estimate = 0.0

        for line in candidate_lines:
            quantity, unit = cls._quantity(line)
            results = ekt_client.search_products(line, limit=3)
            target = next((item for item in results if cls._credible_match(line, item)), None)
            if not target:
                unmatched_items.append({"query_line": line, "status": "Не удалось надёжно сопоставить; уточнить у менеджера"})
                continue

            detail = ekt_client.get_product_detail(target.get("id"))
            product = detail or target
            try:
                unit_price = float(product["price"])
            except (KeyError, TypeError, ValueError):
                unit_price = None
            stock_verified = bool(detail and detail.get("stock_verified"))
            stock = int(detail.get("quantity") or 0) if stock_verified else None
            subtotal = round(unit_price * quantity, 2) if unit_price is not None else None
            if subtotal is not None:
                total_estimate += subtotal

            analog = None
            if stock_verified and stock == 0:
                analogs = ekt_client.find_analogs(detail, limit=1)
                analog = analogs[0] if analogs else None

            if unit_price is None:
                status = "Цена не получена; уточнить"
            elif not stock_verified:
                status = "Остаток не удалось проверить"
            elif stock >= quantity:
                status = "В наличии"
            elif stock > 0:
                status = "Частично в наличии"
            else:
                status = "Нет в наличии"

            matched_items.append({
                "query_line": line,
                "product_id": product.get("id"),
                "name": product.get("name"),
                "article": product.get("article", "Н/Д"),
                "unit_price": unit_price,
                "quantity": quantity,
                "unit": unit or product.get("unit", "шт."),
                "subtotal": subtotal,
                "stock_available": stock,
                "stock_verified": stock_verified,
                "status": status,
                "image": product.get("image"),
                "url": product.get("url"),
                "specifications": product.get("specifications", []),
                "certificate_url": product.get("certificate_url"),
                "analog": analog,
            })

        estimate_label = f"{total_estimate:,.0f} ₸" if matched_items and all(item["unit_price"] is not None for item in matched_items) else "не рассчитана полностью"
        return {
            "lines": lines,
            "total_positions_found": len(matched_items),
            "total_estimate_kzt": round(total_estimate, 2),
            "matched_items": matched_items,
            "unmatched_items": unmatched_items,
            "summary_text": (
                f"Обработано позиций: {len(matched_items)}. Предварительная сумма: {estimate_label}. "
                f"Нераспознанных строк: {len(unmatched_items)}. Цены и остатки зависят от доступности API каталога."
            ),
        }


spec_parser = SpecificationParser()
