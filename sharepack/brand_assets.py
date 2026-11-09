"""Optional publisher logo in the source attribution rail, never an invented logo.

A journal article open-access license does not grant use of its publisher's
trademark. No logo is downloaded or bundled automatically. The requester must
supply the unchanged authorized PNG and document its display permission.
"""
from __future__ import annotations
import hashlib
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from PIL import Image
from .common import ContractError, load

_LOGO = ContextVar("sharepack_licensed_logo", default=None)

@dataclass(frozen=True)
class VerifiedLogo:
    path: Path
    style_id: str
    publisher_name: str
    original_sha256: str
    source_url: str
    permission_url: str
    rights_basis: str
    width_px: int
    height_px: int

    def report(self):
        return {
            "status": "DISPLAYED_WITH_DOCUMENTED_PERMISSION",
            "publisher_name": self.publisher_name,
            "style_id": self.style_id,
            "original_sha256": self.original_sha256,
            "original_source_url": self.source_url,
            "permission_evidence_url": self.permission_url,
            "rights_basis": self.rights_basis,
            "unaltered_logo": True,
            "not_publisher_affiliated": True,
        }

def check_logo(manifest_path, selected_style, paper):
    """Fail closed on non-matching or unlicensed marks, never rebrand a preprint."""
    if manifest_path is None:
        return None
    p = Path(manifest_path).resolve()
    data = load(p)
    if data.get("contract") != "sharepack-journal-logo-v1":
        raise ContractError("LOGO_MANIFEST_SCHEMA_UNKNOWN")
    expected_style = selected_style.style_id
    if data.get("style_id") != expected_style:
        raise ContractError("LOGO_PUBLICATION_STYLE_MISMATCH")
    if data.get("doi") != paper.get("doi"):
        raise ContractError("LOGO_PAPER_DOI_MISMATCH")
    if data.get("source_type") != selected_style.source_type:
        raise ContractError("LOGO_SOURCE_EDITION_MISMATCH")
    if selected_style.status in ("FALLBACK", "FALLBACK_UNKNOWN_JOURNAL",
                                 "CANDIDATE_REQUIRES_VERIFICATION"):
        raise ContractError("LOGO_SOURCE_IDENTITY_NOT_VERIFIED")
    if data.get("rights_basis") not in ("written_permission", "explicit_display_license"):
        raise ContractError("LOGO_PERMISSION_NOT_DOCUMENTED")
    if not all(data.get(k) for k in ("publisher_name","source_url","permission_evidence_url",
                                     "original_sha256","file")):
        raise ContractError("LOGO_PROVENANCE_INCOMPLETE")
    loc = (p.parent / data["file"]).resolve()
    if not loc.is_relative_to(p.parent) or loc.suffix.lower() != ".png":
        raise ContractError("LOGO_FILE_INVALID_OR_OUTSIDE_MANIFEST")
    if not loc.is_file():
        raise ContractError("LOGO_FILE_MISSING")
    dig = hashlib.sha256(loc.read_bytes()).hexdigest()
    if dig != data["original_sha256"]:
        raise ContractError("LOGO_HASH_MISMATCH")
    try:
        with Image.open(loc) as im:
            if im.format != "PNG":
                raise ContractError("LOGO_NOT_PNG")
            w,h=im.size
            im.verify()
    except (OSError,ValueError) as e:
        raise ContractError("LOGO_PNG_INVALID") from e
    if min(w,h) < 48 or max(w,h) < 160 or w/h > 12 or h/w > 3:
        raise ContractError("LOGO_RESOLUTION_OR_RATIO_INVALID")
    return VerifiedLogo(loc,expected_style,data["publisher_name"],dig,data["source_url"],
                        data["permission_evidence_url"],data["rights_basis"],w,h)

@contextmanager
def active_logo(logo):
    token = _LOGO.set(logo)
    try:
        yield
    finally:
        _LOGO.reset(token)

def current_logo():
    return _LOGO.get()
