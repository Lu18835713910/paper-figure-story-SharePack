#!/usr/bin/env python3
"""Independent read-only PFS->SharePack compatibility harness.

Run on the workstation with *actual* v1.1.1 PFS output. It does not execute
PFS, modify knowledge, repair assets, or claim scientific validation.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sharepack.common import digest,save,ContractError
from sharepack.pfs_adapter import bridge,verify_bridge_context

def inventory(paths):
    found={}
    for root in paths:
        root=Path(root).resolve()
        if not root.exists():raise ContractError('PROTECTED_PATH_MISSING:'+str(root))
        for p in ([root] if root.is_file() else root.rglob('*')):
            if p.is_file():
                found[str(p)]=digest(p)
    return found

def main(argv=None):
    a=argparse.ArgumentParser(description='Read-only real PFS 1.1.1 contract acceptance')
    a.add_argument('--knowledge',required=True);a.add_argument('--pfs-assets')
    a.add_argument('--outdir',required=True);a.add_argument('--protect-root',action='append',default=[])
    z=a.parse_args(argv)
    kp=Path(z.knowledge).resolve();ap=Path(z.pfs_assets).resolve() if z.pfs_assets else None
    out=Path(z.outdir).resolve();protect=[kp]+([ap] if ap else [])+[Path(p).resolve() for p in z.protect_root]
    for root in protect:
        if root.is_dir() and out.is_relative_to(root):raise ContractError('OUTPUT_INSIDE_PROTECTED_ROOT')
    if (out/'pfs_bridge_context.json').exists():raise ContractError('OUTPUT_ALREADY_EXISTS_USE_NEW_DIRECTORY')
    before=inventory(protect)
    context_path,context=bridge(kp,out,ap)
    verify_bridge_context(context_path)
    after=inventory(protect)
    if before!=after:raise ContractError('PFS_PROTECTED_FILE_MUTATION')
    report={'kind':'readonly_pfs_bridge_acceptance','knowledge_path':str(kp),
       'knowledge_schema':context['pfs_knowledge_schema_version'],
       'asset_manifest':str(ap) if ap else None,'rsus':len(context['rsus']),
       'typed_relations':len(context['relations']),
       'figure_records':len(context['figures']),'protected_file_count':len(before),
       'sha_unchanged':True,'status':'BRIDGE_STRUCTURAL_PASS_ONLY',
       'scientific_approval':'NOT_PERFORMED','visual_approval':'NOT_PERFORMED',
       'full_sharepack_stories':'NOT_PERFORMED'}
    save(out/'readonly_acceptance_report.json',report)
    print(json.dumps(report,ensure_ascii=False,indent=2));return 0
if __name__=='__main__':
    try:sys.exit(main())
    except (ContractError,FileNotFoundError,ValueError) as e:
        print(json.dumps({'error':str(e)}),file=sys.stderr);sys.exit(2)
