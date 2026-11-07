"""dev.4: evidence-first free-layout regression, without any PFS installation."""
import json, tempfile, unittest, copy
from pathlib import Path
from PIL import Image
from pptx import Presentation
from sharepack.common import save,load,digest,ContractError
from sharepack.render import build
from sharepack.freeform import choose_composition

class FreeformRegression(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  source=self.root/'source';source.mkdir()
  kinds={'W':(840,210),'T':(260,680),'M':(600,470)}
  a=[]
  for key,xy in kinds.items():
   p=source/(key+'.png');Image.new('RGB',xy,{'W':'white','T':'gray','M':'lightblue'}[key]).save(p)
   a.append({'id':key,'figure':'Fig '+key,'path':p.name,'pdf_page':2,'sha256':digest(p),
             'source_pdf_sha256':'a'*64,'review_status':'PENDING'})
  self.assets={'contract':'sharepack-figure-assets-v1','source_pdf_sha256':'a'*64,'assets':a}
  self.ap=source/'assets.json';save(self.ap,self.assets)
  combos=[('cover',[]),('framework',[]),('finding',['W']),('method',['T']),
          ('comparison',['T','M']),('finding',['W','W']),('finding',['M']),('synthesis',[])]
  cards=[];claims=[]
  for j,(role,figures) in enumerate(combos,1):
   ident='C'+str(j)
   claims.append({'id':ident,'question':'是什么问题？','method':'实验测量和对照','observation':'实验报告了特定结果',
                  'meaning':'有限的结论','limit':'不等于全部实验情境成立', 'required':True,'source_ids':['S'],
                  'metrics':([{'label':'指标','value':'1.00→0.43','definition':'归一化相对测量','comparison':'对照组归一化为1'}]
                             if j==5 else [])})
   cards.append({'order':j,'stage':role,'title':'研究分支与关键实验'+str(j),
                 'intro':'根据已有研究结论组织，不新增实验事实。','question':'是什么问题？',
                 'method':'作者测量并比较两组现象','observation':'研究观察到具体差异。',
                 'takeaway':'仅在报告的条件下支持这一认识。','interpretation':'从有条件的实验中解释结果。',
                 'narrative_role':role,'layout_type':'evidence','claim_ids':[ident],
                 'figure_asset_ids':figures,
                 'flow_steps':['提出问题','比较设计','验证结果','综合限制']})
  self.story={'contract':'sharepack-story-v1','paper':{'title':'Test','doi':'10.1234/x','authors_short':'Author et al.'},
              'pdf_sha256':'a'*64,'profile':'standard','sources':[{'id':'S','pdf_page':2}],
              'claims':claims,'cards':cards,'review_status':'PARTIAL','formal_ready':False}
  self.sp=self.root/'story.json';save(self.sp,self.story)
 def tearDown(self):self.tmp.cleanup()
 def test_dynamic_compositions_and_all_metrics_limits(self):
  before=[digest(self.sp),digest(self.ap)]+[digest(self.ap.parent/(z['path'])) for z in self.assets['assets']]
  qa=build(self.sp,self.ap,self.root/'out',render_png=False,layout_engine='freeform')
  expected={'logic','text_synthesis','figure_hero','figure_split','figure_pair','figure_stack'}
  self.assertTrue(expected<=set(g['layout_type'] for g in qa['layout_geometry']))
  self.assertEqual(qa['layout_geometry'][4]['visible_metric_count'],1)
  self.assertTrue(all(g['visible_limit_count']==1 for g in qa['layout_geometry']))
  self.assertFalse(qa['release_ready'])
  self.assertEqual(load(self.root/'out'/'composition_plan.json')['cards'][3]['composition'],'figure_split')
  deck=Presentation(self.root/'out'/'SharePack_editable.pptx')
  self.assertEqual(len(deck.slides),8)
  self.assertEqual(sum(sh.shape_type==13 for s in deck.slides for sh in s.shapes),7)
  self.assertIn('不等于全部实验情境成立',' '.join(sh.text for sh in deck.slides[4].shapes if sh.has_text_frame))
  self.assertEqual(before,[digest(self.sp),digest(self.ap)]+[digest(self.ap.parent/(z['path'])) for z in self.assets['assets']])
  self.assertFalse(qa['static_visual_qa']['canvas_overflow'])
 def test_invalid_manual_composition_is_rejected(self):
  st=copy.deepcopy(self.story);st['cards'][2]['composition']='floating_magic'
  save(self.root/'bad.json',st)
  with self.assertRaisesRegex(ContractError,'FREEFORM_COMPOSITION_UNKNOWN'):
   build(self.root/'bad.json',self.ap,self.root/'bad_out',render_png=False,layout_engine='freeform')
 def test_legacy_still_selectable(self):
  qa=build(self.sp,self.ap,self.root/'legacy',render_png=False,layout_engine='legacy')
  self.assertEqual(qa['layout_engine'],'legacy')
  self.assertFalse((self.root/'legacy'/'composition_plan.json').exists())
 def test_long_metric_cannot_vanish(self):
  st=copy.deepcopy(self.story);st['claims'][4]['metrics'][0]['definition']='不能省略的解释'*100
  save(self.root/'bad_metric.json',st)
  with self.assertRaisesRegex(ContractError,'LAYOUT_TEXT_CAPACITY_EXCEEDED'):
   build(self.root/'bad_metric.json',self.ap,self.root/'bad_metric_out',render_png=False)

if __name__=='__main__':unittest.main()
