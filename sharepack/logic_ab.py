"""Direct PFS v1.1.1 Research Logic A/B projector, not a M1 relationship proxy.

Reads the official `pfs-research-logic-1` model and preserves source_logic_node_ids
and source_logic_relation_ids. No extra arrows, no synthetic experimental order.
"""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from .common import ContractError,load,save,digest
from .logic_projection import VERSION,EDGE_STYLE

AB_VERSION='pfs-research-logic-1'
PFS_EDGE_STYLE={
 'progression':('研究推进（非因果）','447e9f',True,True),
 'question_fork':('问题分支（非因果）','447e9f',True,True),
 'parallel':('并行研究','7c79bd',True,False),
 'complements':('相互补充','2d866b',True,False),
 'evidence_convergence':('证据汇合','2d866b',False,True),
 'shared_workflow':('共用流程','64748b',True,False),
 'hypothesizes':('机制假说','b57c43',True,False),
 'comparison':('比较','7c79bd',True,False),
 'protocol_order':('已证实执行顺序','8c6b2f',False,True),
 'qualifies':('限定','b57c43',True,False),
}

def pfs_model_snapshot(m):
    return hashlib.sha256(json.dumps({k:v for k,v in m.items() if k!='snapshot'},sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()

def _ab_model(path):
    path=Path(path).resolve();m=load(path)
    if m.get('version')!=AB_VERSION:raise ContractError('PFS_AB_VERSION_UNSUPPORTED')
    if m.get('snapshot')!=pfs_model_snapshot(m):raise ContractError('PFS_AB_LOGIC_SNAPSHOT_DRIFT')
    if m.get('formal_ready') is not False:raise ContractError('PFS_AB_FORMAL_STATUS_UNEXPECTED')
    # Verify the official A/B model's upstream scientific evidence and index files,
    # not just the model's self-reported snapshot.
    refs=m.get('inputs',{})
    if not isinstance(refs,dict) or not {'network','scientific_index'}<=set(refs):
        raise ContractError('PFS_AB_REQUIRED_SOURCE_INPUTS_MISSING')
    for name,ref in refs.items():
        original=Path(str(ref.get('path','')))
        if not original.is_absolute():original=(path.parent/original).resolve()
        if not original.is_file():raise ContractError('PFS_AB_INPUT_UNAVAILABLE:'+name)
        if digest(original)!=ref.get('sha256'):raise ContractError('PFS_AB_INPUT_SHA_DRIFT:'+name)
        if name=='network' and m.get('network_snapshot'):
            n=load(original)
            if n.get('snapshot')!=m['network_snapshot']:
                raise ContractError('PFS_AB_NETWORK_SNAPSHOT_DRIFT')
    nm={x['id']:x for x in m.get('nodes',[])}
    em={x['id']:x for x in m.get('edges',[])}
    if len(nm)!=len(m.get('nodes',[])) or len(em)!=len(m.get('edges',[])):
        raise ContractError('PFS_AB_DUPLICATE_IDS')
    for e in em.values():
        if e.get('type') not in PFS_EDGE_STYLE:raise ContractError('PFS_AB_RELATION_UNSUPPORTED:'+str(e.get('type')))
        if e.get('from') not in nm or e.get('to') not in nm or e.get('from')==e.get('to'):
            raise ContractError('PFS_AB_RELATION_ENDPOINT_INVALID:'+e['id'])
        if e.get('causal_claim') is True:raise ContractError('PFS_AB_UNSUPPORTED_CAUSAL_CLAIM')
        if e.get('type')=='protocol_order' and (e.get('identity')!='ACTUAL_PROTOCOL_ORDER' or not e.get('registered_relation_id')):
            raise ContractError('PFS_AB_UNVERIFIED_PROTOCOL_ORDER')
    core=m.get('core',{})
    if not core.get('nodes') or not core.get('edges') or not set(core['nodes'])<=set(nm) or not set(core['edges'])<=set(em):
        raise ContractError('PFS_AB_INVALID_CORE')
    return path,m,nm,em

def project_ab(ab_path,spec_path,out_path):
    path,m,nm,em=_ab_model(ab_path)
    spec=load(spec_path)
    if spec.get('contract')!='sharepack-pfs-ab-view-v1':raise ContractError('PFS_AB_VIEW_CONTRACT_INVALID')
    if spec.get('logic_sha256')!=digest(path):raise ContractError('PFS_AB_VIEW_SOURCE_SHA_MISMATCH')
    views=[]
    for v in spec.get('views',[]):
        scope=v.get('scope')
        if scope not in ('A','A_excerpt','B_excerpt','branch'):raise ContractError('PFS_AB_UNKNOWN_VIEW_SCOPE')
        nodes=v.get('nodes',[]);reids=v.get('edge_ids',[])
        ids=[n.get('logic_node_id') for n in nodes]
        if not 2<=len(nodes)<=15 or len(ids)!=len(set(ids)) or not set(ids)<=set(nm):
            raise ContractError('PFS_AB_VIEW_NODE_INVALID')
        if len(reids)!=len(set(reids)) or not reids or not set(reids)<=set(em):
            raise ContractError('PFS_AB_VIEW_EDGE_INVALID')
        if scope=='A' and (set(ids)!=set(m['core']['nodes']) or set(reids)!=set(m['core']['edges'])):
            raise ContractError('PFS_AB_CORE_EDGE_OR_NODE_OMITTED')
        if scope=='A_excerpt' and (not set(ids)<=set(m['core']['nodes']) or not set(reids)<=set(m['core']['edges'])):
            raise ContractError('PFS_AB_CORE_EXCERPT_HAS_NONCORE_IDS')
        if scope=='B_excerpt' and not set(reids)<=set(e['id'] for e in m['edges']):
            raise ContractError('PFS_AB_B_EDGE_UNKNOWN')
        if scope=='branch':
            b=next((b for b in m.get('branches',[]) if b['id']==v.get('branch_id')),None)
            if not b or not set(ids)<=set(b['nodes']) or not set(reids)<=set(b['edges']):
                raise ContractError('PFS_AB_BRANCH_MISMATCH')
        outnodes=[]
        for ref in nodes:
            source=nm[ref['logic_node_id']]
            text=ref.get('display') or source.get('short_text') or source.get('title')
            if not text:raise ContractError('PFS_AB_NODE_TEXT_MISSING:'+source['id'])
            if len(text)>55:raise ContractError('PFS_AB_DISPLAY_TOO_LONG:'+source['id'])
            orig=source.get('short_text') or source.get('title')
            if text!=orig and ref.get('paraphrase_review') not in ('PENDING','APPROVED'):
                raise ContractError('PFS_AB_PARAPHRASE_REVIEW_REQUIRED')
            if not isinstance(ref.get('layer'),int) or not 0<=ref['layer']<=7:
                raise ContractError('PFS_AB_LAYOUT_LAYER_REQUIRED')
            if not isinstance(ref.get('lane'),int) or not 0<=ref['lane']<=7:
                raise ContractError('PFS_AB_LAYOUT_LANE_REQUIRED')
            outnodes.append({'entity_id':source['id'],'logic_node_id':source['id'],
                'text':text,'source_text':orig,'layer':ref['layer'],'lane':ref['lane'],
                'identity':source.get('identity'),'source_ids':source.get('source_ids',[]),
                'paraphrased':text!=orig,'paraphrase_review':ref.get('paraphrase_review','SOURCE_EXACT')})
        outputedges=[]
        for rid in reids:
            r=em[rid]
            if {r['from'],r['to']}-set(ids):raise ContractError('PFS_AB_EDGE_ENDPOINT_NOT_SHOWN:'+rid)
            outputedges.append({'relation_id':rid,'source':r['from'],'target':r['to'],
                'type':r['type'],'identity':r.get('identity'),'source_ids':r.get('source_ids',[]),
                'label':PFS_EDGE_STYLE[r['type']][0], 'is_biological_causal':False})
        counts={}
        for x in outnodes:counts[x['layer']]=counts.get(x['layer'],0)+1
        if max(counts.values())>4 or len(counts)>6:raise ContractError('PFS_AB_VIEW_TOO_DENSE_SPLIT_REQUIRED')
        views.append({'id':v['id'],'scope':scope,'title':v['title'],'question':v['question'],
            'note':v.get('note',''), 'nodes':outnodes,'edges':outputedges,
            'registered_entity_count':len(outnodes),'registered_relation_count':len(outputedges),
            'review_status':'PENDING'})
    if not views:raise ContractError('PFS_AB_VIEWS_EMPTY')
    all_core_views=[v for v in views if v['scope'] in ('A','A_excerpt')]
    if not all_core_views:raise ContractError('PFS_AB_CORE_VIEW_REQUIRED')
    full_nodes=set().union(*(set(n['entity_id'] for n in v['nodes']) for v in all_core_views))
    full_edges=set().union(*(set(r['relation_id'] for r in v['edges']) for v in all_core_views))
    if full_nodes!=set(m['core']['nodes']) or full_edges!=set(m['core']['edges']):
        raise ContractError('PFS_AB_CORE_COVERAGE_INCOMPLETE')
    result={'contract':VERSION,'source_kind':'PFS_AB_RESEARCH_LOGIC_1',
      'knowledge_path':str(path),'knowledge_sha256':digest(path),
      'pfs_ab_snapshot':m['snapshot'],
      'view_spec_path':str(Path(spec_path).resolve()),'view_spec_sha256':digest(spec_path),
      'semantic_note':'A is EXACT official core, B excerpts are registered edge subsets. Display arrows preserve source logic edge identity, never imply additional causality.',
      'views':views,'formal_ready':False}
    save(out_path,result)
    return result

def verify_ab_projection(o):
    _,m,nm,em=_ab_model(o['knowledge_path'])
    if m['snapshot']!=o.get('pfs_ab_snapshot'):raise ContractError('PFS_AB_SOURCE_LOGIC_DRIFT')
    all_core_views=[v for v in o['views'] if v.get('scope') in ('A','A_excerpt')]
    if set().union(*(set(n['entity_id'] for n in v['nodes']) for v in all_core_views))!=set(m['core']['nodes']):
        raise ContractError('PFS_AB_CORE_NODES_NOT_PRESERVED')
    if set().union(*(set(r['relation_id'] for r in v['edges']) for v in all_core_views))!=set(m['core']['edges']):
        raise ContractError('PFS_AB_CORE_EDGES_NOT_PRESERVED')
    for v in o['views']:
        refs={n['entity_id'] for n in v['nodes']}
        er={x['relation_id'] for x in v['edges']}
        if v.get('scope')=='A' and (refs!=set(m['core']['nodes']) or er!=set(m['core']['edges'])):
            raise ContractError('PFS_AB_CORE_NOT_PRESERVED')
        for r in v['edges']:
            original=em.get(r['relation_id'])
            if not original or (original.get('from'),original.get('to'),original.get('type'))!=(r['source'],r['target'],r['type']):
                raise ContractError('PFS_AB_RELATION_BINDING_DRIFT')
    return True
