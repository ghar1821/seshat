#!/usr/bin/env python3
"""
Convert a PDF (local file or arXiv URL) to Markdown with extracted images.
Uses marker-pdf for high-quality scientific paper conversion.

Usage:
    uv run -m digest.arxiv.convert --input <pdf_path_or_arxiv_url> [--output-dir <dir>]

Examples:
    uv run -m digest.arxiv.convert --input paper.pdf
    uv run -m digest.arxiv.convert --input https://arxiv.org/abs/2301.07041
    uv run -m digest.arxiv.convert --input paper.pdf --output-dir ./output
"""

import argparse
import re
import sys
from pathlib import Path

import requests


def parse_arxiv_url(url: str) -> str | None:
    """Extract arXiv ID from various arXiv URL formats."""
    patterns = [
        r"arxiv\.org/abs/([0-9]+\.[0-9]+(?:v[0-9]+)?)",
        r"arxiv\.org/pdf/([0-9]+\.[0-9]+(?:v[0-9]+)?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def download_arxiv_pdf(arxiv_id: str, dest_dir: Path) -> Path:
    """Download a PDF from arXiv by its ID."""
    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"
    dest_path = dest_dir / f"{arxiv_id.replace('/', '_')}.pdf"

    print(f"Downloading arXiv:{arxiv_id} ...")
    response = requests.get(
        pdf_url, stream=True, timeout=60, headers={"User-Agent": "pdf-to-md/1.0"}
    )
    response.raise_for_status()

    with open(dest_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    print(f"Saved PDF to: {dest_path}")
    return dest_path


def convert_pdf(pdf_path: Path, output_dir: Path, model_dict=None) -> None:
    """Convert a PDF to Markdown and extract images using marker-pdf.

    Pass a pre-loaded model_dict to avoid reloading models on repeated calls.
    """
    from marker.converters.pdf import PdfConverter
    from marker.models import create_model_dict
    from marker.output import text_from_rendered

    if model_dict is None:
        print("Loading models (this may take a moment on first run) ...")
        model_dict = create_model_dict()

    print(f"Converting: {pdf_path.name}")
    converter = PdfConverter(artifact_dict=model_dict)
    rendered = converter(str(pdf_path))

    markdown_text, _, images = text_from_rendered(rendered)

    md_path = output_dir / f"{pdf_path.stem}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(markdown_text)
    print(f"Markdown saved to: {md_path}")

    if images:
        images_dir = output_dir / f"{pdf_path.stem}_images"
        images_dir.mkdir(exist_ok=True)
        for img_name, img in images.items():
            img_path = images_dir / img_name
            img.save(img_path)
        print(f"Exported {len(images)} image(s) to: {images_dir}/")
    else:
        print("No images found in document.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert a PDF (local or arXiv) to Markdown with images.",
    )
    parser.add_argument("--input", required=True, help="Local PDF path or arXiv URL/ID")
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory (default: same folder as the PDF, or ./output for downloads)",
    )
    args = parser.parse_args()

    input_str = args.input

    if input_str.startswith("http://") or input_str.startswith("https://"):
        arxiv_id = parse_arxiv_url(input_str)
        if arxiv_id is None:
            print(
                f"Error: Could not parse arXiv ID from URL: {input_str}",
                file=sys.stderr,
            )
            sys.exit(1)
        download_dir = Path(args.output_dir) if args.output_dir else Path("output")
        download_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = download_arxiv_pdf(arxiv_id, download_dir)
        output_dir = download_dir
    else:
        pdf_path = Path(input_str)
        if not pdf_path.exists():
            print(f"Error: File not found: {pdf_path}", file=sys.stderr)
            sys.exit(1)
        if pdf_path.suffix.lower() != ".pdf":
            print(f"Error: Not a PDF file: {pdf_path}", file=sys.stderr)
            sys.exit(1)
        output_dir = Path(args.output_dir) if args.output_dir else pdf_path.parent
        output_dir.mkdir(parents=True, exist_ok=True)

    convert_pdf(pdf_path, output_dir)
    print("Done.")


if __name__ == "__main__":
    main()
