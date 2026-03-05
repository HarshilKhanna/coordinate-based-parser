"""
Layer 1 — Coordinate Extraction + Row Grouping

Uses pdfplumber's extract_words() to get every word with its
(x0, top, x1, bottom) bounding box, then groups words into
rows based on vertical proximity.
"""

import logging
import pdfplumber

logger = logging.getLogger(__name__)


def extract_rows(page, y_tolerance: float = 2.5) -> list[list[dict]]:
    """
    Extract words from a single page and group them into rows.

    Each word dict has: text, x0, top, x1, bottom.
    Words are grouped into rows when their 'top' values are
    within y_tolerance of each other.

    Returns list of rows, where each row is a list of word dicts
    sorted left-to-right.
    """
    words = page.extract_words(x_tolerance=3, y_tolerance=3)
    words.sort(key=lambda w: (round(w['top'] / y_tolerance), w['x0']))

    rows: list[list[dict]] = []
    current_row: list[dict] = []
    current_y = None

    for word in words:
        y = word['top']
        if current_y is None or abs(y - current_y) > y_tolerance:
            if current_row:
                rows.append(current_row)
            current_row = [word]
            current_y = y
        else:
            current_row.append(word)

    if current_row:
        rows.append(current_row)

    return rows


def extract_date_from_page(page) -> str:
    """
    Try to extract the listing date from a page's text.
    Looks for patterns like 'WEDNESDAY 4 MARCH 2026'.
    """
    import re
    text = page.extract_text() or ''
    m = re.search(
        r'(\w+DAY)\s+(\d+)\s+(\w+)\s+(\d{4})',
        text, re.IGNORECASE,
    )
    if m:
        return f"{m.group(2)} {m.group(3)} {m.group(4)}"
    return ""
