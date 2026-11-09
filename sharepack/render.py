"""Data-driven editable vertical PowerPoint renderer, no article-specific wording."""
from pathlib import Path
import json, re, zipfile, subprocess, tempfile, os
import fitz
from PIL import Image,ImageDraw
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE,MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches,Pt
from pptx.dml.color import RGBColor
from pptx.oxml.xmlchemy import OxmlElement
from .common import ContractError,digest,load,save,within
from .contract import validate_story
from .planning import panel_selection_audit
from .publication_styles import active_style, current_style, select_style
from .brand_assets import active_logo, current_logo, check_logo

PAL={'bg':'FBFCFE','navy':'18354D','royal':'205B83','ink':'25394B','muted':'566E7D','border':'CBDBE7',
    'light':'EDF5FA','white':'FFFFFF','mint':'E7F3EF','peach':'FDF1E4','green':'246F5B','line':'4084A5'}
def rgb(k):
    theme=current_style()
    h=(theme.palette.get(k,PAL.get(k,k)) if theme is not None else PAL.get(k,k)).lstrip('#')
    return RGBColor(*[int(h[i:i+2],16) for i in (0,2,4)])

def rect(sl,x,y,w,h,fill='white',stroke=None,rounded=False):
    t=sl.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE,
           Inches(x),Inches(y),Inches(w),Inches(h))
    t.fill.solid();t.fill.fore_color.rgb=rgb(fill)
    if stroke:t.line.color.rgb=rgb(stroke);t.line.width=Pt(.8)
    else:t.line.fill.background()
    return t

def text(sl,value,x,y,w,h,size=11,color='navy',bold=False,align=PP_ALIGN.LEFT):
    t=sl.shapes.add_textbox(Inches(x),Inches(y),Inches(w),Inches(h))
    f=t.text_frame;f.clear();f.word_wrap=True
    f.margin_top=f.margin_bottom=0;f.margin_left=f.margin_right=Inches(.02)
    p=f.paragraphs[0];p.alignment=align;p.line_spacing=1.11
    theme=current_style()
    latin_font=theme.latin_font if theme is not None else 'Times New Roman'
    cjk_font=theme.cjk_font if theme is not None else 'SimHei'
    for piece in re.findall(r'[\x00-\x7F]+|[^\x00-\x7F]+',str(value)):
        r=p.add_run();r.text=piece;r.font.name=latin_font if piece.isascii() else cjk_font
        r.font.size=Pt(size);r.font.color.rgb=rgb(color);r.font.bold=bold
        ea=OxmlElement('a:ea');ea.set('typeface',cjk_font);r._r.get_or_add_rPr().append(ea)
    return t

def embed_authorized_logo(sl, logo, x, y, w, h):
    """Keep the actual mark intact (aspect-preserving); no brand alteration."""
    ratio = logo.width_px/logo.height_px
    iw = min(w, h*ratio)
    ih = iw/ratio
    xx=x+(w-iw)/2
    yy=y+(h-ih)/2
    return sl.shapes.add_picture(str(logo.path), Inches(xx), Inches(yy),
                                 width=Inches(iw), height=Inches(ih))


def arrow(sl,x1,y1,x2,y2):
    if abs(x1-x2)>1e-6 and abs(y1-y2)>1e-6:raise ContractError('NONORTHOGONAL_ARROW')
    line=sl.shapes.add_connector(MSO_CONNECTOR.STRAIGHT,Inches(x1),Inches(y1),Inches(x2),Inches(y2))
    line.line.color.rgb=rgb('line');line.line.width=Pt(1.4)
    tri=sl.shapes.add_shape(MSO_SHAPE.ISOSCELES_TRIANGLE,Inches(x2-.045),Inches(y2-.045),Inches(.09),Inches(.09))
    tri.rotation=90 if x2>x1 else 270 if x2<x1 else 180 if y2>y1 else 0
    tri.fill.solid();tri.fill.fore_color.rgb=rgb('line');tri.line.fill.background()

