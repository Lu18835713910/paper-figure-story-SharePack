#!/usr/bin/env python3
"""Generate a REVIEW-ONLY view spec using official PFS A core and first readable branch.

This is a geometry/ID draft, not scientific selection or review.
Fails on large graphs rather than dropping core edges or fabricating summaries.
"""
from __future__ import annotations
import argparse,sys,json
from pathlib import Path
from sharepack.common import ContractError,digest,save
from sharepack.logic_ab import _ab_model

def tier_layout(ids,edges):
 import networkx as nx
 gr=nx.DiGraph();gr.add_nodes_from(ids)
 for e in edges:
  if e['type'] in {'progression','question_fork','evidence_convergence'}:
   gr.add_edge(e['from'],e['to'])
 if not nx.is_directed_acyclic_graph(gr):
  raise ContractError('PFS_AB_CYCLIC_RESEARCH_ARGUMENT_REQUIRES_EXPLICIT_LAYOUT')
 depth={}
 for node in nx.topological_sort(gr):
  pred=list(gr.predecessors(node))
  depth[node]=(max(depth[x] for x in pred)+1 if pred else 0)
 layers=sorted(set(depth.values()))
 if len(layers)>6:raise ContractError('PFS_AB_TOO_DEEP_FOR_ONE_MOBILE_VIEW_SPLIT_REQUIRED')
 assigned={x:i for i,x in enumerate(layers)}
 per={}
 for node in ids:per.setdefault(assigned[depth[node]],[]).append(node)
 if any(len(v)>4 for v in per.values()):
  raise ContractError('PFS_AB_TOO_WIDE_FOR_ONE_MOBILE_VIEW_SPLIT_REQUIRED')
 return [{'logic_node_id':node,'layer':lay,'lane':i} for lay,lst in sorted(per.items()) for i,node in enumerate(lst)]

def generate(path,out):
 path,m,nm,em=_ab_model(path)
 core=m['core'];nid=list(core['nodes']);eid=list(core['edges'])
 if len(nid)>15:raise ContractError('PFS_AB_CORE_TOO_LARGE_FOR_MOBILE_SPLIT_REQUIRED')
 items=[]
 def item(vid,title,scope,ids,edges,extra=None):
  if len(ids)>15:return
  lay=tier_layout(ids,[em[e] for e in edges])
  o={'id':vid,'scope':scope,'title':title,'question':'请根据原PFS A/B逐项核实本页科研问题',
     'note':'本页为自动布局草案；节点和边ID来自PFS，文字及论证仍待Agent核验。',
     'nodes':lay,'edge_ids':list(edges)}
  if extra:o.update(extra)
  items.append(o)
 item('A','全文科研逻辑｜PFS A核心','A',nid,eid)
 for b in m.get('branches',[])[:2]:
  ids=b.get('nodes',[]);eids=b.get('edges',[])
  if len(ids)>15 or not eids:continue
  item(b['id'],b.get('title','PFS 局部分支'),'branch',ids,eids,{'branch_id':b['id']})
 if not items:raise ContractError('PFS_AB_NO_READABLE_VIEW')
 spec={'contract':'sharepack-pfs-ab-view-v1','logic_sha256':digest(path),'views':items,
       'review_status':'PENDING','no_scientific_semantics_inferred':True}
 return save(out,spec)

def main():
 p=argparse.ArgumentParser();p.add_argument('--research-logic',required=True);p.add_argument('--out',required=True);a=p.parse_args()
 try:
  res=generate(a.research_logic,a.out);print(json.dumps({'draft':str(res),'science_review':'PENDING'},ensure_ascii=False));return 0
 except ContractError as e:print(str(e),file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
