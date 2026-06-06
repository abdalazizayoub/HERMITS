import logging
from datetime import datetime
from pathlib import Path

import pdfplumber

logger = logging.getLogger("hermits.memory.pdf_ingestor")


def ingest_pdf(pdf_path: str, output_path: str = "data/memory.md") -> str:
    """Extract text from PDF using pdfplumber, write to memory.md."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    pdf_filename = Path(pdf_path).name
    updated_at = datetime.utcnow().isoformat()

    lines = [
        "# Policy memory",
        f"_Last updated: {updated_at}_",
        f"_Source: {pdf_filename}_",
        "",
        "---",
        "",
    ]

    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            lines.append(f"## Page {i}")
            lines.append(text)
            lines.append("")
            lines.append("---")
            lines.append("")

    content = "\n".join(lines)
    out.write_text(content, encoding="utf-8")
    logger.info("Ingested %s → %s", pdf_path, output_path)
    return content


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m hermits.memory.pdf_ingestor <path/to/policy.pdf>")
        sys.exit(1)
    result = ingest_pdf(sys.argv[1])
    print(f"Ingested {len(result)} chars")
