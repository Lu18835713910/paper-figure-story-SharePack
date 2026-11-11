"""CLI of standalone SharePack. An Agent supplies scientific interpretations, not the CLI."""
import argparse,json,sys
from pathlib import Path
from .common import ContractError,load,save

def main(argv=None):
    p=argparse.ArgumentParser(prog='sharepack',description='PDF evidence preparation, human/Agent reviewed story rendering, optional PFS read-only import')
    sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('prepare',help='Index PDF, identify unreviewed Figure candidates; no invented science')
    a.add_argument('--pdf',required=True);a.add_argument('--outdir',required=True)
    b=sub.add_parser('extract-regions',help='Exact PDF panel crops from reviewed region coordinates')
    b.add_argument('--pdf',required=True);b.add_argument('--regions',required=True);b.add_argument('--outdir',required=True)
    g=sub.add_parser('audit-plan',help='Audit authored story structure and panel selection; does not create science')
    g.add_argument('--story',required=True);g.add_argument('--assets',required=True);g.add_argument('--outdir',required=True)
    c=sub.add_parser('validate');c.add_argument('--story',required=True);c.add_argument('--assets',required=True);c.add_argument('--profile',choices=('standard','full'))
    d=sub.add_parser('render');d.add_argument('--story',required=True);d.add_argument('--assets',required=True);d.add_argument('--outdir',required=True);d.add_argument('--profile',choices=('standard','full'));d.add_argument('--no-pdf',action='store_true');d.add_argument('--layout-engine',choices=('freeform','legacy','editorial','flex'),default='freeform');d.add_argument('--pdf-index',help='Optional prepare/pdf_index.json; must match source PDF SHA-256');d.add_argument('--logo-manifest',help='Optional rights-verified original journal logo manifest JSON');d.add_argument('--agent-layout-plan',help='Optional SHA-bound Agent preferences JSON; requires flex layout engine')
    e=sub.add_parser('bridge-pfs',help='PFS 1.1 schema compatibility; emits source pointers, NOT cards')
    e.add_argument('--knowledge',required=True);e.add_argument('--pfs-assets');e.add_argument('--pfs-crosswalk');e.add_argument('--outdir',required=True)
    f=sub.add_parser('import-pfs-assets',help='Copy SHA-verified original PFS Figure assets into an isolated SharePack asset package')
    f.add_argument('--knowledge',required=True);f.add_argument('--pfs-assets',required=True);f.add_argument('--pfs-crosswalk');f.add_argument('--outdir',required=True)
    args=p.parse_args(argv)
    try:
        if args.command=='prepare':
            from .ingest import inspect_pdf
            r=inspect_pdf(args.pdf,args.outdir);print(json.dumps({'pages':r['pages'],'candidate_figures':len(r['figures']),'review':'NOT_PERFORMED'},ensure_ascii=False))
        elif args.command=='extract-regions':
            from .ingest import extract_regions
            r=extract_regions(args.pdf,args.regions,args.outdir);print(json.dumps({'assets':len(r['assets']),'source_sha256':r['source_pdf_sha256']}))
        elif args.command=='audit-plan':
            from .planning import plan_audit,panel_selection_audit
            st=load(args.story);asst=load(args.assets);out=Path(args.outdir)
            if out.resolve() in (Path(args.story).resolve().parent,Path(args.assets).resolve().parent):
                raise ContractError('OUTPUT_SAME_AS_INPUT')
            a=plan_audit(st,asst);b=panel_selection_audit(st,asst)
            save(out/'story_plan_audit.json',a);save(out/'panel_selection_audit.json',b)
            print(json.dumps({'story_plan_status':a['status'],'figure_review_status':b['status'],
                'warnings':len(a['warnings']),'pending_panel_selections':len(b['pending'])},ensure_ascii=False))
        elif args.command=='validate':
            from .contract import validate_story
            r=validate_story(load(args.story),load(args.assets),Path(args.assets).resolve().parent,profile=args.profile,strict=False)
            print(json.dumps(r,ensure_ascii=False,indent=2));return 0 if r['valid'] else 2
        elif args.command=='render':
            from .render import build
            r=build(args.story,args.assets,args.outdir,profile=args.profile,render_png=not args.no_pdf,layout_engine=args.layout_engine,pdf_index_path=args.pdf_index,logo_manifest_path=args.logo_manifest,agent_layout_plan_path=args.agent_layout_plan)
            print(json.dumps({'pptx':str(Path(args.outdir)/'SharePack_editable.pptx'),'cards':r['contract_qa']['cards'],'formal_ready':r['contract_qa']['formal_ready'],'png_count':r.get('png_count',0),
                                    'publication_style':r['publication_style']['style_id'],
                                    'style_status':r['publication_style']['status']},ensure_ascii=False))
        elif args.command=='import-pfs-assets':
            from .pfs_adapter import import_assets
            a=import_assets(args.knowledge,args.pfs_assets,args.outdir)
            print(json.dumps({'assets':len(a['assets']),'source_pdf_sha256':a['source_pdf_sha256'],'science_review':'NOT_PERFORMED'},ensure_ascii=False))
        elif args.command=='bridge-pfs':
            from .pfs_adapter import bridge
            path,r=bridge(args.knowledge,args.outdir,args.pfs_assets,args.pfs_crosswalk)
            print(json.dumps({'context':str(path),'rsus':len(r['rsus']),'relations':len(r['relations']),
                               'science_review':'NOT_PERFORMED','status':'AGENT_HANDOFF_REQUIRED'},ensure_ascii=False))
        return 0
    except (ContractError,ValueError,FileNotFoundError,KeyError) as err:
        print(json.dumps({'error':type(err).__name__,'message':str(err)},ensure_ascii=False),file=sys.stderr)
        return 2

if __name__=='__main__':raise SystemExit(main())
