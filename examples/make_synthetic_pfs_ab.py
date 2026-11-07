"""SYNTHETIC test-only A/B relationships, NOT a real PFS run or source-verified graph."""
from pathlib import Path
import json,hashlib,sys
from sharepack.common import save,digest
from sharepack.logic_ab import pfs_model_snapshot

def produce(out):
 out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
 network=save(out/'evidence_network.json',{'version':'pfs-evidence-network-1','snapshot':'SYNTHETIC_NETWORK_ONLY','paper':{'paper_type':'original_research'},'nodes':[],'edges':[]})
 scientific=save(out/'scientific_index.json',{'version':'pfs-scientific-index-1','status':'SYNTHETIC_ONLY'})
 nodes=[
 ('Q','question','共同问题：闭环能否主动控制细胞？'),
 ('A1','method','迁移控制：沿设定路径引导细胞'),
 ('B1','method','核质控制：反馈调节蛋白定位'),
 ('A2','finding','细胞能够长时程沿路径移动'),
 ('B2','finding','初始PID控制出现稳态偏移'),
 ('A3','finding','位置可控，但速度目标受限'),
 ('B3','method','改用增益调度优化反馈'),
 ('A4','finding','多细胞避碰实验进一步扩展'),
 ('B4','finding','核内滴定与七细胞反馈得到验证'),
 ('S','synthesis','不同过程可用反馈，但各有边界')]
 n=[{'id':i,'kind':k,'identity':'SCIENTIFIC_EVIDENCE','short_text':v,'title':v,'source_ids':['SRC-DEMO'],
    'source_entity_ids':[],'statement_ids':[],'field_bindings':[],'review_status':'PARTIAL'} for i,k,v in nodes]
 rel=[('E1','Q','A1','question_fork','AUTHOR_ARGUMENT'),('E2','Q','B1','question_fork','AUTHOR_ARGUMENT'),
      ('E3','A1','A2','progression','AUTHOR_ARGUMENT'),('E4','A2','A3','progression','AUTHOR_ARGUMENT'),
      ('E5','A3','A4','progression','AUTHOR_ARGUMENT'),('E6','B1','B2','progression','AUTHOR_ARGUMENT'),
      ('E7','B2','B3','progression','AUTHOR_ARGUMENT'),('E8','B3','B4','progression','AUTHOR_ARGUMENT'),
      ('E9','A4','S','evidence_convergence','SCIENTIFIC_EVIDENCE'),('E10','B4','S','evidence_convergence','SCIENTIFIC_EVIDENCE')]
 e=[{'id':i,'from':f,'to':t,'type':typ,'identity':ident,'source_ids':['SRC-DEMO'],'review_status':'PARTIAL','causal_claim':False} for i,f,t,typ,ident in rel]
 m={'version':'pfs-research-logic-1','snapshot':'','network_snapshot':'SYNTHETIC_NETWORK_ONLY','formal_ready':False,
  'inputs':{'network':{'path':str(network),'sha256':digest(network)},'scientific_index':{'path':str(scientific),'sha256':digest(scientific)}},
  'sources':{'SRC-DEMO':{'status':'SYNTHETIC_NO_ORIGINAL_SCIENCE_SOURCE'}},'nodes':n,'edges':e,
  'branches':[{'id':'branch_B','title':'亚细胞控制','nodes':['Q','B1','B2','B3','B4','S'],
      'edges':['E2','E6','E7','E8','E10']}],
  'core':{'nodes':[x[0] for x in nodes],'edges':[x[0] for x in rel]},'method_explanations':[]}
 m['snapshot']=pfs_model_snapshot(m)
 kp=save(out/'SYNTHETIC_research_logic.json',m)
 layout={'Q':(0,0),'A1':(1,0),'B1':(1,1),'A2':(2,0),'B2':(2,1),
   'A3':(3,0),'B3':(3,1),'A4':(4,0),'B4':(4,1),'S':(5,0)}
 spec={'contract':'sharepack-pfs-ab-view-v1','logic_sha256':digest(kp),
  'views':[{'id':'A','scope':'A','title':'全文科研逻辑：两个任务如何共同回答问题？',
    'question':'用实时反馈控制细胞运动与蛋白定位，哪些结论有证据、哪些有限制？',
    'note':'测试示意：关系ID为人工合成，不是实际PFS v1.1.1的A/B模型。',
    'nodes':[{'logic_node_id':i,'layer':layout[i][0],'lane':layout[i][1]} for i,_,_ in nodes],
    'edge_ids':[r[0] for r in rel]},
    {'id':'branch_B','scope':'branch','branch_id':'branch_B',
    'title':'局部科研推理：为什么调整PID控制策略？',
    'question':'基础PID出现稳态偏移后，作者如何修改方法并进一步验证？',
    'note':'测试示意：展示真实逻辑关系类型的排版能力，未核验原模型。',
    'nodes':[{'logic_node_id':i,'layer':j,'lane':0} for j,i in enumerate(['Q','B1','B2','B3','B4','S'])],
    'edge_ids':['E2','E6','E7','E8','E10']}]}
 sp=save(out/'SYNTHETIC_view_spec.json',spec)
 return kp,sp

if __name__=='__main__':
 produce(sys.argv[1])
