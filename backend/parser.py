"""
Layers 2-5 — Column Zoning → State Machine Parser → Regex Extraction

Architecture:
  Layer 2: Column Zoning — classify each word into a zone (item_num,
           case_id, parties, advocates) based on its x0 coordinate.
  Layer 3: State Machine — track bench/court number, detect item
           boundaries, accumulate rows per item, flush on new item.
  Layer 4: Regex Extraction — extract case_type + case_number from
           the case_id zone text.
  Layer 5: Party/Advocate Parsing — split petitioner/respondent at
           VS separator, separate advocate lines by dash separator.
"""

import io
import re
import logging
from collections import defaultdict

import pdfplumber

from extractor import extract_rows, extract_date_from_page

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# COLUMN ZONES  (x0 boundaries in points)
# ─────────────────────────────────────────────

# Standard layout: used by most courts
ZONES_STANDARD = {
    'item_num':  (0,    65),
    'case_id':   (65,   200),
    'parties':   (200,  384),
    'advocates': (384,  600),
}

# Narrow-B layout: TOS/CS/OP original-side cases
ZONES_NARROW_B = {
    'item_num':  (0,    65),
    'case_id':   (65,   175),
    'parties':   (175,  355),
    'advocates': (355,  600),
}


# ─────────────────────────────────────────────
# REGEXES
# ─────────────────────────────────────────────

ITEM_NUM_RE    = re.compile(r'^\d{1,3}$')
BENCH_RE       = re.compile(r'COURT\s+NO\.?\s*(\d+|\bCHAMBERS\b)', re.I)
PAGE_FOOTER_RE = re.compile(r'\d+/\d+\s+[A-Z]+.*(?:LIST|RSKJ|NSJ|SMJ|KSJ)', re.I)

# Comprehensive case number pattern
CASE_NUM_RE = re.compile(
    r'(?:\([A-Z]\))?'
    r'('
        r'WP(?:MP)?(?:\s*Crl\.?)?(?:\([A-Z]+\))?|'
        r'WMP(?:\([A-Z]+\))?|'
        r'WA|WMP|'
        r'LPA|CRP|CMA(?:\([A-Z]+\))?|'
        r'(?:T\.?)?OP(?:\([A-Z]+\))?|'
        r'TOS|'
        r'C\.?S(?:\([A-Z\s/]+\))?|'
        r'CONT\s*P|'
        r'CRL\s*(?:RC|A|MP|OP|REV|APPL)?\.?|'
        r'REV\.?APPL?L?[AW]?|'
        r'SUB\s*APPL|'
        r'(?:TM|PT)\s*A|'
        r'TM\s*A|'
        r'SA|OSA(?:\([A-Z]+\))?|AS|MA|LA|TA|TC|AFC|HCP|SLP|'
        r'CMP|MP|OA|EP|SMA|OCMP|TCA|A|'
        r'CS(?:\s*/?\s*(?:COMM\s*DIV|OS))?'
    r')'
    r'\s*[/\\]?\s*(\d+)\s*[/\\]\s*(\d{4})',
    re.I
)


# Category tags like (Land.Ench.), (Human Rights/RC) that appear in case_id zone
# Negative lookahead prevents stripping case types like WP(MD), CMA(MD) which are
# always followed by /number
CATEGORY_TAG_RE = re.compile(r'(?<!\w)\([A-Za-z][A-Za-z\s./&]{2,}\)(?!\s*/\s*\d)')



# ─────────────────────────────────────────────
# LAYER 2 — Column Zone Classification
# ─────────────────────────────────────────────

def classify_zone(x0: float, zones: dict) -> str:
    """Classify a word's x0 coordinate into a named zone."""
    for name, (lo, hi) in zones.items():
        if lo <= x0 < hi:
            return name
    return 'unknown'


def detect_layout(rows: list[list[dict]]) -> dict:
    """
    Detect whether a page uses STANDARD or NARROW_B column layout.
    NARROW_B is used by original-side courts (TOS, CS, OP suits).
    """
    party_x0s = [
        w['x0'] for row in rows[:40] for w in row
        if 165 <= w['x0'] <= 180
        and len(w['text']) > 3
        and not CASE_NUM_RE.search(w['text'])
    ]
    if len(party_x0s) > 5:
        return ZONES_NARROW_B
    return ZONES_STANDARD


