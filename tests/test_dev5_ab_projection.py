import copy,tempfile,unittest
from pathlib import Path
from sharepack.common import load,save,digest,ContractError
from sharepack.logic_ab import project_ab,pfs_model_snapshot
from sharepack.logic_projection import verify_projection,render
from examples.make_synthetic_pfs_ab import produce

class ResearchLogicABTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.r=Path(self.tmp.name);self.k,self.spec=produce(self.r/'sources')
  self.plan=self.r/'plans'/'projected.json'
 def tearDown(self):self.tmp.cleanup()
 def test_registered_A_core_and_B_branch_provenance(self):
  p=project_ab(self.k,self.spec,self.plan)
  self.assertEqual(p['source_kind'],'PFS_AB_RESEARCH_LOGIC_1')
  self.assertEqual(len(p['views'][0]['edges']),10)
  self.assertEqual({x['relation_id'] for x in p['views'][0]['edges']},set(load(self.k)['core']['edges']))
  self.assertTrue(verify_projection(self.plan))
 def test_missing_core_relation_is_blocked(self):
  sp=load(self.spec);sp['views'][0]['edge_ids'].remove('E4');save(self.spec,sp)
  with self.assertRaisesRegex(ContractError,'CORE_EDGE_OR_NODE_OMITTED'):
   project_ab(self.k,self.spec,self.plan)
 def test_unknown_edge_never_drawn(self):
  sp=load(self.spec);sp['views'][0]['edge_ids'].append('UNKNOWN');save(self.spec,sp)
  with self.assertRaisesRegex(ContractError,'VIEW_EDGE_INVALID'):project_ab(self.k,self.spec,self.plan)
 def test_relation_removal_or_change_invalidates_projection(self):
  project_ab(self.k,self.spec,self.plan)
  model=load(self.k);model['edges'][2]['type']='comparison';model['snapshot']=pfs_model_snapshot(model)
  save(self.k,model)
  with self.assertRaisesRegex(ContractError,'UPSTREAM_DRIFT'):verify_projection(self.plan)
 def test_input_evidence_file_changes_are_rejected(self):
  project_ab(self.k,self.spec,self.plan)
  p=Path(load(self.k)['inputs']['network']['path']);p.write_text('{}')
  with self.assertRaisesRegex(ContractError,'INPUT_SHA_DRIFT'):verify_projection(self.plan)
 def test_A_core_can_span_multiple_readable_pages_without_omitting_edges(self):
  s=load(self.spec)
  left=['Q','A1','A2','A3','A4','S'];right=['Q','B1','B2','B3','B4','S']
  edges_left=['E1','E3','E4','E5','E9'];edges_right=['E2','E6','E7','E8','E10']
  originals=s['views'][0]['nodes']
  l=[dict(n,layer=left.index(n['logic_node_id']),lane=0) for n in originals if n['logic_node_id'] in left]
  r=[dict(n,layer=right.index(n['logic_node_id']),lane=0) for n in originals if n['logic_node_id'] in right]
  s['views']=[dict(s['views'][0],id='A_left',scope='A_excerpt',nodes=l,edge_ids=edges_left),
              dict(s['views'][0],id='A_right',scope='A_excerpt',nodes=r,edge_ids=edges_right)]
  save(self.spec,s)
  p=project_ab(self.k,self.spec,self.plan)
  self.assertEqual(sum(len(v['edges']) for v in p['views']),10)
  self.assertEqual(len(p['views']),2)
 def test_A_split_missing_edge_is_blocked(self):
  s=load(self.spec); v=s['views'][0];v['scope']='A_excerpt';v['edge_ids'].remove('E10')
  save(self.spec,s)
  with self.assertRaisesRegex(ContractError,'CORE_COVERAGE_INCOMPLETE'):
   project_ab(self.k,self.spec,self.plan)
 def test_three_branch_layout_not_hardcoded_two_branch_map(self):
  m=load(self.k);m['nodes'].append({'id':'C1','kind':'finding','identity':'SCIENTIFIC_EVIDENCE',
   'short_text':'第三个独立研究分支','source_ids':['SRC-DEMO'],'review_status':'PARTIAL'})
  m['edges']+=[{'id':'E11','from':'Q','to':'C1','type':'question_fork','identity':'AUTHOR_ARGUMENT',
   'source_ids':['SRC-DEMO'],'review_status':'PARTIAL','causal_claim':False},
   {'id':'E12','from':'C1','to':'S','type':'evidence_convergence','identity':'SCIENTIFIC_EVIDENCE',
   'source_ids':['SRC-DEMO'],'review_status':'PARTIAL','causal_claim':False}]
  m['core']['nodes'].append('C1');m['core']['edges']+=['E11','E12']
  m['snapshot']=pfs_model_snapshot(m);save(self.k,m)
  spec=load(self.spec);v=spec['views'][0]
  v['nodes'].append({'logic_node_id':'C1','layer':1,'lane':2})
  v['edge_ids']+=['E11','E12'];spec['logic_sha256']=digest(self.k);save(self.spec,spec)
  p=project_ab(self.k,self.spec,self.plan)
  self.assertEqual(len(p['views'][0]['edges']),12)
  out,report=render(self.plan,self.r/'three_branch_render',pdf=False)
  from pptx import Presentation
  slide=Presentation(out).slides[0]
  self.assertIn('第三个独立研究分支',' '.join(sh.text for sh in slide.shapes if sh.has_text_frame))
 def test_unsupported_causes_cannot_be_drawn(self):
  model=load(self.k);model['edges'][0]['causal_claim']=True;model['snapshot']=pfs_model_snapshot(model)
  save(self.k,model);sp=load(self.spec);sp['logic_sha256']=digest(self.k);save(self.spec,sp)
  with self.assertRaisesRegex(ContractError,'UNSUPPORTED_CAUSAL_CLAIM'):project_ab(self.k,self.spec,self.plan)
 def test_editable_ppt_has_exact_registered_ids(self):
  project_ab(self.k,self.spec,self.plan)
  p,report=render(self.plan,self.r/'out',pdf=False)
  from pptx import Presentation
  slides=Presentation(p).slides
  self.assertEqual(len(slides),2)
  self.assertEqual(report[0]['relation_count'],10)
  tx=' '.join(sh.text for sh in slides[0].shapes if sh.has_text_frame)
  self.assertIn('共同问题',tx)
  self.assertIn('E10',tx)
  self.assertIn('研究推进',tx)
  self.assertTrue(load(self.r/'out'/'projection_render_report.json')['pfs_source_unchanged'])
 def test_renderer_can_not_claim_source_science_review(self):
  project_ab(self.k,self.spec,self.plan)
  self.assertFalse(load(self.plan)['formal_ready'])
  p,rep=render(self.plan,self.r/'out',pdf=False)
  self.assertEqual(load(self.r/'out'/'projection_render_report.json')['scientific_review'],'PENDING')
if __name__=='__main__':unittest.main()