def box_label(sl,label,body,y,h=.73,fill='light'):
    rect(sl,.51,y,6.48,h,fill,'border',True)
    text(sl,label,.69,y+.16,1.32,h-.18,11.8,'royal',True)
    text(sl,body,2.00,y+.13,4.75,h-.17,10.9,'navy')

def add_figure(sl,a,path,x,y,w,h):
    rect(sl,x,y,w,h,'white','border',True)
    with Image.open(path) as im: ratio=im.width/im.height
    avail_w=w-.24;avail_h=h-.52
    iw=min(avail_w,avail_h*ratio);ih=iw/ratio
    xx=x+(w-iw)/2;yy=y+.09+(avail_h-ih)/2
    sl.shapes.add_picture(str(path), Inches(xx),Inches(yy),width=Inches(iw),height=Inches(ih))
    text(sl, f"论文原图 {a['figure']} · p.{a['pdf_page']}",x+.12,y+h-.33,w-.24,.22,8.6,'muted')

def _cell_len(t):
    return sum(1.0 if ord(c)>127 else (0.55 if c.isalnum() else 0.35) for c in str(t))

def _checked_text(sl,value,x,y,w,h,size=11,color='navy',bold=False,align=PP_ALIGN.LEFT,*,label='text'):
    """Conservative, explicit text capacity gate; never silently omit/scissor data.

    This is not a substitute for a Windows PowerPoint render. It is a minimum
    guard: every text block is checked before it can enter the deck.
    """
    if not str(value).strip():return None
    # CJK characters approximately consume one fontsize square; include padding.
    capacity_per_line=max(1,w*72/(size*1.06))
    lines=max(1, int(__import__('math').ceil(_cell_len(value)/capacity_per_line)))
    line_in=size*1.25/72
    if lines*line_in>h+.065:
        raise ContractError(f'LAYOUT_TEXT_CAPACITY_EXCEEDED:{label}:needs_{lines}_lines')
    return text(sl,value,x,y,w,h,size,color,bold,align)

def _figure_box(sl,a,path,x,y,w,h):
    """Select already-extracted real panel; no synthetic scientific redraw."""
    rect(sl,x,y,w,h,'white','border',True)
    with Image.open(path) as im:ratio=im.width/im.height
    available_w=w-.20;available_h=h-.46
    iw=min(available_w,available_h*ratio);ih=iw/ratio
    xx=x+(w-iw)/2;yy=y+.09+(available_h-ih)/2
    sl.shapes.add_picture(str(path),Inches(xx),Inches(yy),width=Inches(iw),height=Inches(ih))
    caption=f"原文 {a['figure']} · PDF p.{a.get('pdf_page','?')}"
    if a.get('panel_labels'):caption+=' · '+','.join(a['panel_labels'])
    _checked_text(sl,caption,x+.12,y+h-.31,w-.23,.23,8.7,'muted',label='figure_caption')
    return {'asset_id':a['id'],'draw_width_in':round(iw,3),'draw_height_in':round(ih,3),
            'panel_labels':a.get('panel_labels',[]),'visual_review':a.get('review_status','PENDING')}

def _labelled_row(sl,heading,body,y,h,fill='light',size=10.4):
    rect(sl,.50,y,6.50,h,fill,'border',True)
    _checked_text(sl,heading,.67,y+.12,1.32,h-.14,11.0,'royal',True,label=heading)
    _checked_text(sl,body,1.94,y+.10,4.89,h-.12,size,'navy',label=heading+'_body')

