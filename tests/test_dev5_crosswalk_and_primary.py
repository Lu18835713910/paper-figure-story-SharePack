import tempfile,unittest,subprocess,sys
from pathlib import Path
from PIL import Image
from sharepack.common import save,load,digest,ContractError
from sharepack.pfs_adapter import bridge,import_assets,verify_bridge_context

class PFSOfficialFigureAndPrimaryTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.r=Path(self.tmp.name);p=self.r/'pfs';p.mkdir()
  Image.new('RGB',(400,260),'white').save(p/'exact.png')
  self.model={'schema_version':'1.1','document_registry':[{'id':'D','role':'main_paper','sha256':'d'*64,'format':'pdf'}],
   'entities':[{'id':'M','kind':'method'},{'id':'E','kind':'evidence'}],
   'figures':[{'id':'FIG1','document_id':'D','kind':'main'}],
   'stories':[{'id':'RS1','figure_refs':['FIG1'],'method_ids':['M'],'evidence_ids':['E'],'question_or_purpose':'question','finding_or_argument':'result'}],
   'relations':[]}
  self.k=save(p/'knowledge.json',self.model)
  self.a=save(p/'figure_assets.json',{'version':'pfs-figure-assets-1','assets':[
    {'id':'crop_001','path':'exact.png','sha256':digest(p/'exact.png'),'source_pdf_sha256':'d'*64,'physical_page':3,'bbox_pt':[40,50,400,310], 'visual_status':'PENDING'}]})
  self.x=save(p/'crosswalk.json',{'contract':'sharepack-pfs-asset-crosswalk-v1','knowledge_sha256':digest(self.k),
    'asset_manifest_sha256':digest(self.a),'mapping':[{'asset_id':'crop_001','figure_id':'FIG1','source_document_id':'D','evidence_ids':['E']}]})
 def tearDown(self):self.tmp.cleanup()
 def test_requires_crosswalk_instead_of_guessing_filename(self):
  with self.assertRaisesRegex(ContractError,'FIGURE_ID_REQUIRED_CROSSWALK'):
   bridge(self.k,self.r/'bad',self.a)
 def test_main_paper_crosswalk_import_and_original_sha_unchanged(self):
  originals=[digest(self.k),digest(self.a),digest(self.x)]
  path,ctx=bridge(self.k,self.r/'context',self.a,self.x)
  self.assertEqual(ctx['documents'][0]['role'],'main_paper')
  self.assertEqual(ctx['asset_summary']['source_asset_contract'],'pfs-figure-assets-1')
  verify_bridge_context(path)
  a=import_assets(self.k,self.a,self.r/'imported',self.x)
  self.assertEqual(a['assets'][0]['figure'],'FIG1')
  self.assertEqual(a['assets'][0]['pfs_evidence_ids'],['E'])
  self.assertEqual([digest(self.k),digest(self.a),digest(self.x)],originals)
 def test_crosswalk_sha_rejected(self):
  model=load(self.x);model['knowledge_sha256']='0'*64;save(self.x,model)
  with self.assertRaisesRegex(ContractError,'CROSSWALK_KNOWLEDGE_DRIFT'):
   bridge(self.k,self.r/'bad',self.a,self.x)
 def test_crosswalk_evidence_mismatch_rejected(self):
  model=load(self.x);model['mapping'][0]['evidence_ids']=['NO_SUCH_EVIDENCE'];save(self.x,model)
  with self.assertRaisesRegex(ContractError,'ASSET_EVIDENCE_STORY_MISMATCH'):
   bridge(self.k,self.r/'bad',self.a,self.x)
 def test_official_script_accepts_main_paper(self):
  entry=Path(__file__).resolve().parents[1]/'scripts'/'verify_real_pfs_bridge.py'
  story=save(self.r/'A_inputs'/'A_story.json',{'pdf_sha256':'d'*64})
  res=subprocess.run([sys.executable,str(entry),'--sharepack-src',str(entry.parent.parent),
   '--knowledge',str(self.k),'--pfs-assets',str(self.a),'--figure-crosswalk',str(self.x),
   '--independent-story',str(story),'--outdir',str(self.r/'results'/'workbuddy')],capture_output=True,text=True)
  self.assertEqual(res.returncode,0,res.stderr+res.stdout)
  self.assertTrue(load(self.r/'results'/'workbuddy'/'real_pfs_bridge_report.json')['same_primary_pdf_sha'])
if __name__=='__main__':unittest.main()
