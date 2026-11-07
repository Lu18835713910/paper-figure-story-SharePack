"""PFS v1.1 research-logic -> editable, evidence-bound PowerPoint diagrams.

Never invent a PFS relationship. A view selects *existing* entity and relation IDs;
'layer' / 'lane' represent visual placement, NEVER experiment time or causality.
Source SHA and all ID bindings are rechecked at time of export.
"""
from __future__ import annotations
import json, math
from pathlib import Path
from .common import ContractError, load, save, digest
from .pfs_adapter import _load_pfs

VERSION='sharepack-pfs-logic-projection-v1'
# Labels describe the registered evidence relation, not inferred biological causality.
EDGE_STYLE={
 'data_depends_on':('依赖','64748b',False,True),
 'experimental_precedes':('实验证实顺序','9d6c26',False,True),
 'parallel_branch':('并行','7c79bd',True,False),
 'independent_validation':('独立验证','2d866b',False,True),
 'evidence_supports':('证据支持','2d866b',False,True),
 'compares':('比较','7c79bd',True,False),
 'argument_transition':('讲述衔接','447e9f',True,False),
 'optional_path':('可选分支','64748b',True,False),
 'integrates':('综合','2d866b',False,True),
}

def _entity_text(e):
    for key in ('name','label','title','text','description','details','statement','summary'):
        s=e.get(key)
        if isinstance(s,str) and s.strip():return s.strip()
    return e['id']

def _as_dict_records(seq):
    return {x['id']:x for x in seq}

