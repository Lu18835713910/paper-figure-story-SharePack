#!/usr/bin/env python3
"""Draft/verify/render editable PFS logic views from original registered relation IDs."""
import argparse,json,sys
from pathlib import Path
from sharepack.logic_projection import project, render,verify_projection
from sharepack.common import ContractError

def main(argv=None):
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--knowledge');p.add_argument('--research-logic');p.add_argument('--spec');p.add_argument('--projection');p.add_argument('--outdir',required=True)
 p.add_argument('--no-pdf',action='store_true')
 a=p.parse_args(argv)
 try:
  out=Path(a.outdir)
  if a.projection:
   if a.knowledge or a.research_logic or a.spec:raise ContractError('SELECT_PROJECTION_OR_SOURCE_AND_SPEC')
   proj=Path(a.projection);verify_projection(proj)
  else:
   if not(a.spec and bool(a.knowledge)!=bool(a.research_logic)):
    raise ContractError('EXACTLY_ONE_PFS_SOURCE_AND_VIEW_SPEC_REQUIRED')
   for path in (a.knowledge or a.research_logic,a.spec):
    src=Path(path).resolve()
    if out.resolve()==src.parent or out.resolve().is_relative_to(src.parent):
     raise ContractError('PFS_LOGIC_OUTPUT_INSIDE_SOURCE_TREE')
   proj=out/'pfs_logic_projection.json'
   if proj.exists():raise ContractError('PFS_LOGIC_OUTPUT_ALREADY_EXISTS')
   if a.research_logic:
    from sharepack.logic_ab import project_ab
    project_ab(a.research_logic,a.spec,proj)
   else:project(a.knowledge,a.spec,proj)
  target,report=render(proj,out,pdf=not a.no_pdf)
  print(json.dumps({'pptx':str(target),'pages':len(report),'ids':[x['relation_ids'] for x in report],'science_review':'PENDING'},ensure_ascii=False))
  return 0
 except (ContractError,FileNotFoundError,KeyError,ValueError) as err:
  print(json.dumps({'error':str(err)},ensure_ascii=False),file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
