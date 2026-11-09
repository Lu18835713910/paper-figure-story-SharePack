"""Publication-source-driven editorial themes; no logos or publisher endorsement.

Routing uses the *uploaded document edition*, not an inferred eventual publication.
Journal palettes are deliberately original reinterpretations of editorial hierarchy,
not copies of journal covers, mastheads, typefaces, or official brand marks.
"""
from __future__ import annotations

import re
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass

DEFAULT_PALETTE = {
    "bg": "FBFCFE", "navy": "18354D", "royal": "205B83",
    "ink": "25394B", "muted": "566E7D", "border": "CBDBE7",
    "light": "EDF5FA", "white": "FFFFFF", "mint": "E7F3EF",
    "peach": "FDF1E4", "green": "246F5B", "line": "4084A5",
}

# No pure white text over white backgrounds. Body colors are designed for
# high contrast at phone size; figures remain source images, never recolored.
PROFILES = {
    "preprint-arxiv": {
        "display": "arXiv preprint",
        "masthead": "SHAREPACK  /  arXiv PREPRINT STYLE",
        "palette": {
            "bg": "1C1A17", "navy": "F5F4EF", "royal": "E8B5B5",
            "ink": "F5F4EF", "muted": "D0CCC6", "border": "6B6459",
            "light": "34312D", "white": "302D2A", "mint": "31434A",
            "peach": "47342F", "green": "E8B5B5", "line": "AB5559",
        },
        "source_note": "arXiv-inspired editorial hierarchy; not an official template or affiliation",
    },
    "preprint-neutral": {
        "display": "Unspecified preprint",
        "masthead": "SHAREPACK  /  PREPRINT RESEARCH NOTES",
        "palette": {
            "bg": "20252B", "navy": "F4F6F7", "royal": "BED3E4",
            "ink": "F4F6F7", "muted": "CDD4DA", "border": "65707B",
            "light": "323C45", "white": "29343F", "mint": "33463F",
            "peach": "483B37", "green": "9FD7C2", "line": "A3BAC9",
        },
        "source_note": "Neutral preprint editorial interpretation",
    },
    "journal-plos-computational-biology": {
        "display": "PLOS Computational Biology",
        "masthead": "SHAREPACK  /  PLOS COMP. BIOL. STYLE",
        "palette": {
            "bg": "17272C", "navy": "F5F8F7", "royal": "83E0CE",
            "ink": "F5F8F7", "muted": "D4DEDD", "border": "55767A",
            "light": "294348", "white": "243940", "mint": "285247",
            "peach": "4A4039", "green": "8CDCB5", "line": "6EB5AE",
        },
        "source_note": "PLOS-inspired clean editorial treatment; not a replica",
    },
    "journal-nature-communications": {
        "display": "Nature Communications",
        "masthead": "SHAREPACK  /  NATURE COMM. STYLE",
        "palette": {
            "bg": "1B222A", "navy": "F6F6F3", "royal": "F2B0B2",
            "ink": "F6F6F3", "muted": "D4D6D8", "border": "67737F",
            "light": "313A44", "white": "29343E", "mint": "334746",
            "peach": "533D40", "green": "B6DED0", "line": "E18A96",
        },
        "source_note": "Nature-portfolio-inspired restrained editorial treatment; not a replica",
    },
    "journal-cell-systems": {
        "display": "Cell Systems",
        "masthead": "SHAREPACK  /  CELL SYSTEMS STYLE",
        "palette": {
            "bg": "242422", "navy": "F7F5F1", "royal": "E9BB8F",
            "ink": "F7F5F1", "muted": "D6D2CD", "border": "766D63",
            "light": "373634", "white": "322F2C", "mint": "3B4741",
            "peach": "554138", "green": "A9CBB5", "line": "C7A184",
        },
        "source_note": "Cell Systems journal-inspired neutral editorial treatment; not a replica",
    },
    "journal-neutral": {
        "display": "Other journal",
        "masthead": "SHAREPACK  /  JOURNAL RESEARCH NOTES",
        "palette": {
            "bg": "222831", "navy": "F5F7F8", "royal": "B9D0E9",
            "ink": "F5F7F8", "muted": "CDD5DE", "border": "64717E",
            "light": "33404A", "white": "2D3741", "mint": "30463F",
            "peach": "49413B", "green": "A9CDBD", "line": "91B1D4",
        },
        "source_note": "Neutral journal editorial treatment; publisher identity not inferred",
    },
}

PREPRINT_WORDS = ("arxiv", "biorxiv", "medrxiv", "preprint", "预印本", "预印稿", "research square", "ssrn")
_ACTIVE_STYLE = ContextVar("sharepack_publication_style", default=None)


