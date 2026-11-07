#!/usr/bin/env python3
"""Read-only compatibility acceptance for a real PFS v1.1.1 run.

Runs the installed SharePack bridge against real PFS outputs. Never writes inside
any PFS source directory. Does NOT perform scientific review, rendering, or
claim a PFS-quality improvement. A matching source PDF snapshot is mandatory.
"""
import argparse, hashlib, json, os, sys, traceback
from pathlib import Path

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  while True:
   b=f.read(2**20)
   if not b: break
   h.update(b)
 return h.hexdigest()

def write(p,o):
 p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--sharepack-src',type=Path,required=True,help='Directory containing sharepack package')
 p.add_argument('--knowledge',type=Path,required=True)
 p.add_argument('--pfs-assets',type=Path,required=True)
 p.add_argument('--independent-story',type=Path,required=True)
 p.add_argument('--outdir',type=Path,required=True)
 p.add_argument('--figure-crosswalk',type=Path)
 p.add_argument('--logic',type=Path)
 p.add_argument('--inventory',type=Path)
 a=p.parse_args()
 root=a.sharepack_src.resolve();sys.path.insert(0,str(root))
 from sharepack.pfs_adapter import bridge,import_assets,verify_bridge_context
 from sharepack.common import ContractError
 inputs={'knowledge':a.knowledge,'pfs_assets':a.pfs_assets,'independent_story':a.independent_story}
 if a.logic:inputs['logic']=a.logic
 if a.figure_crosswalk:inputs['figure_crosswalk']=a.figure_crosswalk
 if a.inventory:inputs['inventory']=a.inventory
 for k,v in inputs.items():
  if not v.is_file():raise SystemExit(f'INPUT_MISSING:{k}:{v}')
 out=a.outdir.resolve()
 if out.exists() and any(out.iterdir()):raise SystemExit('OUTPUT_MUST_BE_NEW_EMPTY_DIR')
 # These sources are never to be written to, even when nested inside a PFS tree.
 for name,pth in inputs.items():
  src=pth.resolve()
  if out==src.parent or out.is_relative_to(src.parent):
   raise SystemExit('OUTPUT_INSIDE_SOURCE_TREE:'+name)
 before={k:sha(v) for k,v in inputs.items()}
 independent=json.loads(a.independent_story.read_text('utf-8-sig'))
 model=json.loads(a.knowledge.read_text('utf-8-sig'))
 pdf_sha=independent.get('pdf_sha256')
 registered=[d.get('sha256') for d in model.get('document_registry',[]) if d.get('role') in ('main_paper','primary_study')]
 recognized=[d for d in model.get('document_registry',[]) if d.get('role') in ('main_paper','primary_study')]
 if not recognized:
  raise SystemExit('PFS_MAIN_PAPER_DOCUMENT_MISSING: valid PFS role is main_paper')
 same_pdf=bool(pdf_sha and pdf_sha in registered)
 report={'contract':'sharepack-real-pfs-v111-acceptance-v1','pfs_tag_expected':'v1.1.1',
         'pfs_knowledge_schema':model.get('schema_version'),
         'same_primary_pdf_sha':same_pdf,'independent_pdf_sha256':pdf_sha,
         'pfs_primary_pdf_sha256s':registered,'input_sha256_before':before,
         'input_sha256_after':{},'protected_inputs_unchanged':None,
         'bridge':'NOT_RUN','asset_import':'NOT_RUN',
         'scientific_quality':'NOT_TESTED','full_AB':'NOT_TESTED',
         'warnings':[],'diagnostics':[]}
 if not same_pdf:
  report['diagnostics'].append('AB_INVALID_DIFFERENT_PRIMARY_PDF_SNAPSHOT')
  report['status']='BLOCKED_SOURCE_IDENTITY'
  out.mkdir(parents=True,exist_ok=True)
 else:
  out.mkdir(parents=True,exist_ok=True)
  try:
   path,context=bridge(a.knowledge,out/'pfs_bridge',a.pfs_assets,a.figure_crosswalk)
   verify_bridge_context(path)
   report['bridge']='PASS'
   report['bridge_rsus']=len(context.get('rsus',[]))
   report['bridge_relations']=len(context.get('relations',[]))
   report['assets_summary']=context.get('asset_summary')
   report['warnings'].extend(context.get('asset_summary',{}).get('diagnostics',[]))
  except (Exception) as e:
   report['bridge']='BLOCKED';report['diagnostics'].append('BRIDGE:'+type(e).__name__+':'+str(e))
  if report['bridge']=='PASS':
   try:
    result=import_assets(a.knowledge,a.pfs_assets,out/'pfs_assets_import',a.figure_crosswalk)
    report['asset_import']='PASS'
    report['asset_count']=len(result['assets'])
    report['unbound_figure_count']=sum(z.get('evidence_role')=='UNBOUND_FIGURE_REQUIRES_REVIEW' for z in result['assets'])
    report['pending_figure_count']=sum(z.get('review_status')=='PENDING' for z in result['assets'])
   except (Exception) as e:
    report['asset_import']='BLOCKED';report['diagnostics'].append('IMPORT:'+type(e).__name__+':'+str(e))
  report['status']='READY_FOR_AGENT_STORY_PLANNING' if report['asset_import']=='PASS' else 'BLOCKED_PFS_ASSET_LAYER'
 after={k:sha(v) for k,v in inputs.items()}
 report['input_sha256_after']=after
 report['protected_inputs_unchanged']=(before==after)
 if not report['protected_inputs_unchanged']:
  report['status']='FAIL_PROTECTED_INPUT_DRIFT'
 write(out/'real_pfs_bridge_report.json',report)
 print(json.dumps({k:report.get(k) for k in ('status','same_primary_pdf_sha','bridge','asset_import','protected_inputs_unchanged','bridge_rsus','asset_count','warnings','diagnostics')},ensure_ascii=False,indent=2))
 return 0 if report['status']=='READY_FOR_AGENT_STORY_PLANNING' else 2

if __name__=='__main__':raise SystemExit(main())