def _place_visual(sl,c,aa,root,y,h,num):
    images=c.get('figure_asset_ids',[]); records=[]
    if images:
        if len(images)==1:
            a=aa[images[0]]
            records.append(_figure_box(sl,a,within(root,Path(root)/a['path']),.51,y,6.48,h))
        else:
            two=[aa[aid] for aid in images]
            ratios=[]
            for a in two:
                with Image.open(within(root,Path(root)/a['path'])) as im:ratios.append(im.width/im.height)
            # The full-width stacked arrangement is often more readable for 2 wide plots.
            stacked=all(r>=1.8 for r in ratios) and h>=2.4
            for j,a in enumerate(two):
                if stacked:
                    records.append(_figure_box(sl,a,within(root,Path(root)/a['path']),.51,y+(h/2)*j,6.48,h/2-.025))
                else:
                    records.append(_figure_box(sl,a,within(root,Path(root)/a['path']),.51+3.30*j,y,3.18,h))
    else:
        rect(sl,.51,y,6.48,h,'white','border',True)
        flow=c.get('flow_steps',[])
        if flow and 2<=len(flow)<=5:
            n=len(flow);cell=6.05/n
            for j,step in enumerate(flow):
                xx=.72+j*cell
                rect(sl,xx,y+h*.39,cell-.19,.88,['light','mint','peach','light','mint'][j],rounded=True)
                _checked_text(sl,step,xx+.055,y+h*.39+.20,cell-.30,.50,10.5,'royal',True,PP_ALIGN.CENTER,
                              label=f'card{num}_flow{j}')
                if j<n-1:arrow(sl,xx+cell-.17,y+h*.39+.45,xx+cell-.04,y+h*.39+.45)
            _checked_text(sl,'论文科研逻辑示意（不代表实验数据或时间先后）',.87,y+h-.35,5.84,.24,8.7,
                          'muted',align=PP_ALIGN.CENTER,label='flow_disclaimer')
        else:
            note=c.get('visual_note') or c['observation']
            _checked_text(sl,note,.97,y+.65,5.55,min(1.0,h-.8),14.1,'royal',True,PP_ALIGN.CENTER,label='visual_note')
    return records

def _bottom_explanation(sl,c,claims,y,metric,limits,num):
    _labelled_row(sl,'实际发现',c['observation'],y,.55,'light',10.3);y+=.63
    # A valid input may hold multiple metrics. Every one is present or rendering fails.
    for j,m in enumerate(metric):
        tx=f"{m['label']}：{m['value']}｜{m['definition']}；对照：{m['comparison']}"
        rect(sl,.51,y,6.48,.46,'mint',rounded=True)
        _checked_text(sl,tx,.65,y+.075,6.17,.34,9.7,'navy',label=f'card{num}_metric{j}')
        y+=.51
    if not metric:
        rect(sl,.51,y,6.48,.43,'mint',rounded=True)
        _checked_text(sl,c['interpretation'],.66,y+.08,6.14,.29,10.0,'navy',label=f'card{num}_interpretation')
        y+=.48
    rect(sl,.51,y,6.48,.46,'light',rounded=True)
    _checked_text(sl,'这说明什么',.65,y+.10,1.35,.27,10.4,'royal',True,label='meaning_label')
    _checked_text(sl,c['takeaway'],1.95,y+.09,4.87,.33,9.9,'navy',label=f'card{num}_takeaway')
    y+=.53
    rect(sl,.51,y,6.48,.41,'peach',rounded=True)
    _checked_text(sl,'证据边界',.65,y+.085,1.26,.27,9.9,'royal',True,label='limit_label')
    _checked_text(sl,'；'.join(limits),1.84,y+.075,4.99,.30,9.0,'navy',label=f'card{num}_limit')
    y+=.41
    if y>9.20:raise ContractError(f'LAYOUT_PAGE_CAPACITY_EXCEEDED:CARD_{num}:end_{y:.2f}')
    return y

