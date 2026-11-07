"""Failure-oriented dev3 regression: independent of installed PFS and of Agent model."""
import copy, tempfile, unittest
from pathlib import Path
from PIL import Image
from pptx import Presentation
from sharepack.common import save,load,digest,ContractError
from sharepack.pfs_adapter import bridge,import_assets
from sharepack.contract import validate_story
from sharepack.render import build
from sharepack.planning import plan_audit

class LegacyPFSCompat(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.r=Path(self.temp.name)
  self.src=self.r/'pfs';self.src.mkdir()
  for name in ('F1','F6'):
   Image.new('RGB',(700,460),'white').save(self.src/f'{name}.png')
  self.model={'schema_version':'1.1','document_registry':[{'id':'D','role':'primary_study','format':'pdf','sha256':'d'*64}],
    'entities':[{'id':'M','kind':'method'},{'id':'E','kind':'evidence'}],
    'figures':[{'id':'F1','document_id':'D','kind':'main'},{'id':'F6','document_id':'D','kind':'conceptual'}],
    'stories':[{'id':'RS1','figure_refs':['F1'],'method_ids':['M'],'evidence_ids':['E'],
        'question_or_purpose':'why','finding_or_argument':'how','limits':['limited'],
        'source_refs':[{'document_id':'D','locator':{'physical_page':3},'verification':'direct_checked'}]},
       {'id':'RS6','figure_refs':['F6'],'method_ids':[],'evidence_ids':[],
        'question_or_purpose':'model','finding_or_argument':'synthesis'}],
    'relations':[]}
  self.k=self.src/'knowledge.json';save(self.k,self.model)
  self.a=self.src/'figure_assets.json';save(self.a,{'version':'pfs-figure-assets-1','assets':[
   {'id':name,'figure_id':name,'path':f'{name}.png','sha256':digest(self.src/f'{name}.png'),
    'source_pdf_sha256':'d'*64,'physical_page':i,'bbox_pt':[40,44,560,648],
    'visual_status':'PENDING'} for i,name in [(3,'F1'),(11,'F6')]]})
 def tearDown(self): self.temp.cleanup()
 def test_legacy_manifest_copies_without_fake_evidence_or_review(self):
  before=[digest(self.k),digest(self.a),digest(self.src/'F1.png'),digest(self.src/'F6.png')]
  path,context=bridge(self.k,self.r/'bridge',self.a)
  self.assertEqual(context['asset_summary']['source_asset_contract'],'pfs-figure-assets-1')
  self.assertIn('UNBOUND_FIGURE:F6',context['asset_summary']['diagnostics'])
  self.assertEqual(context['rsus'][0]['question_or_purpose'],'why')
  self.assertEqual(context['rsus'][0]['source_refs'][0]['locator']['physical_page'],3)
  imported=import_assets(self.k,self.a,self.r/'imported')
  self.assertEqual(len(imported['assets']),2)
  self.assertEqual(imported['assets'][1]['pfs_evidence_ids'],[])
  self.assertEqual(imported['assets'][1]['evidence_role'],'UNBOUND_FIGURE_REQUIRES_REVIEW')
  self.assertTrue(all(x['review_status']=='PENDING' for x in imported['assets']))
  self.assertEqual(imported['assets'][0]['crop_pdf_pt'],[40,44,560,648])
  self.assertEqual(before,[digest(self.k),digest(self.a),digest(self.src/'F1.png'),digest(self.src/'F6.png')])
 def test_legacy_drift_not_silent(self):
  a=load(self.a);a['assets'][0]['source_pdf_sha256']='e'*64;save(self.a,a)
  with self.assertRaisesRegex(ContractError,'PFS_ASSET_SOURCE_HASH_MISMATCH'):
   bridge(self.k,self.r/'bad',self.a)

class EveryMetricAndLimitVisible(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.r=Path(self.temp.name)
  i=self.r/'assets';i.mkdir();Image.new('RGB',(200,180),'white').save(i/'a.png')
  self.assets={'contract':'sharepack-figure-assets-v1','source_pdf_sha256':'f'*64,
   'assets':[{'id':'A','figure':'Fig. 1','pdf_page':2,'path':'a.png','sha256':digest(i/'a.png'),
     'source_pdf_sha256':'f'*64,'review_status':'PENDING'}]}
  save(i/'assets.json',self.assets)
  self.cl={'id':'C','question':'有什么问题','method':'做了对照','observation':'读到结果',
    'meaning':'可有限推断','limit':'不等于独立验证因果机制','source_ids':['S'],'required':True,
    'metrics':[{'label':'指标一','value':'1.0 → 0.43','definition':'相对蛋白信号','comparison':'WT标准化为1.0'},
               {'label':'指标二','value':'P=0.01','definition':'检验差异的P值','comparison':'两组细胞'}]}
  self.story={'contract':'sharepack-story-v1','paper':{'title':'T','doi':'10.1/x','authors_short':'A et al.'},
    'pdf_sha256':'f'*64,'profile':'standard','sources':[{'id':'S','pdf_page':2}],
    'claims':[self.cl], 'review_status':'PARTIAL','formal_ready':False,
    'cards':[{'order':n,'stage':'发现','title':f'单项发现{n}','intro':'如何研究','question':'有什么问题',
      'method':'作者做了一组对照实验','observation':'结果支持部分假设','interpretation':'有限发现',
      'takeaway':'可能存在调控关系','claim_ids':['C'],'figure_asset_ids':['A'],
      'layout_type':'evidence','narrative_role':'finding'} for n in range(1,9)]}
  self.s=self.r/'story.json';save(self.s,self.story)
 def tearDown(self): self.temp.cleanup()
 def test_two_metrics_and_limit_visible_and_source_binding_safe(self):
  rep=build(self.s,self.r/'assets'/'assets.json',self.r/'render',render_png=False)
  self.assertEqual(rep['layout_geometry'][0]['visible_metric_count'],2)
  self.assertEqual(rep['layout_geometry'][0]['visible_limit_count'],1)
  deck=Presentation(self.r/'render'/'SharePack_editable.pptx')
  tx=' '.join(sh.text for sh in deck.slides[0].shapes if sh.has_text_frame)
  for part in ('指标一','指标二','P=0.01','WT标准化为1.0','不等于独立验证因果机制'):
   self.assertIn(part,tx)
  self.assertIsNone(load(self.r/'render'/'card_source_map.json')['cards'][0]['figures'][0]['crop_pdf_pt'])
 def test_three_metrics_long_text_reports_capacity_not_loss(self):
  x=copy.deepcopy(self.story)
  x['claims'][0]['metrics'][0]['definition']='必须解释的长段落'*60
  save(self.r/'bad.json',x)
  with self.assertRaisesRegex(ContractError,'LAYOUT_TEXT_CAPACITY_EXCEEDED'):
   build(self.r/'bad.json',self.r/'assets'/'assets.json',self.r/'bad_render',render_png=False)
 def test_story_roles_declared_or_diagnostic_and_number_range(self):
  q=plan_audit(self.story,self.assets)
  self.assertIn('STORY_COVERAGE_UNPROVEN:research_navigation',q['warnings'])
  s=copy.deepcopy(self.story);s['cards']=s['cards'][:6]
  with self.assertRaisesRegex(ContractError,'CARD_COUNT_STANDARD_6'):
   validate_story(s,self.assets,self.r/'assets')

if __name__=='__main__':unittest.main()
