"""Compile any reviewed editorial story using the installed CLI."""
import argparse, subprocess, sys
from pathlib import Path

parser=argparse.ArgumentParser()
for arg in ('pdf','story','plan','output'):
    parser.add_argument('--'+arg,type=Path,required=True)
args=parser.parse_args()
out=args.output.resolve()
out.mkdir(parents=True)
assets=out/'figures'
for command,options in [
    ('extract-reviewed-figures',['--pdf',args.pdf,'--plan',args.plan,'--outdir',assets]),
    ('verify-reviewed-figures',['--pdf',args.pdf,'--plan',args.plan,'--manifest',assets/'figure_manifest.json']),
    ('audit-plan',['--story',args.story,'--assets',assets/'assets.json','--outdir',out/'planning']),
    ('render',['--story',args.story,'--assets',assets/'assets.json','--outdir',out/'output','--layout-engine','editorial','--no-pdf']),
]:
    call=[sys.executable,'-m','sharepack',command,*map(str,options)]
    result=subprocess.run(call,capture_output=True)
    (out/(command+'.log')).write_bytes(result.stdout+result.stderr+f'\nexit={result.returncode}\n'.encode())
    result.check_returncode()