def slides(story,assets,root):
    prs=Presentation();prs.slide_width=Inches(7.5);prs.slide_height=Inches(10);layout=prs.slide_layouts[6]
    aa={x['id']:x for x in assets['assets']};claims={x['id']:x for x in story['claims']}
    geometry=[]
    for num,c in enumerate(story['cards'],1):
        s=prs.slides.add_slide(layout)
        role=c.get('layout_type')
        if role not in ('cover','framework','evidence','comparison','synthesis','method'):
            stage=c.get('stage','').lower()
            role=('framework' if ('框架' in stage or 'map' in stage) else
                  'synthesis' if ('结论' in stage or '综合' in stage or 'summary' in stage) else
                  'cover' if ('封面' in stage or '研究问题' in stage or 'cover' in stage) else 'evidence')
        rect(s,0,0,7.5,10,'bg');rect(s,0,0,7.5,.055,'navy')
        logo=current_logo()
        if logo is not None:
            embed_authorized_logo(s,logo,.48,.15,1.22,.42)
            _checked_text(s,(current_style().masthead if current_style() else 'PFS / RESEARCH NOTES'),1.83,.24,4.10,.29,9.2,'royal',True,label='masthead')
        else:
            _checked_text(s,(current_style().masthead if current_style() else 'PFS / RESEARCH NOTES'),.48,.24,5.50,.29,10.1,'royal',True,label='masthead')
        _checked_text(s,f'{num:02} / {len(story["cards"]):02}',6.19,.24,.78,.28,10.8,'muted',align=PP_ALIGN.RIGHT,label='counter')
        rect(s,.48,.70,6.52,.012,'border')
        rect(s,.48,.87,min(4.6,max(1.40,_cell_len(c['stage'])*.13+.32)),.33,'light',rounded=True)
        _checked_text(s,c['stage'],.61,.94,4.45,.24,10.7,'royal',True,label='stage')
        ts=21.0 if _cell_len(c['title'])<29 else 18.3
        _checked_text(s,c['title'],.50,1.28,6.48,.75,ts,'navy',True,label=f'card{num}_title')
        _checked_text(s,c['intro'],.51,2.08,6.45,.43,11.2,'muted',label=f'card{num}_intro')
        indices=[claims[q] for q in c['claim_ids']]
        metrics=[m for cl in indices for m in cl.get('metrics',[])]
        limits=list(dict.fromkeys(cl['limit'] for cl in indices if cl.get('limit')))
        if len(metrics)>3:raise ContractError(f'LAYOUT_METRICS_CAPACITY_EXCEEDED:CARD_{num}:count_{len(metrics)}')
        if _cell_len('；'.join(limits))>92:raise ContractError(f'LAYOUT_LIMITS_CAPACITY_EXCEEDED:CARD_{num}')
        question=c.get('question') or indices[0]['question']
        if role in ('cover','framework','synthesis'):
            # A real conceptual framework gets most of the vertical real estate.
            _labelled_row(s,'核心问题',question,2.57,.60,'light',10.4)
            visual_y,visual_h=3.27,(3.03 if metrics else 3.11)
            fig_records=_place_visual(s,c,aa,root,visual_y,visual_h,num)
            _labelled_row(s,'研究怎么推进',c['method'],visual_y+visual_h+.10,.52,'white',10.1)
            y=visual_y+visual_h+.70
        else:
            # Evidence-oriented cards put methods and question side-by-side and allocate
            # more space to the actual registered Figure panels.
            rect(s,.51,2.59,3.16,.83,'light','border',True)
            rect(s,3.81,2.59,3.18,.83,'white','border',True)
            _checked_text(s,'研究问题',.66,2.67,2.79,.21,10.1,'royal',True,label='q_title')
            _checked_text(s,question,.66,2.91,2.85,.42,9.75,'navy',label=f'card{num}_question')
            _checked_text(s,'作者怎么做',3.97,2.67,2.83,.21,10.1,'royal',True,label='m_title')
            _checked_text(s,c['method'],3.97,2.91,2.84,.42,9.6,'navy',label=f'card{num}_method')
            visual_y=3.55;visual_h=3.20 if len(metrics)<2 else 2.67
            fig_records=_place_visual(s,c,aa,root,visual_y,visual_h,num)
            y=visual_y+visual_h+.11
        end=_bottom_explanation(s,c,claims,y,metrics,limits,num)
        rect(s,.48,9.27,6.52,.013,'border')
        paper=story['paper'];footer=f"{paper['authors_short']} | {paper.get('journal','')} | DOI: {paper['doi']}"
        _checked_text(s,footer,.48,9.36,6.44,.24,8.9,'muted',label='citation')
        _checked_text(s,'SharePack · Independent journal-inspired design, not publisher affiliated',.48,9.63,6.43,.24,8.1,'royal',label='github')
        geometry.append({'card':num,'layout_type':role,'evidence_figure_slots':fig_records,
                         'visible_metric_count':len(metrics),'visible_limit_count':len(limits),
                         'content_end':round(end,3),
                         'small_panel_flag':any(x['draw_height_in']<1.30 for x in fig_records)})
    return prs,geometry

