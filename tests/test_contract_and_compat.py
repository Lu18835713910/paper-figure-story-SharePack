import copy,hashlib,json,tempfile,unittest,sys
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from sharepack.common import ContractError,save,load,digest
from sharepack.contract import validate_story
from sharepack.ingest import inspect_pdf,extract_regions
from sharepack.pfs_adapter import bridge
from sharepack.render import build

class ContractAndCompatibility(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.root=Path(self.t.name)
  src=self.root/'original.pdf'
  import fitz
  d=fitz.open();p=d.new_page();p.insert_text((60,100),'Research data');p.insert_text((70,500),'Fig. 1 | Evidence panel');d.save(src);d.close()
  self.pdf=src;self.sha=digest(src)
  region={'source_pdf_sha256':self.sha,'regions':[{'id':'A1','figure':'Figure 1','pdf_page':1,'crop_pdf_pt':[48,120,300,380]}]}
  save(self.root/'regions.json',region);extract_regions(src,self.root/'regions.json',self.root/'assets')
  self.asset=load(self.root/'assets'/'assets.json')
  claim={'id':'C','question':'问题','method':'方法','observation':'发现','meaning':'意义','limit':'边界','source_ids':['S'],
         'review_status':'PARTIAL','required':True,'metrics':[{'label':'测量','value':'3','definition':'数量','comparison':'基线1'}]}
  card={'order':1,'stage':'发现','title':'测试卡片','intro':'引言','question':'为什么研究','method':'做了一项分析',
        'observation':'观察到一些结果','interpretation':'比较结果','takeaway':'有限结论','claim_ids':['C'],'figure_asset_ids':['A1']}
  self.story={'contract':'sharepack-story-v1','paper':{'title':'Test','doi':'10.1000/test','authors_short':'A et al.'},
     'pdf_sha256':self.sha,'profile':'standard','review_status':'PARTIAL','formal_ready':False,
     'sources':[{'id':'S','pdf_page':1}], 'claims':[claim],
     'cards':[{**card,'order':i,'title':f'测试卡片 {i}'} for i in range(1,9)]}
 def tearDown(self):self.t.cleanup()
 def test_independent_pdf_index_extracts_candidate_only(self):
  a=inspect_pdf(self.pdf,self.root/'pre');self.assertEqual(a['pages'],1);self.assertEqual(len(a['figures']),1)
  self.assertIn('CANDIDATE',a['figures'][0]['status']);self.assertEqual(a['science_review'],'NOT_PERFORMED')
 def test_contract_standard_valid_and_source_pending(self):
  r=validate_story(self.story,self.asset,self.root/'assets');self.assertTrue(r['valid']);self.assertFalse(r['formal_ready'])
 def test_card_range_and_required_claim(self):
  j=copy.deepcopy(self.story);j['cards']=j['cards'][:7]
  with self.assertRaisesRegex(ContractError,'CARD_COUNT_STANDARD_7'):validate_story(j,self.asset,self.root/'assets')
  j=copy.deepcopy(self.story);j['cards'][0]['claim_ids']=[]
  with self.assertRaisesRegex(ContractError,'CARD_CLAIM_INVALID'):validate_story(j,self.asset,self.root/'assets')
 def test_full_capacity(self):
  j=copy.deepcopy(self.story);j['profile']='full'
  j['cards']=[{**self.story['cards'][i%8],'order':i+1,'title':f'独立内容位置{i+1}'} for i in range(15)]
  self.assertTrue(validate_story(j,self.asset,self.root/'assets')['valid'])
  j['cards'].append({**j['cards'][0],'order':16})
  with self.assertRaisesRegex(ContractError,'CARD_COUNT_FULL_16'):validate_story(j,self.asset,self.root/'assets')
 def test_asset_hash_guard_and_traversal(self):
  a=copy.deepcopy(self.asset);a['assets'][0]['sha256']='0'*64
  with self.assertRaisesRegex(ContractError,'ASSET_HASH_DRIFT'):validate_story(self.story,a,self.root/'assets')
  a=copy.deepcopy(self.asset);a['assets'][0]['path']='../original.pdf'
  with self.assertRaisesRegex(ContractError,'ASSET_MISSING_OR_INVALID'):validate_story(self.story,a,self.root/'assets')
 def test_source_pdf_guard(self):
  j=copy.deepcopy(self.story);j['pdf_sha256']='bad'
  with self.assertRaisesRegex(ContractError,'PDF_SNAPSHOT_CONFLICT'):validate_story(j,self.asset,self.root/'assets')
  reg=load(self.root/'regions.json');reg['source_pdf_sha256']='bad';save(self.root/'bad.json',reg)
  with self.assertRaisesRegex(ContractError,'SOURCE_PDF_SHA_MISMATCH'):extract_regions(self.pdf,self.root/'bad.json',self.root/'other')
 def test_editable_render_and_failure_isolation(self):
  st=self.root/'story.json';save(st,self.story)
  rep=build(st,self.root/'assets'/'assets.json',self.root/'output',render_png=False)
  self.assertEqual(rep['contract_qa']['cards'],8)
  from pptx import Presentation
  deck=Presentation(self.root/'output'/'SharePack_editable.pptx')
  self.assertEqual(len(deck.slides),8)
  self.assertTrue(all(sum(s.has_text_frame for s in slide.shapes)>8 for slide in deck.slides))
  self.assertFalse(rep['static_visual_qa']['canvas_overflow'])
  with self.assertRaisesRegex(ContractError,'OUTPUT_ALREADY_EXISTS'):build(st,self.root/'assets'/'assets.json',self.root/'output',render_png=False)
  self.assertEqual(digest(st),rep['story_sha256'])
 def test_pfs_bridge_known_and_version_fail(self):
  model={'knowledge_schema_version':'1.1','document_registry':[{'id':'D1'}],
        'entities':[{'id':'A'},{'id':'B'}], 'figures':[{'id':'F1'}],
        'stories':[{'id':'RSU01','presentation_order':1,'figure_refs':['F1'],
         'method_ids':['A'],'evidence_ids':['B'],'source_refs':[]}],
        'relations':[{'id':'R1','type':'compares','from':'A','to':'B','certainty':'paper_reported','provenance':'paper','mandatory':False}]}
  p=self.root/'pfs_source'/'pfs-model.json';save(p,model);before=digest(p)
  path,r=bridge(p,self.root/'bridge')
  self.assertEqual(r['pfs_knowledge_schema_version'],'1.1')
  self.assertEqual(r['rsus'][0]['rsu_id'],'RSU01')
  self.assertEqual(r['relations'][0]['type'],'compares')
  self.assertFalse(r['diagnostics']['formal_ready']);self.assertEqual(before,digest(p))
  model['knowledge_schema_version']='1.2';save(p,model)
  with self.assertRaisesRegex(ContractError,'PFS_SCHEMA_UNSUPPORTED'):bridge(p,self.root/'bad-bridge')
 def test_pfs_malformed_links_rejected(self):
  model={'schema_version':'1.1','document_registry':[],'entities':[{'id':'A'}],
   'figures':[{'id':'F'}], 'stories':[{'id':'X','figure_refs':['NO-FIG'],'method_ids':[], 'evidence_ids':[]}], 'relations':[]}
  p=self.root/'pfs_source'/'pfs.json';save(p,model)
  with self.assertRaisesRegex(ContractError,'PFS_UNRESOLVED_FIGURE'):bridge(p,self.root/'bad')

if __name__=='__main__':unittest.main()

# Additional PFS asset binding contract tests, without loading PFS runtime.
class PFSAssetBindingTest(unittest.TestCase):
 def test_asset_version_and_document_source_guards(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)
   m={'schema_version':'1.1','document_registry':[{'id':'D','sha256':'a'*64}],
      'entities':[{'id':'M'},{'id':'E'}],
      'figures':[{'id':'F','document_id':'D'}],
      'stories':[{'id':'RSU','method_ids':['M'],'evidence_ids':['E'],'figure_refs':['F']}],
      'relations':[]}
   save(root/'pfs_source'/'knowledge.json',m)
   asset={'asset_version':'m2b-1','assets':[{'id':'AS','figure_id':'F','source_document_id':'D',
               'source_sha256':'a'*64,'sha256':'b'*64,'evidence_ids':['E'],'path':'nonmounted_image.png'}]}
   save(root/'pfs_source'/'assets.json',asset)
   path,x=bridge(root/'pfs_source'/'knowledge.json',root/'out',root/'pfs_source'/'assets.json')
   self.assertEqual(x['asset_summary']['count'],1)
   self.assertFalse(x['diagnostics']['formal_ready'])
   asset['asset_version']='future';save(root/'pfs_source'/'assets.json',asset)
   with self.assertRaisesRegex(ContractError,'PFS_ASSET_VERSION_UNSUPPORTED'):
    bridge(root/'pfs_source'/'knowledge.json',root/'future',root/'pfs_source'/'assets.json')
   asset['asset_version']='m2b-1';asset['assets'][0]['source_sha256']='b'*64
   save(root/'pfs_source'/'assets.json',asset)
   with self.assertRaisesRegex(ContractError,'PFS_ASSET_SOURCE_HASH_MISMATCH'):
    bridge(root/'pfs_source'/'knowledge.json',root/'bad',root/'pfs_source'/'assets.json')

class CrossInputBindings(unittest.TestCase):
 def test_pfs_rsu_binding_and_hash(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t)
   m={'schema_version':'1.1','document_registry':[],'entities':[],'figures':[],
      'stories':[{'id':'RSU1','method_ids':[],'evidence_ids':[],'figure_refs':[]}], 'relations':[]}
   save(root/'pfs_source'/'m1.json',m)
   cp,context=bridge(root/'pfs_source'/'m1.json',root/'bridge')
   st={'contract':'sharepack-story-v1','pdf_sha256':'xyz',
      'profile':'standard','paper':{'title':'a','doi':'b','authors_short':'c'},
      'review_status':'PARTIAL','sources':[{'id':'S','pdf_page':1}],
      'claims':[{'id':'CL','question':'q','method':'m','observation':'o','meaning':'r','limit':'l',
                 'source_ids':['S'],'required':True,'pfs_rsu_ids':['RSU1']}],
      'cards':[{'order':i,'stage':'a','title':'b','intro':'c','takeaway':'d','method':'e',
                'observation':'f','interpretation':'g','claim_ids':['CL'],'figure_asset_ids':[]} for i in range(1,9)],
      'pfs_bridge':{'context_path':str(cp),'context_sha256':digest(cp),'knowledge_sha256':context['knowledge_sha256']}}
   assets={'contract':'sharepack-figure-assets-v1','source_pdf_sha256':'xyz','assets':[]}
   self.assertTrue(validate_story(st,assets,root)['valid'])
   st['claims'][0]['pfs_rsu_ids']=['fabricated']
   with self.assertRaisesRegex(ContractError,'PFS_RSU_REF_UNKNOWN'):
    validate_story(st,assets,root)
   st['claims'][0]['pfs_rsu_ids']=['RSU1'];st['pfs_bridge']['knowledge_sha256']='drift'
   with self.assertRaisesRegex(ContractError,'PFS_KNOWLEDGE_BINDING_DRIFT'):
    validate_story(st,assets,root)
 def test_figure_coverage_guard(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t)
   st={'contract':'sharepack-story-v1','pdf_sha256':'x','profile':'standard',
      'paper':{'title':'a','doi':'b','authors_short':'c'},'required_figure_labels':['Figure 2'],
      'sources':[{'id':'S','pdf_page':1}],
      'claims':[{'id':'CL','question':'q','method':'m','observation':'o','meaning':'r','limit':'l','source_ids':['S'],'required':True}],
      'cards':[{'order':i,'stage':'x','title':'x','intro':'x','method':'x','observation':'x',
                'interpretation':'x','takeaway':'x','claim_ids':['CL'],'figure_asset_ids':[]} for i in range(1,9)]}
   assets={'contract':'sharepack-figure-assets-v1','source_pdf_sha256':'x','assets':[]}
   with self.assertRaisesRegex(ContractError,'REQUIRED_FIGURE_OMITTED:Figure 2'):
    validate_story(st,assets,root)
