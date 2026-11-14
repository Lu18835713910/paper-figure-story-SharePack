"""Reviewed Figure extraction for SharePack, R18 isolated integration candidate.

This is a provenance tool: it does not check scientific conclusions, confer
rights to redistribute images, or generate biological interpretations.

Run via the optional SharePack CLI integration or ``python -m sharepack.figure_evidence``.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
from pathlib import Path

from .pdf_backend import Document, valid_clip
from .common import ContractError
from PIL import Image

PLAN_VERSION = 'sharepack-reviewed-figure-plan-v2'
MANIFEST_VERSION = 'sharepack-reviewed-figure-manifest-v2'
IDENT = re.compile(r'^[A-Za-z][A-Za-z0-9_-]{1,39}$')


class FigureEvidenceError(ValueError):
    """A reviewed Figure plan or its immutable evidence is invalid."""


def reject(code: str) -> None:
    raise FigureEvidenceError(code)


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize(s: str) -> str:
    return re.sub(r'\s+', ' ', s).casefold().strip()


def _get_pdf(pdf: Path):
    if not pdf.is_file() or pdf.suffix.lower() != '.pdf':
        reject('PDF_INPUT_NOT_FOUND')
    with pdf.open('rb') as stream:
        if stream.read(5) != b'%PDF-':
            reject('PDF_HEADER_INVALID')
    try:
        return Document(pdf)
    except ContractError as exc:
        reject(str(exc))


def _caption_verified(doc, no: int, cap_page: int, phrase: str, number: int) -> bool:
    """Figure captions may appear on the figure page or its following page.

    The exact Fig.N caption heading is mandatory. Mere mentions of Fig.N
    in the paper body or the caption of a different Figure never qualify.
    """
    if not isinstance(cap_page, int) or cap_page not in (no, no + 1) or cap_page > len(doc):
        reject('CAPTION_PAGE_NOT_SAME_OR_NEXT')
    page_text = doc[cap_page - 1].text
    prefix = re.compile(r'(?im)^\s*(?:Fig\.?|Figure\.?)\s*' + str(number) + r'(?:[ 	]*[|:.]|[ 	]*$)')
    if not prefix.search(page_text):
        reject('CAPTION_FIGURE_NUMBER_MISMATCH')
    if not phrase or normalize(phrase) not in normalize(page_text):
        reject('CAPTION_PHRASE_NOT_FOUND')
    # Reject an unrelated exact phrase from text elsewhere on the page:
    # require it to begin with the requested Figure caption prefix.
    if not re.match(r'(?i)^(?:fig\.?|figure\.?)\s*' + str(number) + r'(?:[ 	]*[|:.]|[ \t]*\n)', phrase.strip()):
        reject('CAPTION_PHRASE_NOT_HEAD_ANCHORED')
    return True


def scan(pdf_path: Path) -> dict:
    pdf_path = Path(pdf_path).resolve()
    with _get_pdf(pdf_path) as doc:
        pages = []
        for i, page in enumerate(doc, 1):
            words = page.text
            caps = sorted({int(m.group(1)) for m in re.finditer(r'(?im)^\s*(?:Fig\.?|Figure\.?)\s*(\d+)\s*[|:.]', words)})
            refs = []
            for xref, image in page.displayed_images.items():
                refs.append({'xref': xref, 'width_px': image.image.width, 'height_px': image.image.height,
                             'image_sha256': digest_bytes(image.data)})
            pages.append({'pdf_page': i, 'caption_headers': caps, 'image_candidates': refs})
        return {'status': 'CANDIDATES_ONLY', 'paper_pdf_sha256': digest(pdf_path),
                'pdf_pages': len(doc), 'pages': pages, 'science_review': 'NOT_PERFORMED'}


def _specs(doc, pdf_sha, plan):
    if not isinstance(plan, dict):
        reject('PLAN_SCHEMA_UNSUPPORTED')
    if plan.get('contract') != PLAN_VERSION:
        reject('PLAN_SCHEMA_UNSUPPORTED')
    if plan.get('paper_pdf_sha256') != pdf_sha:
        reject('PDF_SHA_MISMATCH')
    if plan.get('review_decision') != 'FIGURE_PLAN_APPROVED_FOR_PRIVATE_REVIEW':
        reject('EXPLICIT_PLAN_REVIEW_REQUIRED')
    items = plan.get('figures', [])
    if not isinstance(items, list) or not items:
        reject('NO_FIGURES_SELECTED')
    used = set()
    for item in items:
        fid = item.get('id')
        if not isinstance(fid, str) or not IDENT.fullmatch(fid) or fid in used:
            reject('DUPLICATE_OR_UNSAFE_FIGURE_ID')
        used.add(fid)
        num, pg, cap = item.get('figure_number'), item.get('image_pdf_page'), item.get('caption_pdf_page')
        if type(num) is not int or num < 1 or type(pg) is not int or not 1 <= pg <= len(doc):
            reject('FIGURE_NUMBER_OR_PAGE_INVALID')
        _caption_verified(doc, pg, cap, item.get('caption_phrase', ''), num)
        if item.get('method') not in ('original_pdf_xobject', 'approved_pdf_region'):
            reject('UNKNOWN_METHOD')
        yield item


def _extract_item(doc, item):
    page = doc[item['image_pdf_page'] - 1]
    mode = item['method']
    if mode == 'original_pdf_xobject':
        xref = item.get('approved_xref')
        if type(xref) is not int:
            reject('APPROVED_XREF_REQUIRED')
        image = page.displayed_images.get(xref)
        if image is None:
            reject('XREF_NOT_DRAWN_ON_FIGURE_PAGE')
        width, height = image.image.size
        if width * height < 100_000:
            reject('IMAGE_TOO_SMALL_FOR_REVIEW')
        original_sha = digest_bytes(image.data)
        if item.get('expected_image_sha256') and item['expected_image_sha256'] != original_sha:
            reject('XOBJECT_SOURCE_HASH_MISMATCH')
        return image.data, Path(image.name).suffix.lstrip('.'), {
            'approved_xref': xref, 'original_xobject_sha256': original_sha,
            'width_px': width, 'height_px': height, 'derived_from_pdf_region': False}
    coords = item.get('pdf_clip_pt')
    if (not isinstance(coords, list) or len(coords) != 4 or
            any(type(n) not in (int, float) for n in coords)):
        reject('APPROVED_CLIP_REQUIRED')
    if not valid_clip(coords, page.width, page.height):
        reject('CLIP_OUTSIDE_PDF_PAGE')
    dpi = item.get('dpi', 250)
    if type(dpi) is not int or dpi < 144 or dpi > 400:
        reject('DPI_OUT_OF_REVIEW_RANGE')
    data = page.png(dpi / 72, clip=coords)
    return data, 'png', {'pdf_clip_pt': coords, 'dpi': dpi, 'derived_from_pdf_region': True}


def extract_reviewed(pdf_path: str | Path, plan_path: str | Path, output: str | Path) -> dict:
    pdf_path, plan_path, output = Path(pdf_path).resolve(), Path(plan_path).resolve(), Path(output).resolve()
    if output.exists() and any(output.iterdir()):
        reject('OUTPUT_DIRECTORY_NOT_EMPTY')
    if output == pdf_path.parent or output == plan_path.parent:
        reject('REFUSE_SOURCE_DIRECTORY_AS_OUTPUT')
    plan = json.loads(plan_path.read_text(encoding='utf-8'))
    psha = digest(pdf_path)
    staged = []
    with _get_pdf(pdf_path) as doc:
        for item in _specs(doc, psha, plan):
            image, ext, details = _extract_item(doc, item)
            with Image.open(io.BytesIO(image)) as im:
                im.verify()
            name = item['id'] + '.' + ext
            staged.append({'asset_id': item['id'], 'figure_number': item['figure_number'],
                'filename': name, 'sha256': digest_bytes(image), 'image_pdf_page': item['image_pdf_page'],
                'caption_pdf_page': item['caption_pdf_page'], 'caption_phrase': item['caption_phrase'],
                'method': item['method'], 'science_review': 'NOT_PERFORMED',
                'rights_review': 'NOT_PERFORMED', **details, '_bytes': image})
    output.mkdir(parents=True, exist_ok=True)
    final_items = []
    for item in staged:
        raw = item.pop('_bytes')
        (output / item['filename']).write_bytes(raw)
        final_items.append(item)
    manifest = {'contract': MANIFEST_VERSION, 'paper_pdf_sha256': psha,
        'plan_sha256': digest(plan_path), 'pdf_engine': 'PDFium+pypdf', 'source_pdf_basename': pdf_path.name,
        'figures': final_items, 'verify_status': 'PENDING_VERIFICATION',
        'science_review': 'NOT_PERFORMED', 'rights_status': plan.get('rights_status', 'UNKNOWN'),
        'publication_status': 'NO_GO_PRIVATE_REVIEW_ONLY'}
    (output / 'figure_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    # A compatible asset manifest is intentionally PENDING until a reviewer binds
    # the panel identity and checks the scientific claim. Never mark VISUAL_REVIEWED.
    asset_items = []
    for it in final_items:
        asset_items.append({'id': it['asset_id'], 'figure': f"Figure {it['figure_number']}",
            'pdf_page': it['image_pdf_page'], 'caption_pdf_page': it['caption_pdf_page'],
            'path': it['filename'], 'sha256': it['sha256'], 'source_pdf_sha256': psha,
            'review_status': 'PENDING', 'evidence_role': 'UNBOUND_FIGURE_REQUIRES_REVIEW',
            'license_note': manifest['rights_status']})
    assets = {'contract': 'sharepack-figure-assets-v1', 'source_pdf_sha256': psha,
              'source_pdf_name': pdf_path.name, 'assets': asset_items,
              'science_review': 'NOT_PERFORMED', 'original_data_unchanged': True}
    (output / 'assets.json').write_text(json.dumps(assets, ensure_ascii=False, indent=2), encoding='utf-8')
    return manifest


def verify_reviewed(pdf_path: str | Path, manifest_path: str | Path, plan_path: str | Path | None = None) -> dict:
    pdf_path, manifest_path = Path(pdf_path).resolve(), Path(manifest_path).resolve()
    manifest = json.loads(manifest_path.read_text('utf-8'))
    if not isinstance(manifest, dict) or manifest.get('contract') != MANIFEST_VERSION:
        reject('MANIFEST_SCHEMA_UNSUPPORTED')
    if manifest.get('paper_pdf_sha256') != digest(pdf_path):
        reject('PDF_SHA_MISMATCH')
    # A source-byte audit is not a reviewed-Figure binding audit without the
    # immutable approved plan. The plan hash alone is insufficient because
    # manifest fields can be rewritten while preserving that hash.
    if plan_path is None:
        reject('APPROVED_PLAN_REQUIRED_FOR_VERIFICATION')
    plan_path = Path(plan_path).resolve()
    if manifest.get('plan_sha256') != digest(plan_path):
        reject('PLAN_SHA_MISMATCH')
    plan = json.loads(plan_path.read_text('utf-8'))
    figures = manifest.get('figures', [])
    if not isinstance(figures, list) or not figures or any(not isinstance(it,dict) for it in figures):
        reject('EMPTY_MANIFEST')
    if len({it.get('asset_id') for it in figures}) != len(figures):
        reject('DUPLICATE_MANIFEST_ASSET_IDS')
    with _get_pdf(pdf_path) as doc:
        approved = list(_specs(doc, manifest['paper_pdf_sha256'], plan))
        if len(figures) != len(approved):
            reject('PLAN_MANIFEST_BINDING_DRIFT:COUNT')
        expected = {item['id']: item for item in approved}
        if {it.get('asset_id') for it in figures} != set(expected):
            reject('PLAN_MANIFEST_BINDING_DRIFT:IDS')
        for it in figures:
            ap = expected[it['asset_id']]
            # Source, figure-number, caption and selection method are a single
            # approved unit, not independent mutable labels in a JSON manifest.
            for mk, pk in [('figure_number','figure_number'),('image_pdf_page','image_pdf_page'),
                           ('caption_pdf_page','caption_pdf_page'),('caption_phrase','caption_phrase'),
                           ('method','method')]:
                if it.get(mk) != ap.get(pk):
                    reject('PLAN_MANIFEST_BINDING_DRIFT:' + str(it['asset_id']) + ':' + mk)
            if ap['method'] == 'original_pdf_xobject':
                if it.get('approved_xref') != ap.get('approved_xref'):
                    reject('PLAN_MANIFEST_BINDING_DRIFT:XREF')
                if (ap.get('expected_image_sha256') and
                        it.get('original_xobject_sha256') != ap['expected_image_sha256']):
                    reject('PLAN_MANIFEST_BINDING_DRIFT:SOURCE_HASH')
            else:
                if (it.get('pdf_clip_pt') != ap.get('pdf_clip_pt') or
                        it.get('dpi') != ap.get('dpi',250)):
                    reject('PLAN_MANIFEST_BINDING_DRIFT:CLIP')
            name = it.get('filename')
            if not isinstance(name, str) or '/' in name or '\\' in name or not IDENT.fullmatch(Path(name).stem):
                reject('UNSAFE_ASSET_FILENAME')
            file = manifest_path.parent / name
            if not file.is_file() or digest(file) != it.get('sha256'):
                reject('FIGURE_HASH_DRIFT:' + str(it.get('asset_id')))
            try:
                with Image.open(file) as im:
                    im.verify()
            except (OSError, ValueError):
                reject('INVALID_IMAGE:' + name)
            number = it.get('figure_number')
            _caption_verified(doc, it.get('image_pdf_page'), it.get('caption_pdf_page'),
                              it.get('caption_phrase', ''), number)
            image, _, details = _extract_item(doc, {**it, 'approved_xref': it.get('approved_xref'),
                    'method': it['method'], 'pdf_clip_pt': it.get('pdf_clip_pt'),
                    'dpi': it.get('dpi'), 'expected_image_sha256': it.get('original_xobject_sha256')})
            if digest_bytes(image) != it.get('sha256'):
                reject('FIGURE_NO_LONGER_MATCHES_SOURCE_PDF:' + name)
    # Downstream SharePack receives assets.json rather than figure_manifest.json.
    # That handoff must preserve Figure identity, caption page, bytes and path.
    asset_path = manifest_path.parent / 'assets.json'
    if not asset_path.is_file():
        reject('COMPATIBLE_ASSET_MANIFEST_REQUIRED')
    assets = json.loads(asset_path.read_text('utf-8'))
    if not isinstance(assets,dict):
        reject('COMPATIBLE_ASSET_MANIFEST_INVALID')
    if (assets.get('contract') != 'sharepack-figure-assets-v1' or
            assets.get('source_pdf_sha256') != manifest['paper_pdf_sha256']):
        reject('COMPATIBLE_ASSET_MANIFEST_INVALID')
    records = assets.get('assets', [])
    if (not isinstance(records,list) or any(not isinstance(a,dict) for a in records) or
            len(records) != len(figures) or
            len({a.get('id') for a in records}) != len(records)):
        reject('ASSET_MANIFEST_BINDING_DRIFT:COUNT')
    ref = {it['asset_id']: it for it in figures}
    if {a.get('id') for a in records} != set(ref):
        reject('ASSET_MANIFEST_BINDING_DRIFT:IDS')
    for a in records:
        src = ref[a['id']]
        expected = {'figure':f"Figure {src['figure_number']}",'pdf_page':src['image_pdf_page'],
                    'caption_pdf_page':src['caption_pdf_page'],'path':src['filename'],
                    'sha256':src['sha256'],'source_pdf_sha256':manifest['paper_pdf_sha256']}
        for key, value in expected.items():
            if a.get(key) != value:
                reject('ASSET_MANIFEST_BINDING_DRIFT:' + a['id'] + ':' + key)
    return {'status': 'PASS_SOURCE_BYTES_ONLY', 'figure_count': len(figures),
            'paper_pdf_sha256': digest(pdf_path), 'reviewed_plan_binding': True,
            'compatible_asset_binding': True,'science_verified': False,
            'publication_ready': False}


def main(argv=None):
    parser = argparse.ArgumentParser(prog='python -m sharepack.figure_evidence')
    sub = parser.add_subparsers(dest='action', required=True)
    p = sub.add_parser('scan'); p.add_argument('--pdf', required=True); p.add_argument('--out', required=True)
    p = sub.add_parser('extract'); p.add_argument('--pdf', required=True); p.add_argument('--plan', required=True); p.add_argument('--outdir', required=True)
    p = sub.add_parser('verify'); p.add_argument('--pdf', required=True); p.add_argument('--manifest', required=True); p.add_argument('--plan', required=True)
    args = parser.parse_args(argv)
    try:
        if args.action == 'scan':
            result = scan(Path(args.pdf)); Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2), 'utf-8')
        elif args.action == 'extract':
            result = extract_reviewed(args.pdf, args.plan, args.outdir)
        else:
            result = verify_reviewed(args.pdf, args.manifest, args.plan)
        print(json.dumps(result if args.action != 'extract' else {'status': 'PASS', 'extracted': len(result['figures']), 'science_review': 'NOT_PERFORMED'}, ensure_ascii=False))
        return 0
    except (FigureEvidenceError, OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({'status': 'FAIL', 'error': str(exc)}, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
