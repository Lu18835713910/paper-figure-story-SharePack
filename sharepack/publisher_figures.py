"""Source-verified, unreviewed original publisher Figure candidate fetchers.

This capability only supports the tested PLOS figure endpoint. A downloaded
original Figure is still pending scientific/panel inspection; its role, rights,
and correspondence to individual claims cannot be inferred from the URL alone.
"""
from __future__ import annotations
import hashlib
import io
import re
import urllib.request
from pathlib import Path
from PIL import Image

from .common import ContractError

PLOS_DOI = re.compile(r"^10\.1371/journal\.(?:pcbi|pbio|pone|pgen|ppat|pmed|pntd|pctr|pclm)\.\d{6,9}$",re.I)
PNG_SIGNATURE=b"\x89PNG\r\n\x1a\n"

def fetch_plos_original_figure(*,doi,figure_num,source_pdf_sha256,pdf_page,outdir):
    """Fetch unchanged PLOS publisher-hosted PNG for a specified Figure (not panel).

    Network source is hard-coded to the official PLOS domain, preventing arbitrary
    URL injection. PLOS may redirect to image storage; provenance records the
    canonical publisher endpoint, SHA and pixel size. All scientific review PENDING.
    """
    if not isinstance(doi,str) or not PLOS_DOI.fullmatch(doi):
        raise ContractError("OFFICIAL_FIGURE_UNSUPPORTED_DOI")
    if isinstance(figure_num,bool) or not isinstance(figure_num,int) or not 1<=figure_num<=100:
        raise ContractError("OFFICIAL_FIGURE_INVALID_NUMBER")
    if not isinstance(source_pdf_sha256,str) or not re.fullmatch(r"[0-9a-f]{64}",source_pdf_sha256):
        raise ContractError("OFFICIAL_FIGURE_SOURCE_PDF_SHA_REQUIRED")
    if isinstance(pdf_page,bool) or not isinstance(pdf_page,int) or pdf_page<1:
        raise ContractError("OFFICIAL_FIGURE_PDF_PAGE_INVALID")
    url=("https://journals.plos.org/ploscompbiol/article/figure/image"
         f"?size=large&id={doi}.g{figure_num:03d}")
    # The tested source is PLOS Computational Biology. Do not silently use that
    # journal endpoint for a different PLOS imprint.
    if not doi.lower().startswith("10.1371/journal.pcbi."):
        raise ContractError("OFFICIAL_FIGURE_IMPRINT_NOT_IMPLEMENTED")
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 SharePack source-evidence QA"})
    try:
        with urllib.request.urlopen(req,timeout=35) as response:
            content_type=response.headers.get("Content-Type","")
            data=response.read(12_000_001)
    except Exception as ex:
        raise ContractError("OFFICIAL_FIGURE_DOWNLOAD_FAILED") from ex
    if len(data)>12_000_000 or not data.startswith(PNG_SIGNATURE) or "image/png" not in content_type.lower():
        raise ContractError("OFFICIAL_FIGURE_NOT_VALID_PNG_RESPONSE")
    try:
        with Image.open(io.BytesIO(data)) as img:
            if img.format!="PNG" or img.width<500 or img.height<300:
                raise ContractError("OFFICIAL_FIGURE_INSUFFICIENT_RESOLUTION")
            dims=(img.width,img.height)
            img.verify()
    except (OSError,ValueError) as ex:
        raise ContractError("OFFICIAL_FIGURE_IMAGE_INVALID") from ex
    path=Path(outdir)/"assets"/f"plos_figure_{figure_num:02d}_unreviewed.png"
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        raise ContractError("OFFICIAL_FIGURE_OUTPUT_EXISTS")
    path.write_bytes(data)
    return {
        "id":f"plos_fig_{figure_num:02d}","figure":f"Fig. {figure_num}",
        "pdf_page":pdf_page,"path":str(path.relative_to(Path(outdir))),
        "sha256":hashlib.sha256(data).hexdigest(),
        "source_pdf_sha256":source_pdf_sha256,"pixel_dimensions":list(dims),
        "source_url":url,"source_kind":"PUBLISHER_ORIGINAL_FULL_FIGURE",
        "review_status":"PENDING","evidence_role":"UNBOUND_FIGURE_REQUIRES_REVIEW",
        "license_note":"PLOS article CC BY 4.0; check original article and attribution; trademark license is separate",
        "panel_labels":[],"crop_pdf_pt":None,
    }
