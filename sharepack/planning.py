"""Non-generative story coverage auditor. Planning decisions belong to a reviewing Agent.

This module NEVER invents scientific edges, metric definitions or filler cards.
"""
from collections import Counter
from .common import ContractError

ROLES={'cover','background','framework','method','finding','comparison','synthesis','limits'}
LAYOUTS={'cover','framework','evidence','comparison','synthesis','method'}

def plan_audit(story,assets):
    cards=story.get('cards',[])
    claims={c['id']:c for c in story.get('claims',[])}
    aa={a['id']:a for a in assets.get('assets',[])}
    roles=Counter(); warnings=[]; records=[]
    for c in cards:
        role=c.get('narrative_role')
        if role not in ROLES:
            warnings.append(f'NARRATIVE_ROLE_NOT_DECLARED:{c.get("order")}')
        else:roles[role]+=1
        layout=c.get('layout_type')
        if layout not in LAYOUTS:
            warnings.append(f'LAYOUT_TYPE_UNDECLARED:{c.get("order")}')
        ids=c.get('figure_asset_ids',[])
        for aid in ids:
            if aid in aa:
                a=aa[aid]
                if a.get('evidence_role')=='UNBOUND_FIGURE_REQUIRES_REVIEW':
                    warnings.append(f'AUTHOR_MODEL_OR_UNBOUND_FIGURE_REQUIRES_REVIEW:{aid}')
                if not a.get('panel_labels') and a.get('pfs_asset_id'):
                    warnings.append(f'PFS_FULL_FIGURE_PANEL_READABILITY_REVIEW:{aid}')
        records.append({'order':c.get('order'),'role':role,'layout':layout,
            'claim_ids':c.get('claim_ids',[]),'figure_asset_ids':ids,
            'required_metrics':sum(len(claims[q].get('metrics',[])) for q in c.get('claim_ids',[]) if q in claims)})
    required_groups=[('background',{'cover','background'}),('research_navigation',{'framework'}),
                     ('findings',{'finding'}),('synthesis_and_limits',{'synthesis','limits'})]
    for name,accept in required_groups:
        if not any(roles[r] for r in accept):warnings.append('STORY_COVERAGE_UNPROVEN:'+name)
    required={x['id'] for x in claims.values() if x.get('required')}
    covered={q for c in cards for q in c.get('claim_ids',[])}
    total=sum(x['required_metrics'] for x in records)
    return {'contract':'sharepack-story-plan-audit-v1','science_created':False,
        'status':'REQUIRES_AGENT_STORY_REVIEW' if warnings else 'STRUCTURALLY_REVIEWABLE',
        'card_count':len(cards),'profile':story.get('profile'),'roles':dict(roles),
        'required_claims':len(required),'uncovered_required_claims':sorted(required-covered),
        'total_required_metrics':total,'warnings':sorted(set(warnings)),'cards':records,
        'notice':'No new scientific facts or cards were inferred. This is not a scientific approval.'}

def panel_selection_audit(story,assets):
    """Machine-verifiable checklist, NOT an automatic image/panel reviewer."""
    index={a['id']:a for a in assets.get('assets',[])}
    records=[];missing=[]
    for c in story.get('cards',[]):
        selections={s.get('asset_id'):s for s in c.get('figure_selections',[]) if isinstance(s,dict)}
        for aid in c.get('figure_asset_ids',[]):
            a=index.get(aid);choice=selections.get(aid,{})
            reviewed=bool(choice.get('reason') and choice.get('panel_labels') and
                          a and a.get('review_status')=='VISUAL_REVIEWED' and
                          choice.get('scientific_check')=='PASS')
            rec={'card':c.get('order'),'asset_id':aid,'figure':a.get('figure') if a else None,
                'source_pdf_page':a.get('pdf_page') if a else None,
                'source_pdf_sha256':a.get('source_pdf_sha256') if a else None,
                'asset_sha256':a.get('sha256') if a else None,
                'crop_pdf_pt':a.get('crop_pdf_pt') if a else None,
                'pfs_asset_id':a.get('pfs_asset_id') if a else None,
                'pfs_evidence_role':a.get('evidence_role') if a else None,
                'author_selection_reason':choice.get('reason'),
                'panel_labels':choice.get('panel_labels') or a.get('panel_labels',[]) if a else [],
                'visual_and_science_review':'PASS' if reviewed else 'PENDING'}
            if not reviewed:missing.append({'card':c.get('order'),'asset_id':aid,'reason':'PANEL_SELECTION_OR_REVIEW_INCOMPLETE'})
            records.append(rec)
    return {'contract':'sharepack-panel-audit-v1','status':'PENDING' if missing else 'REGISTERED_REVIEWED',
        'records':records,'pending':missing,'notice':'Does not infer crop positions, panel identity, or scientific validity.'}