def project(knowledge_path, spec_path, output_path):
    kp,model,ver,_=_load_pfs(knowledge_path)
    original=load(spec_path)
    if original.get('contract')!='sharepack-pfs-logic-view-v1':
        raise ContractError('PFS_LOGIC_VIEW_CONTRACT_INVALID')
    if original.get('knowledge_sha256')!=digest(kp):
        raise ContractError('PFS_LOGIC_VIEW_SOURCE_DRIFT')
    nodes_by_id=_as_dict_records(model['entities'])
    relations=_as_dict_records(model['relations'])
    views=[]
    for view in original.get('views',[]):
        if not view.get('id') or not view.get('title') or not view.get('question'):
            raise ContractError('PFS_LOGIC_VIEW_FIELDS_REQUIRED')
        ref_nodes=view.get('nodes',[]);ref_edges=view.get('relation_ids',[])
        if not 2<=len(ref_nodes)<=15:
            raise ContractError('PFS_LOGIC_VIEW_NODE_CAPACITY')
        if not ref_edges:
            raise ContractError('PFS_LOGIC_VIEW_NO_REGISTERED_RELATIONS')
        if len(ref_edges)!=len(set(ref_edges)):
            raise ContractError('PFS_LOGIC_RELATION_DUPLICATED')
        used=[];selected={}
        for item in ref_nodes:
            eid=item.get('entity_id')
            if eid not in nodes_by_id: raise ContractError('PFS_LOGIC_NODE_UNKNOWN:'+str(eid))
            if eid in selected:raise ContractError('PFS_LOGIC_NODE_DUPLICATE:'+eid)
            layer=item.get('layer')
            if not isinstance(layer,int) or layer<0 or layer>7:
                raise ContractError('PFS_LOGIC_LAYER_MUST_BE_EXPLICIT:'+eid)
            lane=item.get('lane',0)
            if not isinstance(lane,int) or lane<0 or lane>7:
                raise ContractError('PFS_LOGIC_LANE_MUST_BE_EXPLICIT:'+eid)
            ent=nodes_by_id[eid]
            # Edited display text is explicitly differentiated from the source label.
            source_text=_entity_text(ent)
            display=item.get('display') or source_text
            if not isinstance(display,str) or not display.strip():
                raise ContractError('PFS_LOGIC_EMPTY_DISPLAY:'+eid)
            if len(display)>55:raise ContractError('PFS_LOGIC_LABEL_TOO_LONG:'+eid)
            if display!=source_text and item.get('paraphrase_review') not in ('PENDING','APPROVED'):
                raise ContractError('PFS_LOGIC_PARAPHRASE_REVIEW_REQUIRED:'+eid)
            n={'entity_id':eid,'text':display,'source_text':source_text,
               'kind':ent.get('kind'),'layer':layer,'lane':lane,
               'paraphrased':display!=source_text,
               'paraphrase_review':item.get('paraphrase_review') if display!=source_text else 'SOURCE_EXACT'}
            used.append(n);selected[eid]=n
        edges=[]
        for rid in ref_edges:
            if rid not in relations:raise ContractError('PFS_LOGIC_RELATION_UNKNOWN:'+rid)
            r=relations[rid];src=r.get('from');dst=r.get('to')
            if src not in selected or dst not in selected:
                raise ContractError('PFS_LOGIC_EDGE_END_MISSING:'+rid)
            rtype=r.get('type')
            if rtype not in EDGE_STYLE:raise ContractError('PFS_LOGIC_EDGE_TYPE_UNKNOWN:'+str(rtype))
            if rtype=='experimental_precedes' and not (r.get('certainty')=='paper_reported' and r.get('order_basis')):
                raise ContractError('PFS_LOGIC_CHRONOLOGY_UNVERIFIED:'+rid)
            edges.append({'relation_id':rid,'source':src,'target':dst,'type':rtype,
                'certainty':r.get('certainty'),'provenance':r.get('provenance'),
                'label':EDGE_STYLE[rtype][0], 'is_biological_causal':False})
        # Strictly refuse graph decoration as scientific links.
        layers={}
        for n in used:layers.setdefault(n['layer'],[]).append(n)
        if max(len(v) for v in layers.values())>4:
            raise ContractError('PFS_LOGIC_LAYER_CAPACITY_EXCEEDED')
        if len(layers)>6:
            raise ContractError('PFS_LOGIC_DEPTH_CAPACITY_EXCEEDED')
        views.append({'id':view['id'],'title':view['title'],'question':view['question'],
            'note':view.get('note',''), 'nodes':used,'edges':edges,
            'registered_entity_count':len(used),'registered_relation_count':len(edges),
            'review_status':'PENDING' if any(n['paraphrase_review']=='PENDING' for n in used) else 'SOURCE_BOUND_NOT_SCIENCE_APPROVED'})
    if not views:raise ContractError('PFS_LOGIC_NO_VIEWS')
    result={'contract':VERSION,'pfs_schema_version':ver,
      'knowledge_path':str(kp),'knowledge_sha256':digest(kp),
      'view_spec_path':str(Path(spec_path).resolve()),'view_spec_sha256':digest(spec_path),
      'semantic_note':'Only the original registered PFS relation IDs are drawn. Diagram order is presentation, not scientific temporal or causal order.',
      'views':views,'formal_ready':False}
    if digest(kp)!=result['knowledge_sha256']:raise ContractError('PFS_LOGIC_SOURCE_CHANGED')
    save(output_path,result)
    return result

def verify_projection(path):
    o=load(path)
    if o.get('contract')!=VERSION:raise ContractError('PFS_LOGIC_PROJECTION_VERSION')
    knowledge=Path(o.get('knowledge_path',''))
    if not knowledge.is_file() or digest(knowledge)!=o.get('knowledge_sha256'):
        raise ContractError('PFS_LOGIC_UPSTREAM_DRIFT')
    spec=Path(o.get('view_spec_path',''))
    if not spec.is_file() or digest(spec)!=o.get('view_spec_sha256'):
        raise ContractError('PFS_LOGIC_VIEW_SPEC_DRIFT')
    if o.get('source_kind')=='PFS_AB_RESEARCH_LOGIC_1':
        from .logic_ab import verify_ab_projection
        verify_ab_projection(o)
        return o
    kp,model,_,_=_load_pfs(knowledge)
    originals=_as_dict_records(model['relations'])
    for v in o['views']:
        names={n['entity_id'] for n in v['nodes']}
        for r in v['edges']:
            raw=originals.get(r['relation_id'])
            if (not raw or raw.get('from')!=r['source'] or raw.get('to')!=r['target']
                or raw.get('type')!=r['type'] or r['source'] not in names or r['target'] not in names):
                raise ContractError('PFS_LOGIC_RELATION_DRIFT:'+r['relation_id'])
    return o