def row_to_zones(row: list[dict], zones: dict) -> dict[str, str]:
    """Classify every word in a row into zones and join per zone."""
    z = defaultdict(list)
    for word in row:
        z[classify_zone(word['x0'], zones)].append(word['text'])
    return {k: ' '.join(v) for k, v in z.items()}


# ─────────────────────────────────────────────
# LAYER 4 — Regex Case Number Extraction
# ─────────────────────────────────────────────

def extract_case_number(text: str) -> tuple:
    """
    Extract (full_case_number, case_type) from case_id zone text.
    Returns (None, None) if no match.
    """
    m = CASE_NUM_RE.search(text)
    if m:
        ct = re.sub(r'\s+', ' ', m.group(1)).strip().upper()
        return f"{ct}/{m.group(2)}/{m.group(3)}", ct.split()[0]
    return None, None


# ─────────────────────────────────────────────
# LAYER 5 — Party / Advocate Parsing
# ─────────────────────────────────────────────

def parse_item_rows(item_rows: list[dict]) -> tuple:
    """
    Extract petitioner, respondent, and their advocates from
    a list of zone-dicts accumulated for one item.

    The parties zone uses VS as the petitioner/respondent separator.
    The advocates zone uses dashes (------) as the separator between
    petitioner's advocates and respondent's advocates.
    """
    petitioner_parts = []
    respondent_parts = []
    pet_adv_parts = []
    res_adv_parts = []
    vs_seen = False
    dash_seen = False

    for z in item_rows:
        parties = z.get('parties', '').strip()
        adv = z.get('advocates', '').strip()

        # Separator leaked into parties zone
        if '--' in parties:
            parts = re.split(r'-{3,}', parties)
            segment = parts[0].strip()
            if segment:
                (respondent_parts if vs_seen else petitioner_parts).append(segment)
            dash_seen = True
            continue

        if parties == 'VS':
            vs_seen = True
            continue
        if parties and parties not in ('AND',):
            (respondent_parts if vs_seen else petitioner_parts).append(parties)

        if '--' in adv:
            clean = re.sub(r'-{3,}', '', adv).strip()
            if clean:
                pet_adv_parts.append(clean)
            dash_seen = True
        elif adv and dash_seen:
            res_adv_parts.append(adv)
        elif adv and not dash_seen:
            pet_adv_parts.append(adv)

    return (
        ' '.join(petitioner_parts).strip(),
        ' '.join(respondent_parts).strip(),
        ' '.join(pet_adv_parts).strip(),
        ' '.join(res_adv_parts).strip(),
        vs_seen,
    )


# ─────────────────────────────────────────────
# LAYER 3 — State Machine Parser
# ─────────────────────────────────────────────

