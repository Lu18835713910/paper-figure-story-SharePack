"""One scientific truth per claim. Presentation never upgrades an unchecked claim."""
from pathlib import Path
from PIL import Image
from .common import ContractError,load,digest,within
from .pfs_adapter import verify_bridge_context
from .planning import plan_audit

def validate_story(story,assets,root, profile=None, strict=True):
    e=[]; warnings=[]
    if story.get('contract')!='sharepack-story-v1':e.append('STORY_SCHEMA_UNSUPPORTED')
    if assets.get('contract')!='sharepack-figure-assets-v1':e.append('ASSET_SCHEMA_UNSUPPORTED')
    paper=story.get('paper',{})
    if not all(paper.get(k) for k in ('title','doi','authors_short')):e.append('PAPER_FIELDS_REQUIRED')
    if story.get('pdf_sha256')!=assets.get('source_pdf_sha256'):e.append('PDF_SNAPSHOT_CONFLICT')
    prof=profile or story.get('profile','standard')
    if prof not in ('standard','full'):e.append('PROFILE_UNKNOWN')
    cards=story.get('cards',[]);min_card,max_card=(8,10) if prof=='standard' else (1,15)
    if not min_card<=len(cards)<=max_card:e.append(f'CARD_COUNT_{prof.upper()}_{len(cards)}')
    sources={x['id']:x for x in story.get('sources',[]) if x.get('id')}
    claims={x['id']:x for x in story.get('claims',[]) if x.get('id')}
    aa={x['id']:x for x in assets.get('assets',[]) if x.get('id')}
    if len(sources)!=len(story.get('sources',[])) or len(claims)!=len(story.get('claims',[])) or len(aa)!=len(assets.get('assets',[])):
        e.append('DUPLICATE_OR_EMPTY_IDS')
    for src in sources.values():
        if not isinstance(src.get('pdf_page'),int) or src['pdf_page']<1:e.append('INVALID_SOURCE_PAGE:'+src['id'])
    for c in claims.values():
        for field in ('question','method','observation','meaning','limit'):
            if not str(c.get(field,'')).strip():e.append('MISSING_CLAIM_FIELD:'+c['id']+'/'+field)
        if not c.get('source_ids') or not set(c['source_ids'])<=set(sources):e.append('CLAIM_SOURCE_MISSING:'+c['id'])
        for n in c.get('metrics',[]):
            if not all(n.get(k) for k in ('label','value','definition','comparison')):
                e.append('METRIC_EXPLANATION_MISSING:'+c['id'])
    for a in aa.values():
        try:
            p=within(root,Path(root)/a['path']);Image.open(p).verify()
            if digest(p)!=a.get('sha256'):e.append('ASSET_HASH_DRIFT:'+a['id'])
        except (FileNotFoundError,ValueError,OSError,ContractError):e.append('ASSET_MISSING_OR_INVALID:'+a['id'])
        if a.get('source_pdf_sha256')!=assets.get('source_pdf_sha256'):e.append('ASSET_PDF_HASH_DRIFT:'+a['id'])
        if a.get('review_status')!='VISUAL_REVIEWED':warnings.append('ASSET_REVIEW_PENDING:'+a['id'])
        if a.get('evidence_role')=='UNBOUND_FIGURE_REQUIRES_REVIEW':
            warnings.append('UNBOUND_FIGURE_NOT_SCIENTIFICALLY_REVIEWED:'+a['id'])
    covered=set()
    for i,c in enumerate(cards,1):
        if c.get('order')!=i:e.append('ORDER_NONCONTIGUOUS:'+str(i))
        if not all(c.get(k) for k in ('stage','title','intro','takeaway')):e.append('CARD_TEXT_MISSING:'+str(i))
        if not c.get('claim_ids') or not set(c['claim_ids'])<=set(claims):e.append('CARD_CLAIM_INVALID:'+str(i))
        covered.update(c.get('claim_ids',[]))
        if len(c.get('figure_asset_ids',[]))>2:e.append('TOO_MANY_IMAGES:'+str(i))
        if not set(c.get('figure_asset_ids',[]))<=set(aa):e.append('CARD_ASSET_INVALID:'+str(i))
        for field in ('method','observation','interpretation'):
            if not str(c.get(field,'')).strip():e.append('CARD_EXPLANATION_MISSING:'+str(i)+'/'+field)
    expected_figures=set(story.get('required_figure_labels',[]))
    shown_figures={aa[id]['figure'] for card in cards for id in card.get('figure_asset_ids',[]) if id in aa}
    for fig in sorted(expected_figures-shown_figures):e.append('REQUIRED_FIGURE_OMITTED:'+fig)
    if story.get('paper',{}).get('article_type')=='original_research' and not shown_figures:
        warnings.append('NO_ORIGINAL_FIGURES_INCLUDED')
    pfs=story.get('pfs_bridge')
    if pfs:
        try:
            context_path=Path(pfs['context_path']);context=load(context_path)
            if context.get('contract')!='sharepack-pfs-bridge-v1' or digest(context_path)!=pfs.get('context_sha256'):
                e.append('PFS_BRIDGE_CONTEXT_DRIFT')
            if context.get('knowledge_sha256')!=pfs.get('knowledge_sha256'):
                e.append('PFS_KNOWLEDGE_BINDING_DRIFT')
            # A correctly hashed bridge file is not enough: upstream PFS can change later.
            try:
                verify_bridge_context(context_path)
            except (ContractError, OSError, ValueError) as ex:
                e.append(str(ex))
            primary_hashes={d.get('sha256') for d in context.get('documents',[])
              if d.get('sha256') and ('primary' in str(d.get('role','')).lower() or
              str(d.get('role','')).lower() in ('paper','article','main','main_paper'))}
            if primary_hashes and story.get('pdf_sha256') not in primary_hashes:
                e.append('PFS_PAPER_SOURCE_HASH_MISMATCH')
            allowed_rs={x['rsu_id'] for x in context.get('rsus',[])}
            allowed_rel={x['id'] for x in context.get('relations',[])}
            for cl in claims.values():
                for rid in cl.get('pfs_rsu_ids',[]):
                    if rid not in allowed_rs:e.append('PFS_RSU_REF_UNKNOWN:'+str(rid))
                for rid in cl.get('pfs_relation_ids',[]):
                    if rid not in allowed_rel:e.append('PFS_RELATION_REF_UNKNOWN:'+str(rid))
        except (FileNotFoundError,ValueError,KeyError):e.append('PFS_BRIDGE_CONTEXT_UNAVAILABLE')
    for cid,c in claims.items():
        if c.get('required') and cid not in covered:e.append('REQUIRED_CLAIM_OMITTED:'+cid)
        if c.get('review_status')!='DIRECT_CHECKED':warnings.append('CLAIM_REVIEW_PENDING:'+cid)
    if story.get('review_status')!='REVIEWED':warnings.append('STORY_REVIEW_PENDING')
    # Story-planning audit is kept distinct from the input structural schema.
    # Legacy stories remain valid for diagnostic preview but cannot imply story review.
    planning=plan_audit(story,assets)
    warnings.extend(planning['warnings'])
    valid=not e
    ready=valid and not warnings and story.get('formal_ready') is True
    result={'valid':valid,'formal_ready':ready,'errors':e,'warnings':warnings,'profile':prof,
        'cards':len(cards),'used_claim_ids':sorted(covered),'required_claims':sum(bool(c.get('required')) for c in claims.values()),
        'asset_count':len(aa),'story_plan_audit':planning,'binding':'STORY_AND_ASSETS_SHARED_PDF_SHA'}
    if strict and e:raise ContractError('; '.join(e))
    return result
