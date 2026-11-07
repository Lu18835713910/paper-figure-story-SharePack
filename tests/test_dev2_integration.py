"""PFS integration is a synthetic contract/e2e test, NOT actual user PFS v1.1.1 acceptance."""
import copy
import tempfile
import unittest
from pathlib import Path
import fitz
from PIL import Image

from sharepack.common import ContractError,save,load,digest
from sharepack.ingest import inspect_pdf
from sharepack.pfs_adapter import bridge, import_assets
from sharepack.contract import validate_story
from sharepack.render import build

class BridgeIntegration(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  self.pfs=self.root/'pfs_source';self.pfs.mkdir()
  self.out=self.root/'sharepack_output';self.out.mkdir()
  self.pic=self.pfs/'fig.png'
  Image.new('RGB',(200,140),'white').save(self.pic)
  self.pdfhash='a'*64
  self.m={'schema_version':'1.1','document_registry':[{'id':'D','sha256':self.pdfhash,'role':'primary_study','format':'pdf'}],
     'entities':[{'id':'M','kind':'experiment'},{'id':'E','kind':'evidence'}],
     'figures':[{'id':'F','document_id':'D','kind':'main'}],
     'stories':[{'id':'RSU','method_ids':['M'],'evidence_ids':['E'],'figure_refs':['F'],'presentation_order':1}],
     'relations':[{'id':'R','from':'E','to':'M','type':'compares','certainty':'paper_reported','provenance':'paper','mandatory':False}]}
  self.knowledge=self.pfs/'knowledge.json';save(self.knowledge,self.m)
  self.asset={'asset_version':'m2b-1','assets':[{'id':'A','figure_id':'F','source_document_id':'D',
      'source_sha256':self.pdfhash,'sha256':digest(self.pic),'evidence_ids':['E'],'path':'fig.png',
      'physical_page':2,'crop':[.1,.2,.9,.8]}]}
  self.assets=self.pfs/'assets.json';save(self.assets,self.asset)
 def tearDown(self): self.tmp.cleanup()
 def test_unreviewed_asset_copy_and_pfs_bound_story_end_to_end(self):
  pre_sha=[digest(self.knowledge),digest(self.assets),digest(self.pic)]
  context_path,ctx=bridge(self.knowledge,self.out/'bridge',self.assets)
  imported=import_assets(self.knowledge,self.assets,self.out/'imported')
  self.assertEqual(imported['assets'][0]['review_status'],'PENDING')
  self.assertEqual(imported['assets'][0]['sha256'],digest(self.pic))
  card={'order':1,'stage':'研究','title':'逻辑研究故事','intro':'我们如何验证','method':'将数据和对照比较',
     'observation':'看到有条件的结果','interpretation':'只支持部分结论','takeaway':'需要进一步实验',
     'claim_ids':['C1'],'figure_asset_ids':['pfsa_001']}
  story={'contract':'sharepack-story-v1','paper':{'title':'Test','doi':'10.1000/test','authors_short':'Test et al.'},
     'pdf_sha256':self.pdfhash,'profile':'standard','review_status':'PARTIAL','formal_ready':False,
     'sources':[{'id':'SRC','pdf_page':2}],
     'claims':[{'id':'C1','question':'问题是什么','method':'怎么验证','observation':'观察到什么','meaning':'这说明什么',
                'limit':'限制是什么','source_ids':['SRC'],'required':True,'review_status':'PARTIAL',
                'pfs_rsu_ids':['RSU'],'pfs_relation_ids':['R']}],
     'cards':[{**card,'order':i,'title':f'测试卡 {i}'} for i in range(1,9)],
     'pfs_bridge':{'context_path':str(context_path),'context_sha256':digest(context_path),
                    'knowledge_sha256':ctx['knowledge_sha256']}}
  sf=self.out/'story.json';save(sf,story)
  va=validate_story(story,imported,self.out/'imported')
  self.assertTrue(va['valid']);self.assertFalse(va['formal_ready'])
  rep=build(sf,self.out/'imported'/'assets.json',self.out/'rendered',render_png=False)
  self.assertEqual(rep['contract_qa']['cards'],8)
  self.assertEqual(pre_sha,[digest(self.knowledge),digest(self.assets),digest(self.pic)])
  # Catch true upstream drift, even if the bridge context itself was untouched.
  self.m['stories'][0]['presentation_order']=9;save(self.knowledge,self.m)
  va=validate_story(story,imported,self.out/'imported',strict=False)
  self.assertFalse(va['valid']);self.assertIn('PFS_ORIGINAL_KNOWLEDGE_DRIFT',va['errors'])
 def test_missing_pfs_assets_not_hidden_and_reviewed_asset_blocked(self):
  self.asset['assets'][0]['path']='not-found.png';save(self.assets,self.asset)
  _,ctx=bridge(self.knowledge,self.out/'ok',self.assets)
  self.assertEqual(ctx['asset_summary']['unavailable_asset_ids'],['A'])
  with self.assertRaisesRegex(ContractError,'PFS_SOURCE_ASSETS_UNAVAILABLE'):
   import_assets(self.knowledge,self.assets,self.out/'imported')
  self.asset['assets'][0]['visual_review']={'status':'pass','figure_identity':True,'crop_complete':True,
      'axes_legends_scalebars':True,'significance_marks':True,'readability':True}
  save(self.assets,self.asset)
  with self.assertRaisesRegex(ContractError,'PFS_REVIEWED_ASSET_FILE_MISSING'):
   bridge(self.knowledge,self.out/'reject',self.assets)
 def test_unknown_relations_and_wrong_source_pdf_rejected(self):
  self.m['relations'][0]['type']='caused_by_magic';save(self.knowledge,self.m)
  with self.assertRaisesRegex(ContractError,'PFS_RELATION_TYPE_UNSUPPORTED'):
   bridge(self.knowledge,self.out/'bad')
  self.m['relations'][0]['type']='compares';save(self.knowledge,self.m)
  ctxp,ctx=bridge(self.knowledge,self.out/'good')
  st={'contract':'sharepack-story-v1','pdf_sha256':'f'*64,'profile':'standard',
       'paper':{'title':'a','doi':'b','authors_short':'c'},'sources':[{'id':'S','pdf_page':1}],
       'claims':[{'id':'C','question':'q','method':'m','observation':'o','meaning':'m','limit':'l',
         'source_ids':['S'],'required':True}],
       'cards':[{'order':i,'stage':'s','title':'t','intro':'i','method':'m','observation':'o',
         'interpretation':'i','takeaway':'t','claim_ids':['C'],'figure_asset_ids':[]} for i in range(1,9)],
       'pfs_bridge':{'context_path':str(ctxp),'context_sha256':digest(ctxp),'knowledge_sha256':ctx['knowledge_sha256']}}
  assets={'contract':'sharepack-figure-assets-v1','source_pdf_sha256':'f'*64,'assets':[]}
  qa=validate_story(st,assets,self.out,strict=False)
  self.assertIn('PFS_PAPER_SOURCE_HASH_MISMATCH',qa['errors'])
 def test_visual_review_status_requires_exact_identity_binding(self):
  a=self.asset['assets'][0]
  a['visual_review']={'status':'pass','reviewer':'Independent reviewer',
    'figure_identity':True,'crop_complete':True,'axes_legends_scalebars':True,
    'significance_marks':True,'readability':True}
  save(self.assets,self.asset)
  imported=import_assets(self.knowledge,self.assets,self.out/'unbound')
  self.assertEqual(imported['assets'][0]['review_status'],'PENDING')
  a['visual_review'].update({k:a.get(k) for k in (
    'sha256','source_sha256','physical_page','crop','evidence_ids',
    'figure_id','source_document_id','panels')})
  save(self.assets,self.asset)
  imported=import_assets(self.knowledge,self.assets,self.out/'bound')
  self.assertEqual(imported['assets'][0]['review_status'],'VISUAL_REVIEWED')
 def test_source_asset_bytes_drift_after_bridge_is_rejected(self):
  import hashlib
  cp,ctx=bridge(self.knowledge,self.out/'assetbridge',self.assets)
  r=copy.deepcopy(self.asset)
  # The manifest is unchanged; only the source image bytes have been replaced.
  Image.new('RGB',(200,140),'black').save(self.pic)
  card={'contract':'sharepack-story-v1','pdf_sha256':self.pdfhash,'profile':'standard',
    'paper':{'title':'a','doi':'b','authors_short':'c'},
    'sources':[{'id':'S','pdf_page':1}],
    'claims':[{'id':'C','question':'q','method':'m','observation':'o','meaning':'m','limit':'l','source_ids':['S'],'required':True}],
    'cards':[{'order':i,'stage':'stage','title':'title','intro':'intro','method':'method',
       'observation':'obs','interpretation':'interp','takeaway':'take','claim_ids':['C'],
       'figure_asset_ids':[]} for i in range(1,9)],
    'pfs_bridge':{'context_path':str(cp),'context_sha256':digest(cp),
                  'knowledge_sha256':ctx['knowledge_sha256']}}
  a={'contract':'sharepack-figure-assets-v1','source_pdf_sha256':self.pdfhash,'assets':[]}
  q=validate_story(card,a,self.out,strict=False)
  self.assertFalse(q['valid']);self.assertIn('PFS_ASSET_FILE_HASH_MISMATCH:A',q['errors'])
 def test_pfs_output_inside_source_is_disallowed(self):
  with self.assertRaisesRegex(ContractError,'PFS_OUTPUT_INSIDE_SOURCE_TREE'):
   bridge(self.knowledge,self.pfs/'subdir')

class FigureCaptions(unittest.TestCase):
 def test_nature_plos_and_other_caption_styles_are_candidates_only(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);pdf=root/'test.pdf';doc=fitz.open()
   for line in ('Fig. 1 | Nature', 'Fig 2. PLOS Figure', 'Figure 3: Other'):
    p=doc.new_page();p.draw_rect(fitz.Rect(70,80,340,260),color=(0,0,0))
    p.insert_text((65,575),line,fontsize=11)
   doc.save(pdf);doc.close()
   result=inspect_pdf(pdf,root/'result')
   self.assertEqual([f['figure_label'] for f in result['figures']],['Fig. 1','Fig. 2','Fig. 3'])
   self.assertTrue(all(f['status']=='CANDIDATE_NOT_PANEL_VERIFIED' for f in result['figures']))

if __name__=='__main__':unittest.main()