class CauseListParser:
    """
    State machine that walks through rows page-by-page.

    Two-level flush:
      - _flush_sub_case(): flush current sub-case rows into a case dict,
        append to _current_item_cases. Triggered by AND alone in zone B.
      - _flush_item(): flush sub-case + emit all accumulated cases in
        _current_item_cases to self.records. Triggered by new item number
        or new bench header.

    (Concluded) is treated as a block separator, NOT a document terminator.
    """

    # Pattern for the concluded marker
    CONCLUDED_RE = re.compile(r'\*+\s*\(?\s*Concluded\s*\)?\s*\*+', re.I)

    # Hard termination — mediation section is a different document format
    TERMINATION_RE = re.compile(
        r'Tamil\s+Nadu\s+Mediation\s+and\s+Conciliation\s+Centre|'
        r'Tamil\s+Nadu\s+Mediation|'
        r'Mediation\s+Centre|'
        r'List\s+of\s+Cases\s+for\s+Mediation|'
        r'MEDIATION\s+AND\s+CONCILIATION|'
        r'ALL\s+THE\s+PARTIES\s+ARE\s+REQUESTED\s+TO\s+RECORD\s+THEIR\s+PRESENCE',
        re.I
    )

    # Administrative / noise text to skip (row-level)
    ADMIN_SKIP_RE = re.compile(
        r'Powered\s+by\s+TCPDF|'
        r'THE\s+MASTER|'
        r'TO\s+BE\s+HEARD\s+ON|'
        r'FOR\s+RECORDING\s+EVIDENCE|'
        r'SITTING\s+ARRANGEMENTS|'
        r'NATIONAL\s+LOK\s+ADALAT|'
        r'PROVISIONAL\s+LIST|'
        r'NOTIFICATION\s+NO|'
        r'RESTORED\s+ALONG\s+WITH',
        re.I
    )

    # Legal boilerplate that bleeds into party fields
    LEGAL_BOILERPLATE_RE = re.compile(
        r'\bbatta\b|'
        r'deficit\s+batta|'
        r'copies\s+of\s+(?:petition|affidavit)|'
        r'copy\s+of\s+petition|'
        r'petition\s+and\s+affidavit\s+(?:due|filed|copies)|'
        r'affidavit\s+(?:due|copies|copy)\s+(?:reg|filed)|'
        r'due\s+reg\s+R\d|'
        r'memo\s+of\s+grounds\s+due|'
        r'bring\s+on\s+record|'
        r'legal\s+heirs?\s+of|'
        r'deceased\s+respondent|'
        r'array\s+them\s+as|'
        r'process\s+fee|'
        r'court\s+fee|'
        r'condone\s+the\s+delay|'
        r'\bimpleading\b|'
        r'steps\s+taken|'
        r'notice\s+(?:sent|awaited|refused)',
        re.I
    )

    def __init__(self, court_name: str = "High Court of Judicature at Madras",
                 listing_date: str = ""):
        self.court_name = court_name
        self.listing_date = listing_date
        self.records: list[dict] = []
        self.stats = {"total": 0, "regex_ok": 0, "partial": 0, "llm_needed": 0}

        self._bench = "UNKNOWN"
        self._sub_case_rows: list[dict] = []       # rows for current sub-case
        self._current_item_cases: list[dict] = []   # flushed sub-cases for current item
        self._item_num = None
        self._pending_num = None
        self._terminated = False  # Hard stop at mediation section

    def _flush_sub_case(self):
        """Flush current sub-case rows into a case dict, append to _current_item_cases."""
        if not self._sub_case_rows:
            return

        all_case_id = ' '.join(z.get('case_id', '') for z in self._sub_case_rows)
        case_number, _ = extract_case_number(all_case_id)

        petitioner, respondent, pet_adv, res_adv, vs_seen = parse_item_rows(self._sub_case_rows)

        # Merge advocates into one field
        adv_parts = []
        if pet_adv:
            adv_parts.append(pet_adv)
        if res_adv:
            adv_parts.append(res_adv)
        advocates = '; '.join(adv_parts) if adv_parts else None

        self._current_item_cases.append({
            "case_number": case_number,
            "petitioner": petitioner or None,
            "respondent": respondent or None,
            "advocates": advocates,
            "vs_seen": vs_seen,
        })
        self._sub_case_rows = []

    def _flush_item(self):
        """Flush current sub-case + emit all accumulated cases for this item."""
        self._flush_sub_case()

        if not self._current_item_cases or self._item_num is None:
            self._current_item_cases = []
            self._item_num = None
            return

        for case in self._current_item_cases:
            self.stats["total"] += 1

            single_party = not case["vs_seen"] and case["petitioner"] and not case["respondent"]

            missing = []
            if not case["case_number"]:
                missing.append("case_number")
            if not case["petitioner"]:
                missing.append("petitioner")
            if not case["respondent"] and not single_party:
                missing.append("respondent")

            if not missing:
                self.stats["regex_ok"] += 1
            elif len(missing) == 1 and missing[0] == "respondent" and single_party:
                self.stats["regex_ok"] += 1
            elif len(missing) <= 1:
                self.stats["partial"] += 1
            else:
                self.stats["llm_needed"] += 1

            self.records.append({
                "item_number": self._item_num,
                "court_name": self.court_name,
                "court_no": self._bench,
                "listing_date": self.listing_date,
                "case_number": case["case_number"],
                "petitioner": case["petitioner"],
                "respondent": case["respondent"],
                "advocates": case["advocates"],
            })

        self._current_item_cases = []
        self._item_num = None

    def _process_row(self, row: list[dict], zones: dict):
        """Process a single row through the state machine."""
        if self._terminated:
            return

        z = row_to_zones(row, zones)
        full_text = ' '.join(w['text'] for w in row)

        # Skip page footers
        if PAGE_FOOTER_RE.search(full_text):
            return

        # Hard stop — mediation section is a different document
        if self.TERMINATION_RE.search(full_text):
            self._flush_item()
            self._terminated = True
            return

        # Skip admin / noise text
        if self.ADMIN_SKIP_RE.search(full_text):
            return

        # Skip legal boilerplate (batta, notice, etc.)
        if self.LEGAL_BOILERPLATE_RE.search(full_text):
            return

        # ── (Concluded) = block separator, flush and continue scanning ──
        if self.CONCLUDED_RE.search(full_text):
            self._flush_item()
            self._pending_num = None
            return

        # Detect bench/court number header
        bench_m = BENCH_RE.search(full_text)
        if bench_m and len(full_text) < 100:
            self._flush_item()
            self._pending_num = None
            self._bench = bench_m.group(1)
            return

        item_zone = z.get('item_num', '').strip()
        case_id_zone = z.get('case_id', '').strip()

        # Strip (Filing No.) suffix from case_id zone
        case_id_zone = re.sub(r'\(Filing\s*No\.?\)', '', case_id_zone).strip()

        # Strip category tags like (Land.Ench.) but preserve case types like WP(MD)
        case_id_zone = CATEGORY_TAG_RE.sub('', case_id_zone).strip()

        # Strip TO CONDONE DELAY from parties zone only (not whole row)
        if 'parties' in z:
            z['parties'] = re.sub(
                r'TO\s+CONDONE\s+(?:THE\s+)?DELAY[^,\.]*', '', z.get('parties', '')
            ).strip()

        # Write cleaned case_id_zone back to zone dict
        z['case_id'] = case_id_zone

        # ── AND alone = sub-case boundary (but not AND ANOTHER / AND N OTHERS) ──
        is_and = (
            case_id_zone.strip() == 'AND'
            or item_zone.strip() == 'AND'
            or full_text.strip() == 'AND'
        ) and not re.search(r'AND\s+(?:ANOTHER|\d+\s+OTHERS)', full_text, re.I)
        if is_and and self._sub_case_rows:
            self._flush_sub_case()
            return

        if ITEM_NUM_RE.match(item_zone):
            case_on_same_row = bool(CASE_NUM_RE.search(z.get('case_id', '')))
            parties_on_same_row = bool(z.get('parties', '').strip())

            if case_on_same_row or parties_on_same_row:
                # Variant A: item number + data on same row
                self._flush_item()
                self._pending_num = None
                self._item_num = int(item_zone)
                self._sub_case_rows = [z]
            else:
                # Variant B: standalone item number, data on next row
                self._flush_item()
                self._pending_num = int(item_zone)
                self._sub_case_rows = []

        elif self._pending_num is not None:
            # First data row after a standalone item number
            self._item_num = self._pending_num
            self._pending_num = None
            self._sub_case_rows = [z]

        elif self._item_num is not None:
            # Continuation row for the current sub-case
            self._sub_case_rows.append(z)

    def parse_bytes(self, pdf_bytes: bytes, skip_pages: int = 5, max_pages: int | None = None) -> list[dict]:
        """
        Parse a PDF from bytes (for FastAPI integration).

        Args:
            pdf_bytes: Raw PDF file bytes
            skip_pages: Number of index/preamble pages to skip (default 5)
            max_pages: Maximum number of content pages to process (default: all)
        """
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            # Extract date from page 1
            if pdf.pages and not self.listing_date:
                date_str = extract_date_from_page(pdf.pages[0])
                if date_str:
                    self.listing_date = date_str

            content_pages = pdf.pages[skip_pages:]
            if max_pages is not None:
                content_pages = content_pages[:max_pages]

            # Process case pages (skip index/preamble)
            for page in content_pages:
                if self._terminated:
                    break
                rows = extract_rows(page)
                zones = detect_layout(rows)
                for row in rows:
                    if self._terminated:
                        break
                    self._process_row(row, zones)

            self._flush_item()

        logger.info(
            "Parsed %d items: regex_ok=%d, partial=%d, llm_needed=%d",
            self.stats["total"], self.stats["regex_ok"],
            self.stats["partial"], self.stats["llm_needed"],
        )
        return self.records

    def parse_file(self, pdf_path: str, skip_pages: int = 5) -> list[dict]:
        """Parse a PDF from a file path (for CLI usage)."""
        with open(pdf_path, 'rb') as f:
            return self.parse_bytes(f.read(), skip_pages=skip_pages)

    def summary(self) -> dict:
        s = self.stats
        t = s["total"] or 1
        return {
            "total_items": s["total"],
            "regex_success": s["regex_ok"],
            "partial": s["partial"],
            "llm_needed": s["llm_needed"],
            "regex_pct": round(100 * s["regex_ok"] / t, 1),
            "llm_pct": round(100 * s["llm_needed"] / t, 1),
        }