def build(story_path,asset_path,outdir, *, profile=None, render_png=True, layout_engine='freeform', pdf_index_path=None, logo_manifest_path=None):
    story_path=Path(story_path).resolve();asset_path=Path(asset_path).resolve();root=asset_path.parent
    outdir=Path(outdir).resolve();story=load(story_path);assets=load(asset_path)
    qa=validate_story(story,assets,root,profile=profile)
    # PDF-index metadata is a visual style hint, not scientific review.
    index_path=Path(pdf_index_path).resolve() if pdf_index_path else None
    hint=None
    if index_path:
        index=load(index_path)
        if index.get('pdf_sha256')!=story.get('pdf_sha256'):
            raise ContractError('PUBLICATION_INDEX_PDF_HASH_MISMATCH')
        hint=index.get('publication_hint')
    paper_for_style=dict(story.get('paper',{}))
    if hint and not paper_for_style.get('source_type') and not paper_for_style.get('journal'):
        paper_for_style['publication_hint']=hint
    publication_style=select_style(paper_for_style)
    publication_logo=check_logo(logo_manifest_path,publication_style,story.get('paper',{}))
    if outdir==root or outdir==story_path.parent:raise ContractError('OUTPUT_SAME_AS_INPUT')
    outdir.mkdir(parents=True,exist_ok=True)
    pptpath=outdir/'SharePack_editable.pptx'
    if pptpath.exists():raise ContractError('OUTPUT_ALREADY_EXISTS_USE_NEW_DIRECTORY')
    with active_style(publication_style), active_logo(publication_logo):
        if layout_engine=='legacy':
            deck,geometry=slides(story,assets,root)
        elif layout_engine=='freeform':
            from .freeform import slides_freeform
            deck,geometry=slides_freeform(story,assets,root)
        elif layout_engine=='editorial':
            from .editorial import slides_editorial
            deck,geometry=slides_editorial(story,assets,root)
        else:raise ContractError('LAYOUT_ENGINE_UNKNOWN')
    deck.save(pptpath)
    reports={'story_sha256':digest(story_path),'assets_sha256':digest(asset_path),
     'publication_style':publication_style.to_dict(),
     'publication_logo':publication_logo.report() if publication_logo else {'status':'NOT_EMBEDDED_NO_VERIFIED_PERMISSION'},
     'publication_index_sha256':digest(index_path) if index_path else None,
     'pptx_sha256':digest(pptpath),'pfs_needed':bool(story.get('pfs_bridge')),
     'layout_engine':layout_engine,'layout_geometry':geometry, 'panel_selection_audit':panel_selection_audit(story,assets),'scientific_status':'PARTIAL' if not qa['formal_ready'] else 'REVIEWED_SOURCE_ONLY',
     'contract_qa':qa,'original_figure_assets_used':sum(len(c.get('figure_asset_ids',[])) for c in story['cards'])}
    if render_png:
        with tempfile.TemporaryDirectory(prefix='sharepack_lo_') as ld:
            res=subprocess.run(['libreoffice',f'-env:UserInstallation=file://{ld}/lo','--headless','--convert-to','pdf',
                        '--outdir',str(outdir),str(pptpath)],capture_output=True,text=True,timeout=140)
        pdf=outdir/'SharePack_editable.pdf'
        if res.returncode!=0 or not pdf.exists():raise RuntimeError('LIBREOFFICE_EXPORT_FAILED:'+res.stderr)
        doc=fitz.open(pdf)
        if len(doc)!=len(story['cards']):raise RuntimeError('PDF_PAGE_COUNT_MISMATCH')
        carddir=outdir/'cards';carddir.mkdir(exist_ok=True);files=[]
        for i,page in enumerate(doc,1):
            name=carddir/f'{i:02d}_card.png'
            page.get_pixmap(matrix=fitz.Matrix(1080/page.rect.width,1440/page.rect.height),alpha=False).save(name)
            files.append(name)
        totalw=3*324;totalh=((len(files)+2)//3)*456
        sheet=Image.new('RGB',(totalw,totalh),(237,243,247))
        for i,f in enumerate(files):
            with Image.open(f) as p:im=p.copy()
            im.thumbnail((300,420))
            sheet.paste(im,((i%3)*324+(324-im.width)//2,(i//3)*456+10))
        sheet.save(outdir/'00_contact_sheet.png')
        reports.update({'pdf_sha256':digest(pdf),'png_count':len(files),
                        'png_sha256':{f.name:digest(f) for f in files}})
    # Per-card provenance stays separate from the reader-facing slides.
    by_claim={c['id']:c for c in story['claims']};by_asset={a['id']:a for a in assets['assets']}
    bindings=[]
    for card in story['cards']:
        bindings.append({'card':card['order'],'title':card['title'],
          'claims':[{'id':cid,'source_ids':by_claim[cid]['source_ids'],
                     'pfs_rsu_ids':by_claim[cid].get('pfs_rsu_ids',[]),
                     'pfs_relation_ids':by_claim[cid].get('pfs_relation_ids',[])} for cid in card['claim_ids']],
          'figures':[{k:by_asset[aid].get(k) for k in ('id','figure','pdf_page','crop_pdf_pt','sha256','source_pdf_sha256')}
                     for aid in card.get('figure_asset_ids',[])]})
    save(outdir/'card_source_map.json',{'pdf_sha256':assets['source_pdf_sha256'],
       'story_sha256':digest(story_path),'bridge':story.get('pfs_bridge'), 'cards':bindings})
    # Static shape audit: boundary checks and declared typeface names. Does not replace visual inspection.
    deck2=Presentation(pptpath);overflow=[]
    for i,s in enumerate(deck2.slides,1):
        for j,sh in enumerate(s.shapes):
            if sh.left < -500 or sh.top< -500 or sh.left+sh.width>deck2.slide_width+500 or sh.top+sh.height>deck2.slide_height+500:
                overflow.append([i,j,sh.name])
    # A second, object-level check catches textual boxes colliding under free layout.
    # It is not a substitute for font-aware visual inspection in PowerPoint.
    text_collisions=[]
    for i,slide in enumerate(deck2.slides,1):
        boxes=[(j,sh) for j,sh in enumerate(slide.shapes)
               if sh.has_text_frame and sh.text.strip()]
        for k,(a,sa) in enumerate(boxes):
            for b,sb in boxes[k+1:]:
                xover=min(sa.left+sa.width,sb.left+sb.width)-max(sa.left,sb.left)
                yover=min(sa.top+sa.height,sb.top+sb.height)-max(sa.top,sb.top)
                if xover>Inches(.03) and yover>Inches(.03):
                    text_collisions.append({'page':i,'shape_a':a,'shape_b':b})
    # Static mobile-font check. At a 400px-wide portrait card, one PowerPoint
    # point occupies about 0.74 rendered pixels. This is only a warning; actual
    # rasterized text must still be inspected (font fallback can change metrics).
    mobile_type_warnings=[]
    for page_i,slide in enumerate(deck2.slides,1):
        for shape_i,shape in enumerate(slide.shapes):
            if not shape.has_text_frame or not shape.text.strip():
                continue
            for paragraph in shape.text_frame.paragraphs:
                for run in paragraph.runs:
                    if not run.text.strip() or run.font.size is None:
                        continue
                    pt=run.font.size.pt
                    approx_px=round(pt*400/(7.5*72),1)
                    if approx_px<12.0:
                        mobile_type_warnings.append({'page':page_i,'shape':shape_i,
                            'font_pt':round(pt,2),'approx_px_at_400w':approx_px,
                            'sample':run.text[:28]})
    with zipfile.ZipFile(pptpath) as z:
        xml=''.join(z.read(p).decode('utf-8') for p in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml',p))
    small_slots=[{'card':g['card'],'asset_id':slot['asset_id'],'draw_height_in':slot['draw_height_in']}
                 for g in geometry for slot in g['evidence_figure_slots'] if slot['draw_height_in']<1.30]
    reports['static_visual_qa']={'canvas_overflow':overflow,'simhei_declared':'SimHei' in xml,
       'tnr_declared':'Times New Roman' in xml,
       'expected_cjk_font':publication_style.cjk_font,
       'expected_latin_font':publication_style.latin_font,'small_panel_slots':small_slots,
       'text_text_collisions':text_collisions,
       'mobile_type_warnings':mobile_type_warnings,
       'min_accepted_approx_type_px_at_400w':12.0,
       'layout_status':'PARTIAL_REQUIRES_REDISTRIBUTION' if small_slots or overflow or text_collisions else 'STRUCTURAL_PASS',
       'real_office_review':'PENDING','mobile_visual_review':'PENDING'}
    # A machine shape check cannot confer human scientific or mobile acceptance.
    reports['release_ready']=False
    reports['release_blockers']=['SCIENCE_AND_WINDOWS_VISUAL_REVIEW_NOT_PERFORMED']
    if small_slots:reports['release_blockers'].append('MOBILE_FIGURE_TOO_SMALL')
    if text_collisions:reports['release_blockers'].append('TEXT_OVERLAP')
    if mobile_type_warnings:reports['release_blockers'].append('MOBILE_TEXT_TOO_SMALL')
    if reports['panel_selection_audit']['pending']:
        reports['release_blockers'].append('PANEL_SELECTION_NOT_REVIEWED')
    if layout_engine=='freeform':
        # Machine-auditable composition; no new scientific claims are inferred.
        save(outdir/'composition_plan.json',{
          'contract':'sharepack-freeform-composition-v1',
          'origin':'AGENT_REVIEWED_STORY_AND_REGISTERED_FIGURES',
          'story_sha256':reports['story_sha256'],'assets_sha256':reports['assets_sha256'],
          'cards':[{'card':g['card'],'composition':g['layout_type'],
                    'source_figure_ids':[e['asset_id'] for e in g['evidence_figure_slots']],
                    'source_metrics_visible':g['visible_metric_count'],
                    'source_limits_visible':g['visible_limit_count'],
                    'content_end':g['content_end'],
                    'mobile_review_required':g.get('mobile_review_required',False)} for g in geometry],
          'science_review':'NOT_PERFORMED_BY_LAYOUT_ENGINE',
          'visual_review':'REQUIRES_HUMAN_OR_OFFICE_INSPECTION'})
    save(outdir/'publication_style.json',publication_style.to_dict())
    save(outdir/'publication_logo.json',reports['publication_logo'])
    save(outdir/'qa_report.json',reports)
    return reports
