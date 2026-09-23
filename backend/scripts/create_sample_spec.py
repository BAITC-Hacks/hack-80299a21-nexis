"""Create the two-row upload example with an embedded Cyrillic font.

Run from any directory: python backend/scripts/create_sample_spec.py
Use --font /path/to/a/cyrillic.ttf to choose another font.
Only articles and requested quantities are examples; prices/stock come from API.
"""
import argparse
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[2]
ROWS = [("200300285_", 2), ("НЕСУЩЕСТВУЮЩИЙ-XYZ-900", 3)]


def choose_font(value):
    candidates = [Path(value)] if value else [
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
    ]
    font = next((path for path in candidates if path.is_file()), None)
    if font is None:
        raise SystemExit("Pass --font with a Cyrillic TTF font (Arial or DejaVu Sans).")
    return font


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--font", help="Path to an embeddable TTF with Cyrillic glyphs")
    parser.add_argument("--output", type=Path, default=ROOT / "docs/sample_specification.pdf")
    args = parser.parse_args()
    font = choose_font(args.font)
    document = pymupdf.open()
    document.set_metadata({"title": "Тестовая спецификация", "author": "NEXIS", "subject": "Пример загрузки: две позиции, без цен и остатков"})
    page = document.new_page(width=595, height=842)
    font_xref = page.insert_font(fontname="Cyrillic", fontfile=str(font))
    used_text = []

    def text(position, value, size, color):
        used_text.append(value)
        page.insert_text(position, value, fontname="Cyrillic", fontsize=size, color=color)

    navy, gray = (0.08, 0.17, 0.28), (0.35, 0.40, 0.47)
    page.draw_rect(pymupdf.Rect(48, 46, 547, 50), color=None, fill=(0.93, 0.44, 0.10))
    text((48, 85), "Спецификация: тестовый пример", 21, navy)
    text((48, 116), "Проект: проверка найденной и нераспознанной позиции", 11, gray)
    text((48, 138), "Дата: 23.09.2026", 11, gray)
    for index, (article, quantity) in enumerate(ROWS):
        top = 173 + index * 72
        page.draw_rect(pymupdf.Rect(48, top, 547, top + 54), color=None, fill=(0.95, 0.96, 0.98))
        text((62, top + 33), f"{article} - {quantity} шт.", 13, navy)
    text((48, 788), "Страница 1", 10, gray)
    # Some Arial glyphs map both '-' and soft hyphen, or space and NBSP.
    # Record the actual characters used so copy/paste preserves exact articles.
    source_font = pymupdf.Font(fontfile=str(font))
    pairs = {source_font.has_glyph(ord(char)): char.encode("utf-16-be").hex()
             for char in set("".join(used_text))}
    if 0 in pairs:
        raise SystemExit("The selected font is missing characters used by the Cyrillic sample.")
    mapping = "\n".join(f"<{glyph:04x}> <{value}>" for glyph, value in sorted(pairs.items()))
    cmap = ("/CIDInit /ProcSet findresource begin 12 dict begin begincmap\n"
            "/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def\n"
            "/CMapName /NexisUnicode def /CMapType 2 def\n"
            "1 begincodespacerange <0000> <ffff> endcodespacerange\n"
            f"{len(pairs)} beginbfchar\n{mapping}\nendbfchar\n"
            "endcmap CMapName currentdict /CMap defineresource pop end end")
    cmap_xref = int(document.xref_get_key(font_xref, "ToUnicode")[1].split()[0])
    document.update_stream(cmap_xref, cmap.encode("ascii"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    document.subset_fonts()
    document.save(args.output, garbage=4, deflate=True)
    document.close()
    text_output = args.output.with_suffix(".txt")
    text_output.write_text("Артикул;Количество;Единица\n" + "".join(f"{article};{quantity};шт.\n" for article, quantity in ROWS), encoding="utf-8")
    print(f"Created {args.output.name} and {text_output.name}; 2 rows, quantities 2 and 3.")


if __name__ == "__main__":
    main()