def render(checked_projection, outdir, *, pdf=True):
    """Slides remain editable PowerPoint vectors (text, shapes, connectors)."""
    from pptx import Presentation
    from pptx.util import Inches,Pt
    from pptx.dml.color import RGBColor
    from pptx.enum.shapes import MSO_SHAPE,MSO_CONNECTOR
    from pptx.enum.text import PP_ALIGN,MSO_ANCHOR
    from pptx.enum.dml import MSO_THEME_COLOR
    from pptx.oxml.xmlchemy import OxmlElement
    from pptx.enum.dml import MSO_LINE_DASH_STYLE
    o=verify_projection(checked_projection)
    out=Path(outdir)
    out.mkdir(parents=True,exist_ok=True)
    prs=Presentation();prs.slide_width=Inches(7.5);prs.slide_height=Inches(10)
    c=lambda s:RGBColor.from_string(s.strip('#').upper())
    def shape_rect(sl,x,y,w,h,fill,stroke='D4E0E9',rad=True):
        s=sl.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if rad else MSO_SHAPE.RECTANGLE,Inches(x),Inches(y),Inches(w),Inches(h))
        s.fill.solid();s.fill.fore_color.rgb=c(fill);s.line.color.rgb=c(stroke);s.line.width=Pt(.8)
        if rad:
            try:s.adjustments[0]=.13
            except Exception:pass
        return s
    def text(sl,t,x,y,w,h,size=13,bold=False,color='18334B',align=PP_ALIGN.LEFT):
        box=sl.shapes.add_textbox(Inches(x),Inches(y),Inches(w),Inches(h));tf=box.text_frame
        tf.word_wrap=True;tf.margin_left=Inches(.03);tf.margin_top=Inches(.015);tf.margin_right=Inches(.02)
        p=tf.paragraphs[0];p.text=t;p.alignment=align
        p.space_before=Pt(0);p.space_after=Pt(0);p.line_spacing=1.05
        for run in p.runs:
            run.font.name='SimHei' if any(ord(ch)>127 for ch in t) else 'Times New Roman'
            run.font.size=Pt(size);run.font.bold=bold;run.font.color.rgb=c(color)
        return box
    def arrow(sl,x1,y1,x2,y2,r):
        from pptx.enum.shapes import MSO_CONNECTOR
        from pptx.enum.dml import MSO_LINE_DASH_STYLE
        from .logic_ab import PFS_EDGE_STYLE
        sty=(PFS_EDGE_STYLE if o.get('source_kind')=='PFS_AB_RESEARCH_LOGIC_1' else EDGE_STYLE)[r['type']]
        p=sl.shapes.add_connector(MSO_CONNECTOR.STRAIGHT,Inches(x1),Inches(y1),Inches(x2),Inches(y2))
        p.line.color.rgb=c(sty[1]);p.line.width=Pt(1.45 if not sty[2] else 1.15)
        if sty[2]:p.line.dash_style=MSO_LINE_DASH_STYLE.DASH
        if sty[3]:
            # OOXML native arrowheads, never for unlabeled presentation or parallel links.
            ln=p.get_or_add_ln()
            fin=OxmlElement('a:tailEnd');fin.set('type','triangle');fin.set('w','sm');fin.set('len','sm')
            ln.append(fin)
        return p
    report=[]
    for index,v in enumerate(o['views'],1):
        sl=prs.slides.add_slide(prs.slide_layouts[6]);shape_rect(sl,0,0,7.5,10,'F9FBFD','F9FBFD',False)
        shape_rect(sl,0,0,7.5,.08,'173B57','173B57',False)
        text(sl,'PFS / RESEARCH LOGIC',.46,.22,5.4,.31,13,True,'25658B')
        text(sl,f'{index:02} / {len(o["views"]):02}',6.16,.23,.91,.30,11,False,'64798A',PP_ALIGN.RIGHT)
        shape_rect(sl,.46,.68,6.55,.012,'CEDCE8','CEDCE8',False)
        text(sl,v['title'],.48,.87,6.44,.80,22,True)
        text(sl,'研究问题：'+v['question'],.48,1.64,6.43,.85,11.7,False,'47677F')
        groups={}
        for n in v['nodes']:groups.setdefault(n['layer'],[]).append(n)
        layers=sorted(groups)
        # Dynamic positions: between 2 and 6 layers, 1-4 nodes per layer.
        ytop=2.65; ybottom=7.93
        rowh=min(1.18, (ybottom-ytop-.24*(len(layers)-1))/len(layers))
        gap=(ybottom-ytop-rowh*len(layers))/(max(1,len(layers)-1))
        positions={}
        for j,layer in enumerate(layers):
            row=sorted(groups[layer],key=lambda n:(n['lane'],n['entity_id']))
            n=len(row);sep=.14; ww=min(4.85,(6.55-(n-1)*sep)/n)
            start=(7.5-(ww*n+sep*(n-1)))/2
            yy=ytop+j*(rowh+gap)
            for k,item in enumerate(row):positions[item['entity_id']]=(start+k*(ww+sep),yy,ww,rowh)
        # Connect only *registered* edges, never auto-add arrow between adjacent boxes.
        for r in v['edges']:
            x,y,w,h=positions[r['source']];tx,ty,tw,th=positions[r['target']]
            if ty>y+h+.12: a=(x+w/2,y+h); b=(tx+tw/2,ty)
            elif ty+h<y-.12: a=(x+w/2,y);b=(tx+tw/2,ty+th)
            else: a=(x+w/2 if x<tx else x, y+h/2);b=(tx if x<tx else tx+tw,ty+th/2)
            arrow(sl,*a,*b,r)
        for n in v['nodes']:
            x,y,w,h=positions[n['entity_id']]
            palette=['F0F6FA','EFF8F3','FFF6E9','F5F3FB']
            shape_rect(sl,x,y,w,h,palette[n['layer']%4], 'D4E0E9')
            text(sl,n['text'],x+.13,y+.17,w-.23,h-.39,12.8 if len(n['text'])<20 else 11.2,True)
            text(sl,n['entity_id'],x+.13,y+h-.29,w-.26,.23,8,False,'5E788C')
        if v['note']:
            text(sl,v['note'],.48,8.10,6.45,.47,10.4,False,'3D627B')
        # Actual relation IDs and review status stay visible, but never fake source approval.
        text(sl,'关系：'+ ' / '.join(f"{r['relation_id']}({r['label']})" for r in v['edges'])[:160],.48,8.69,6.47,.32,7.3,False,'516879')
        shape_rect(sl,.46,9.15,6.55,.012,'D4E0E9','D4E0E9',False)
        text(sl,'PFS 1.1知识关系投影 · 待科学/视觉复核 · SHA '+o['knowledge_sha256'][:12],.48,9.28,6.40,.37,8.2,False,'486C84')
        report.append({'view':v['id'],'node_count':len(v['nodes']),'relation_count':len(v['edges']),
            'node_ids':[n['entity_id'] for n in v['nodes']], 'relation_ids':[r['relation_id'] for r in v['edges']]})
    target=out/'PFS_Logic_Projection_editable.pptx';prs.save(target)
    save(out/'projection_render_report.json',{'contract':VERSION,'knowledge_sha256':o['knowledge_sha256'],
        'rendered_relation_ids':report,'scientific_review':'PENDING','pfs_source_unchanged':digest(o['knowledge_path'])==o['knowledge_sha256']})
    if pdf:
        import subprocess
        q=subprocess.run(['libreoffice','-env:UserInstallation=file:///tmp/lo_sharepack_logic_v5', '--headless', '--convert-to','pdf','--outdir',str(out),str(target)],capture_output=True,text=True,timeout=50)
        if q.returncode!=0:raise ContractError('PFS_LOGIC_PDF_EXPORT_FAILED:'+q.stderr[:200])
        import fitz
        pdf_file=target.with_suffix('.pdf')
        doc=fitz.open(pdf_file)
        for i,page in enumerate(doc,1):
            page.get_pixmap(matrix=fitz.Matrix(1.45,1.45),alpha=False).save(out/f'logic_{i:02d}.png')
    return target,report
