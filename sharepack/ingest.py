"""PDF index and cautious Figure candidate extraction. No semantic inference."""
import re
from pathlib import Path
import fitz
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
    doc=fitz.open(pdf)
    if doc.is_encrypted:raise ContractError('PDF_ENCRYPTED')
    psha=digest(pdf)
    results={'contract':'sharepack-pdf-index-v1','pdf_name':pdf.name,'pdf_sha256':psha,'pages':len(doc),
             'science_review':'NOT_PERFORMED','figures':[], 'page_text':[]}
    text_dir=outdir/'_cache'/'text';text_dir.mkdir(parents=True,exist_ok=True)
    region_dir=outdir/'_cache'/'candidate_figures';region_dir.mkdir(parents=True,exist_ok=True)
    for pi,page in enumerate(doc):
        txt=page.get_text('text')
        tf=text_dir/f'page_{pi+1:02}.txt';tf.write_text(txt,encoding='utf-8')
        results['page_text'].append({'page':pi+1,'file':str(tf.relative_to(outdir)),'sha256':digest(tf)})
        blocks=[b for b in page.get_text('blocks') if len(b)>4 and isinstance(b[4],str)]
        for b in blocks:
            m=CAPTION.match(b[4])
            if not m:continue
            fig='Fig. '+m.group(1)
            cap_top=float(b[1]); top=40.0 # conservative, may include article text: candidate only
            bbox=fitz.Rect(38,top,page.rect.width-35,cap_top-6)
            if bbox.height<60:continue
            filename=f'figure_{int(m.group(1)):02}_page_{pi+1:02}_UNREVIEWED.png'
            p=region_dir/filename
            page.get_pixmap(matrix=fitz.Matrix(1.6,1.6),clip=bbox,alpha=False).save(p)
            results['figures'].append({'id':f'figure-{m.group(1)}-candidate-p{pi+1}',
                'figure_label':fig,'page':pi+1,'caption':b[4].strip()[:450],
                'candidate_path':str(p.relative_to(outdir)), 'candidate_sha256':digest(p),
                'candidate_rect_pdf_pt':list(bbox),'status':'CANDIDATE_NOT_PANEL_VERIFIED',
                'notice':'Candidate may include unrelated text or exclude parts. Review PDF and provide approved region manifest.'})
    save(outdir/'pdf_index.json',results)
    return results

def extract_regions(pdf,regions_path,outdir):
    """Read user/Agent-reviewed region coordinates (PDF points) from JSON, never infer panel identity."""
    pdf=Path(pdf).resolve(); data=__import__('json').loads(Path(regions_path).read_text(encoding='utf-8'))
    if not pdf.is_file():raise ContractError('PDF_NOT_FOUND')
    doc=fitz.open(pdf); psha=digest(pdf)
    if data.get('source_pdf_sha256')!=psha:raise ContractError('SOURCE_PDF_SHA_MISMATCH')
    if not data.get('regions'):raise ContractError('REGIONS_REQUIRED')
    outdir=Path(outdir); assets=[];seen=set()
    for a in data['regions']:
        id=a['id'];page_n=a['pdf_page'];raw=a['crop_pdf_pt']
        if id in seen or not re.fullmatch(r'[A-Za-z0-9_-]+',id):raise ContractError('DUPLICATE_OR_UNSAFE_ASSET_ID')
        seen.add(id)
        if not isinstance(page_n,int) or not 1<=page_n<=len(doc):raise ContractError('PAGE_OUT_OF_RANGE')
        if len(raw)!=4 or any(type(n) not in (float,int) for n in raw):raise ContractError('INVALID_CROP')
        box=fitz.Rect(*raw);bounds=doc[page_n-1].rect
        if box.is_empty or box.x0<bounds.x0 or box.y0<bounds.y0 or box.x1>bounds.x1 or box.y1>bounds.y1:raise ContractError('CROP_OUTSIDE_PDF')
        path=outdir/'assets'/f'{id}.png';path.parent.mkdir(parents=True,exist_ok=True)
        doc[page_n-1].get_pixmap(matrix=fitz.Matrix(2.4,2.4),clip=box,alpha=False).save(path)
        assets.append({'id':id,'figure':a['figure'],'pdf_page':page_n,'crop_pdf_pt':list(box),
             'path':str(path.relative_to(outdir)), 'sha256':digest(path),'source_pdf_sha256':psha,
             'review_status':a.get('review_status','PENDING'),
             'reviewer':a.get('reviewer'), 'license_note':a.get('license_note','source PDF; check article terms')})
    manifest={'contract':'sharepack-figure-assets-v1','source_pdf_name':pdf.name,'source_pdf_sha256':psha,
              'assets':assets,'original_data_unchanged':True}
    save(outdir/'assets.json',manifest)
    return manifest
