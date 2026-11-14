"""PDF index and cautious Figure candidate extraction. No semantic inference."""
import re
from pathlib import Path
from .pdf_backend import Document, valid_clip
from .common import ContractError,digest,save

CAPTION=re.compile(r'^\s*Fig(?:ure)?\.?\s*(\d+)\s*[.:|]\s*',re.I)

def inspect_pdf(pdf,outdir):
    pdf=Path(pdf).resolve();outdir=Path(outdir)
    if not pdf.is_file() or pdf.suffix.lower()!='.pdf':
        raise ContractError('PDF_INPUT_INVALID')
    with pdf.open('rb') as stream:
        if stream.read(5)!=b'%PDF-':raise ContractError('PDF_INPUT_INVALID')
    if outdir.resolve().is_relative_to(pdf.parent) and outdir.resolve()==pdf.parent:
        raise ContractError('OUTPUT_MUST_BE_ISOLATED')
    doc=Document(pdf)
    psha=digest(pdf)
    results={'contract':'sharepack-pdf-index-v1','pdf_name':pdf.name,'pdf_sha256':psha,'pages':len(doc),
             'science_review':'NOT_PERFORMED','figures':[], 'page_text':[]}
    text_dir=outdir/'_cache'/'text';text_dir.mkdir(parents=True,exist_ok=True)
    for pi,page in enumerate(doc):
        txt=page.text
        tf=text_dir/f'page_{pi+1:02}.txt';tf.write_text(txt,encoding='utf-8')
        results['page_text'].append({'page':pi+1,'file':str(tf.relative_to(outdir)),'sha256':digest(tf)})
        # Caption discovery is text-only; a reviewed plan supplies crop geometry.
        for line in txt.splitlines():
            m=CAPTION.match(line)
            if m:
                results['figures'].append({'id':f'figure-{m.group(1)}-candidate-p{pi+1}',
                    'figure_label':'Fig. '+m.group(1),'page':pi+1,'caption':line.strip()[:450],
                    'status':'CAPTION_CANDIDATE_REQUIRES_REVIEWED_REGION'})
    doc.close()
    save(outdir/'pdf_index.json',results)
    return results

def extract_regions(pdf,regions_path,outdir):
    """Read user/Agent-reviewed region coordinates (PDF points) from JSON, never infer panel identity."""
    pdf=Path(pdf).resolve(); data=__import__('json').loads(Path(regions_path).read_text(encoding='utf-8'))
    if not pdf.is_file():raise ContractError('PDF_NOT_FOUND')
    doc=Document(pdf); psha=digest(pdf)
    if data.get('source_pdf_sha256')!=psha:raise ContractError('SOURCE_PDF_SHA_MISMATCH')
    if not data.get('regions'):raise ContractError('REGIONS_REQUIRED')
    outdir=Path(outdir); assets=[];seen=set()
    for a in data['regions']:
        id=a['id'];page_n=a['pdf_page'];raw=a['crop_pdf_pt']
        if id in seen or not re.fullmatch(r'[A-Za-z0-9_-]+',id):raise ContractError('DUPLICATE_OR_UNSAFE_ASSET_ID')
        seen.add(id)
        if not isinstance(page_n,int) or not 1<=page_n<=len(doc):raise ContractError('PAGE_OUT_OF_RANGE')
        if len(raw)!=4 or any(type(n) not in (float,int) for n in raw):raise ContractError('INVALID_CROP')
        page=doc[page_n-1]
        if not valid_clip(raw,page.width,page.height):raise ContractError('CROP_OUTSIDE_PDF')
        path=outdir/'assets'/f'{id}.png';path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(page.png(2.4,clip=raw))
        assets.append({'id':id,'figure':a['figure'],'pdf_page':page_n,'crop_pdf_pt':raw,
             'path':str(path.relative_to(outdir)), 'sha256':digest(path),'source_pdf_sha256':psha,
             'review_status':a.get('review_status','PENDING'),
             'reviewer':a.get('reviewer'), 'license_note':a.get('license_note','source PDF; check article terms')})
    manifest={'contract':'sharepack-figure-assets-v1','source_pdf_name':pdf.name,'source_pdf_sha256':psha,
              'assets':assets,'original_data_unchanged':True}
    doc.close()
    save(outdir/'assets.json',manifest)
    return manifest