@dataclass(frozen=True)
class StyleSelection:
    style_id: str
    display: str
    journal: str
    source_type: str
    selected_from: str
    status: str
    warning: str
    cjk_font: str = "SimHei"
    latin_font: str = "Arial"

    @property
    def palette(self):
        return PROFILES[self.style_id]["palette"]

    @property
    def masthead(self):
        return PROFILES[self.style_id]["masthead"]

    def to_dict(self):
        return {
            "style_id": self.style_id, "display": self.display,
            "journal_metadata": self.journal, "source_type": self.source_type,
            "selected_from": self.selected_from, "status": self.status,
            "warning": self.warning, "cjk_font": self.cjk_font,
            "latin_font": self.latin_font, "palette": dict(self.palette),
            "not_publisher_affiliated": True,
            "source_note": PROFILES[self.style_id]["source_note"],
        }


def _mapped_journal(journal):
    s = journal.casefold().strip()
    if "plos computational biology" in s or "plos comput biol" in s or "plos comp biol" in s:
        return "journal-plos-computational-biology"
    if "nature communications" in s or "nat commun" in s:
        return "journal-nature-communications"
    if "cell systems" in s:
        return "journal-cell-systems"
    return "journal-neutral"


def _is_preprint(s):
    s = str(s).casefold()
    return any(x in s for x in PREPRINT_WORDS)


def select_style(paper):
    """Select from source-edition metadata. Never infer journal from article title.

    Explicit source_type takes precedence when provided; if the uploaded source
    is explicitly a preprint, a later journal citation cannot rebrand that PDF.
    """
    paper = paper or {}
    source_type = str(paper.get("source_type") or "").strip().lower()
    if source_type not in ("", "journal", "preprint"):
        raise ValueError("PUBLICATION_SOURCE_TYPE_UNKNOWN")
    journal = str(paper.get("journal") or "").strip()
    source_name = str(paper.get("preprint_server") or "").strip()
    doi = str(paper.get("doi") or "").strip()
    doc_hint = paper.get("publication_hint")
    hint = doc_hint if isinstance(doc_hint, dict) else {}
    if not journal and hint.get("source_type") == "journal":
        journal = str(hint.get("journal") or "").strip()
    if not source_name and hint.get("source_type") == "preprint":
        source_name = str(hint.get("preprint_server") or "").strip()
    preprint_marked = (_is_preprint(journal) or _is_preprint(source_name) or
                       doi.casefold().startswith("10.48550/arxiv.") or
                       doi.casefold().startswith("10.1101/"))
    if source_type == "preprint" or (source_type != "journal" and preprint_marked):
        is_arxiv = ("arxiv" in (source_name + " " + journal + " " + doi).casefold())
        sid = "preprint-arxiv" if is_arxiv else "preprint-neutral"
        return StyleSelection(sid, PROFILES[sid]["display"], journal, "preprint",
                              "explicit_source_type" if source_type else "preprint_identifier",
                              "ROUTED", "Preprint edition; do not claim a later journal layout.")
    if journal or source_type == "journal":
        sid = _mapped_journal(journal)
        return StyleSelection(sid, PROFILES[sid]["display"], journal, "journal",
                              "explicit_journal_metadata" if journal else "explicit_source_type",
                              "ROUTED" if journal else "FALLBACK_UNKNOWN_JOURNAL",
                              "Style inspiration only; journal name is not publisher approval.")
    return StyleSelection("preprint-neutral", PROFILES["preprint-neutral"]["display"],
                          "", "preprint", "journal_metadata_missing", "FALLBACK",
                          "No confirmed journal in source metadata; use neutral preprint style.")


def detect_publication_hint(first_page_text):
    """Cautious first-page PDF metadata hint; may be wrong and MUST be reviewed.

    Only examines first-page header slice, not citations throughout full manuscript.
    """
    head = re.sub(r"\s+", " ", str(first_page_text)[:3000]).casefold()
    if re.search(r"\bplos computational biology\b|\bplos comput biol\b", head):
        return {"source_type": "journal", "journal": "PLOS Computational Biology",
                "confidence": "PDF_HEADER_CANDIDATE", "review_status": "PENDING"}
    if re.search(r"\bnature communications\b|\bnat commun\b", head):
        return {"source_type": "journal", "journal": "Nature Communications",
                "confidence": "PDF_HEADER_CANDIDATE", "review_status": "PENDING"}
    if re.search(r"\bcell systems\b", head):
        return {"source_type": "journal", "journal": "Cell Systems",
                "confidence": "PDF_HEADER_CANDIDATE", "review_status": "PENDING"}
    if re.search(r"\barxiv\b|arxiv\s*:\s*\d{4}", head):
        return {"source_type": "preprint", "preprint_server": "arXiv",
                "confidence": "PDF_HEADER_CANDIDATE", "review_status": "PENDING"}
    if re.search(r"\bbiorxiv\b", head):
        return {"source_type": "preprint", "preprint_server": "bioRxiv",
                "confidence": "PDF_HEADER_CANDIDATE", "review_status": "PENDING"}
    return {"source_type": "unknown", "journal": None,
            "confidence": "NOT_DETECTED", "review_status": "PENDING"}


@contextmanager
def active_style(style):
    token = _ACTIVE_STYLE.set(style)
    try:
        yield
    finally:
        _ACTIVE_STYLE.reset(token)


def current_style():
    return _ACTIVE_STYLE.get()
