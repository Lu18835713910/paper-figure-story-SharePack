#!/usr/bin/env python3
"""Mechanical comparison of PDF-only and PFS-assisted story outputs.

Not an automatic measure of scientific quality: independent blinded review needed.
"""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sharepack.common import load,save

def summary(data):
    claims=data.get('claims',[]);cards=data.get('cards',[])
    fig=set(data.get('required_figure_labels',[]))
    return {'card_count':len(cards),'claim_count':len(claims),
      'required_claim_ids':sorted(x['id'] for x in claims if x.get('required')),
      'metrics_documented':sum(len(x.get('metrics',[])) for x in claims),
      'source_linked_claims':sum(bool(x.get('source_ids')) for x in claims),
      'pfs_rsu_bound_claims':sum(bool(x.get('pfs_rsu_ids')) for x in claims),
      'pfs_relation_bound_claims':sum(bool(x.get('pfs_relation_ids')) for x in claims),
      'required_figures':sorted(fig), 'story_review_status':data.get('review_status'),
      'formal_ready_claimed':data.get('formal_ready') is True}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--direct-story',required=True);p.add_argument('--pfs-story',required=True);p.add_argument('--out',required=True)
    a=p.parse_args()
    direct=load(a.direct_story);pfs=load(a.pfs_story)
    report={'contract':'sharepack-mode-comparison-v1',
      'same_paper_sha':direct.get('pdf_sha256')==pfs.get('pdf_sha256'),
      'direct':summary(direct),'pfs_assisted':summary(pfs),
      'note':'Counts/identities only. Scientific completeness, correctness and readability require blind source review.',
      'independent_blinded_quality_judgment':'NOT_PERFORMED'}
    if not report['same_paper_sha']:
        report['status']='DIFFERENT_PAPER_SNAPSHOT_NO_FAIR_COMPARISON'
    else:report['status']='STRUCTURAL_COUNTS_ONLY'
    save(a.out,report);print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
