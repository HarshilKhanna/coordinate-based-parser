"""
Layer 2 — Intelligent Segmentation

Walks through ordered text blocks and splits them into individual
case blocks using item-number boundaries.

Strategy:
  - A new case block starts when we see an ITEM NUMBER at the start
    of a line (e.g. "1", "2", "8.", "12" alone or followed by text).
  - A CASE_NUMBER_PATTERN on its own line also marks a new block
    (fallback for cause lists without item numbers).
  - "AND" followed by another case number = connected case; kept
    within the same block.
"""

import re
import logging

logger = logging.getLogger(__name__)

# Standalone item number on its own line: "8", "12", "123"
STANDALONE_ITEM = re.compile(r"^\s*(\d{1,4})\s*$")

# Item number with punctuation: "8.", "9)", "10."
ITEM_BOUNDARY = re.compile(r"^\s*(\d{1,4})\s*[.)]\s+", re.MULTILINE)

# Case number pattern: various Indian court case formats
CASE_NUMBER_PATTERN = re.compile(
    r"""
    (?:
        (?:W\.?P\.?|W\.?A\.?|WP|WA|WMP|CMP|CONT\.?\s*P|SUB\.?\s*APPL|
           CMSA|CRL\.?\s*(?:O\.?P\.?|A\.?|M\.?C\.?|R\.?C\.?|APPEAL|PETITION|M\.?P\.?)?|
           Crl\.O\.P|CRP|SA|RSA|RP|BAIL\s*APPLN|SLP|FAO|MFA|
           ARB\.?\s*(?:O\.?P\.?|A\.?|CASE)?|
           C\.?S\.?|O\.?S\.?|A\.?S\.?|E\.?P\.?|
           CIVIL\s*(?:APPEAL|SUIT|MISC|REVISION|PETITION)|
           CRIM(?:INAL)?\s*(?:APPEAL|PETITION|MISC|REVISION)|
           REVIEW\s*(?:APPLN|PETITION)|
           CONTEMPT\s*(?:CASE|PETITION)|
           PIL|OA|TA|MA|COMP|
           M\.?A\.?T\.?|L\.?P\.?A\.?|C\.?O\.?|
           MISC\.?\s*(?:CASE|APPLN|PETITION)|
           T\.?P\.?|REF\.?\s*(?:CASE)?|
           I\.?T\.?A\.?|S\.?A\.?)
        \s*(?:\(?\s*(?:C|Crl|Civil|Criminal|MD|OS|SS|DB|SB|FB|Com|Tax|Lab|Cus)\s*\)?\s*)?
        [/\s.]*(?:No\.?\s*)?
        \d{1,6}
        \s*/\s*\d{4}
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)


def segment_case_blocks(text_blocks: list[dict]) -> list[str]:
    """
    Split ordered text blocks into individual case block strings.

    Returns a list of plain-text strings, one per case entry.
    """
    logger.info("Layer 2 — Segmenting %d text blocks", len(text_blocks))

    # Merge all block texts into a single line stream
    full_text = "\n".join(b["text"] for b in text_blocks)
    lines = full_text.split("\n")

    case_blocks: list[str] = []
    current_block: list[str] = []

    for line in lines:
        stripped = line.strip()

        # Skip empty lines (but keep in existing blocks)
        if not stripped:
            if current_block:
                current_block.append(line)
            continue

        # Detect new item boundary
        is_new_item = False
        if STANDALONE_ITEM.match(stripped):
            is_new_item = True
        elif ITEM_BOUNDARY.match(stripped):
            is_new_item = True
        elif not current_block and CASE_NUMBER_PATTERN.match(stripped):
            is_new_item = True

        if is_new_item and current_block:
            block_text = "\n".join(current_block).strip()
            if block_text:
                case_blocks.append(block_text)
            current_block = [line]
        else:
            current_block.append(line)

    # Flush last block
    if current_block:
        block_text = "\n".join(current_block).strip()
        if block_text:
            case_blocks.append(block_text)

    logger.info("Layer 2 — Segmented into %d case blocks", len(case_blocks))
    return case_blocks
