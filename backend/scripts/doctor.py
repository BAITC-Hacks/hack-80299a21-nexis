"""Local runtime diagnostics; never prints credentials or queries the partner API."""
import argparse
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from settings import ROOT  # Loads the root .env without printing its contents.
from spec_parser import SpecificationParser
from knowledge_base import retrieval_status
from ekt_client import ekt_client


def inspect_ocr():
    executable = os.getenv("TESSERACT_CMD") or shutil.which("tesseract")
    result = {"available": False, "languages": [], "required_languages": ["eng", "rus", "kaz"]}
    if not executable or not Path(executable).is_file():
        return {**result, "error": "ocr_executable_missing"}
    try:
        completed = subprocess.run([executable, "--list-langs"], capture_output=True, text=True, timeout=5, check=True)
        languages = [line.strip() for line in completed.stdout.splitlines() if re.fullmatch(r"[a-z_]+", line.strip())]
        missing = sorted(set(result["required_languages"]) - set(languages))
        return {**result, "available": not missing, "languages": languages, "missing_languages": missing}
    except (OSError, subprocess.SubprocessError):
        return {**result, "error": "ocr_executable_unusable"}


def ocr_smoke():
    """Recognize generated, non-customer text using the real OCR executable."""
    from PIL import Image, ImageDraw, ImageFont

    fonts = [Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"), Path("C:/Windows/Fonts/arial.ttf")]
    font_path = next((path for path in fonts if path.is_file()), None)
    font = ImageFont.truetype(str(font_path), 48) if font_path else ImageFont.load_default(size=48)
    image = Image.new("RGB", (1500, 180), "white")
    ImageDraw.Draw(image).text((35, 45), "SPEC-1001     2 pcs", font=font, fill="black")
    output = io.BytesIO()
    image.save(output, "PNG")
    text = SpecificationParser().extract_text(output.getvalue(), "generated-ocr-check.png")
    rows, _ = SpecificationParser.rows(text)
    if not re.search(r"SPEC\s*[-—]?\s*1001", text, re.I) or not rows or rows[0]["quantity"] != 2:
        raise RuntimeError("generated_text_not_recognized")
    return {"passed": True, "input": "generated_image", "recognized_sku": "SPEC-1001", "recognized_quantity": 2}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-ocr", action="store_true", help="Fail if any OCR language is unavailable.")
    parser.add_argument("--ocr-smoke", action="store_true", help="Run real OCR on an in-memory generated image.")
    args = parser.parse_args()
    result = {
        "python": sys.version.split()[0],
        "catalog_credentials_configured": bool(os.getenv("EKT_API_USER") and os.getenv("EKT_API_PASS")),
        "model_key_configured": bool(os.getenv("OPENAI_API_KEY")) and not os.getenv("OPENAI_API_KEY", "").startswith("your_"),
        "ocr": inspect_ocr(),
        "languages": ["ru", "kk", "en"],
        "retrieval": retrieval_status(),
        "catalog_index": ekt_client.coverage(),
    }
    success = result["ocr"]["available"] if args.require_ocr else True
    if args.ocr_smoke:
        try:
            result["ocr_smoke"] = ocr_smoke()
        except Exception:
            result["ocr_smoke"] = {"passed": False, "error": "ocr_smoke_failed"}
            success = False
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
