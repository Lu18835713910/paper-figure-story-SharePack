"""Reformat previously human-reviewed Passmore test evidence as SharePack v1.
Scientific interpretation is authored for this specific test, not an auto parser.
Run with original PDF and existing previous provenance; never distribute raw article PDF in repo.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sharepack.common import load,save

if len(sys.argv)!=4:raise SystemExit('usage: python examples/make_passmore_fixture.py OLD_STORY PRIOR_PROVENANCE OUTDIR')
old=load(sys.argv[1]);provenance=load(sys.argv[2]);out=Path(sys.argv[3]);out.mkdir(parents=True,exist_ok=True)
source_pages={'S1':1,'S2':2,'S3':3,'S4':3,'S5':4,'S6':5,'S7':5,'S8':6,'S9':6}
sources=[{'id':k,'pdf_page':source_pages[k],'section':v['section'],'figure_refs':v['figures'],
          'review_status':'DIRECT_TEXT_CHECKED_FIGURES_PARTIAL'} for k,v in old['sources'].items()]
questions=['如何从被动观察转向主动控制？','反馈回路具体怎么运行？','细胞能沿预定路径运动吗？',
           '在不同细胞和光强下轨迹是否稳定？','不同光强能否精确设定速度？','如何让三个细胞协调且避免碰撞？',
           '光照能调控蛋白在细胞核/细胞质之间的分布吗？','标准PID遇到什么问题，怎样改进？',
           '核与质控制在不同实验中是否稳定？','七个不同细胞能否接近同一核内目标？','结果能推广到所有细胞吗？']
methods=['比较智能显微镜常见采集反馈与主动光遗传干预。','实时成像、分割、与设定目标比较，调整光照。',
         '对表达TIAM1光敏构件的HT1080细胞进行轨迹追踪与空间照光。','比较循环路径、不同光强、细胞路径偏差。',
         '每个循环或半循环改变辐照度并测量相对投影速度。',
         '给三细胞不同路径，用预判碰撞与回拉策略协调照光。',
         '在U2OS-LEXY细胞中用蓝光驱动核输出并追踪荧光。',
         '比较标准PID与增益调度PID在不同强度设定点的误差。',
         '在同一细胞对核/质控制重复进行，并测量多个目标值。',
         '使用脉宽调制向七个细胞分别给光并追踪核荧光。',
         '对照两类光敏系统、细胞类型和控制边界。']
observations=['本文以主动改变生物过程作为目标。','反馈回路根据真实结果动态调整照光。',
              '个别细胞能够沿圆形路线持续迁移超过10小时。','多个细胞在控制下保持接近目标路径，但个体速度不同。',
              '相对速度能调节，但固定光强不能确保每个细胞达到相同绝对速度。',
              '三个细胞沿各自路径移动，可减速避碰；还观察到拥挤环境的细胞互相影响。',
              'LEXY蛋白的核/质荧光分布随反馈光照调整。',
              '标准PID跨强度范围出现稳态偏差，增益调度改善了控制表现。',
              '核内控制比细胞质更平滑，重复控制能接近不同设定值。',
              '七个细胞虽然需要不同光强，最终核内荧光都趋近共同目标。',
              '适用性依赖光敏构件、细胞系统、硬件和处理成本。']
meanings=['显微镜可将成像反馈用于生物干预而非只优化拍摄。',
          '控制对象是细胞行为的目标误差，而非拍摄参数。',
          '反馈定位能够持续引导部分细胞的方向与路线。',
          '位置控制对速度异质性有一定容忍度。',
          '改变光照强度不等于绝对速度可以精确控制。',
          '反馈可以协调有限数量细胞的路径与避碰。',
          '同一闭环思路可推广到亚细胞蛋白定位任务。',
          '真实细胞的非线性响应要求调整控制器参数。',
          '对不同设定点的蛋白定位控制可重复实现。',
          '不同细胞可以使用不同输入实现相似输出。',
          '这是针对特定工程化体系的概念验证。']
limits=['不能宣称此前没有任何闭环光遗传研究。','不等于通用的复杂生物过程控制。',
        '单次实例不能代表所有细胞的群体均值。','样本量及定量指标须对应各图面板。',
        '不能把相对速度变化当作绝对速度设定成功。','有限细胞数的演示不等于普遍集体迁移机制。',
        '荧光强度是读出代理，不能自动等于绝对蛋白浓度。',
        '标准PID局部小误差不能推广为全工作区间。','不同控制器及测量空间的噪声不同。',
        '七细胞共享目标并不表示给予同一剂量光。','不能推断所有细胞、所有组织或三维体系都有效。']
metric_map={
'C03':[{'label':'单细胞路径','value':'>10小时','definition':'示例细胞持续跟随路线的时间','comparison':'预设圆形路径，非总体平均持续时长'}],
'C04':[{'label':'路径偏差','value':'5 µm以内','definition':'目标轨迹与细胞中心的距离','comparison':'多个细胞的路径控制，不是平均误差'}],
'C06':[{'label':'同步控制','value':'3个细胞','definition':'分别跟踪并主动调光的细胞数','comparison':'独立路径及主动避碰演示'}],
'C08':[{'label':'局部PID误差','value':'<10%','definition':'测得荧光强度相对设定值偏差','comparison':'仅针对部分标准PID条件，不是全强度范围'}],
'C10':[{'label':'单独反馈','value':'7个细胞','definition':'用不同光强分别调控的细胞数','comparison':'同一目标核内荧光，而非同一光照剂量'}]}
claims=[]
for i,c in enumerate(old['claims']):
    cid=c['id'];claims.append({'id':cid,'question':questions[i],'method':methods[i],
    'observation':observations[i],'meaning':meanings[i],'limit':limits[i],
    'source_ids':c['sources'],'review_status':'PARTIAL','required':True,
    'metrics':metric_map.get(cid,[])})

def card(order,stage,title,intro,claim_ids,figures,method,observation,takeaway,flow=None):
    c={'order':order,'stage':stage,'title':title,'intro':intro,'claim_ids':claim_ids,
    'figure_asset_ids':figures,'method':method,'observation':observation,
    'interpretation':takeaway,'takeaway':takeaway,
    'question':questions[int(claim_ids[0][1:])-1]}
    if flow:c['flow_steps']=flow
    return c
cards=[
card(1,'研究问题 / COVER','显微镜不只观察：还能按目标控制细胞','目标驱动显微镜把实时分析与光遗传干预连成闭环。',['C01','C02'],[],
     '实时拍摄细胞，计算实际状态与目标的偏差，再调整照光。','作者搭建了一套能反馈调节生物过程的显微镜平台。','研究核心是“看见偏差，再改变干预”。',['拍摄','分析','比较目标','调整光照']),
card(2,'背景与问题 / FIGURE 1','为什么仅靠自动拍摄还不够？','从优化成像转向主动改变细胞行为，是论文的研究起点。',['C01','C02'],['F1b'],
     '用空间光调制器更新照光位置与强度，连续采集并纠偏。','同一套闭环可将细胞实际反馈转化为下一次光照控制。','研究目标从“拍得好”发展为“细胞接近设定目标”。'),
card(3,'全文框架 / STORY MAP','作者如何逐步验证闭环控制？','围绕运动和蛋白定位两条分支测试共同的反馈原理。',['C02','C03','C07'],[],
     '研究线A关注运动路径；研究线B关注蛋白核/质转运。','两类不同的细胞过程都能由测量—比较—调光流程驱动。','两条研究线是互补证据，不等于实际实验的时间先后。',['建立反馈','细胞运动','核/质定位','整合证据']),
card(4,'发现一 / FIGURE 1','细胞真的能沿着指定路线走吗？','HT1080细胞的光敏系统允许研究者改变细胞的迁移方向。',['C03','C04'],['F1c','F1ef'],
     '用追踪算法检测细胞中心，再实时调整照光区域。','单细胞示例沿圆形路径运行超过10小时；群体偏差较小。','反馈控制可保持位置接近路线，但单个例子不代表总体。'),
card(5,'发现二 / FIGURE 1','调整光强，能准确控制走路速度吗？','研究者让细胞沿圆形轨道运动，逐圈改变照光强度。',['C05'],['F1g','F1hi'],
     '比较不同辐照度下的相对运动速度及初始速度差异。','光强能让细胞加速或减速，却难统一设定绝对速度。','位置控制有效，并不等于速度控制已被彻底解决。'),
card(6,'发现三 / FIGURE 2','三个细胞同时移动，怎样避免碰撞？','研究从单细胞扩展到多细胞不同路径的同步控制。',['C06'],['F2ab','F2c'],
     '分别追踪三细胞，预测相撞风险后调整照光方向。','细胞可以独立移动并减速避碰；拥挤场景显示相互影响。','验证了有限规模的协调能力，不能据此宣称普遍机制。'),
card(7,'研究转折 / FIGURE 3','细胞内蛋白也能按设定值调整吗？','研究从移动整个细胞转向改变蛋白的核/质定位。',['C07','C08'],['F3ab'],
     '用LEXY系统和PID反馈，根据荧光偏差持续调整蓝光。','可以调节核/质荧光，但基础PID在一些区间出现偏差。','出现新问题：相同控制参数不能适应所有细胞状态。'),
card(8,'方法改进 / FIGURE 3','换一种PID，能让蛋白控制更稳定吗？','作者针对非线性与细胞间差异加入增益调度。',['C08','C09'],['F3cd','F3fg'],
     '按目标强度范围优化PID增益，并测试核与质控制。','改进后的控制在多设定点更稳定，核内示例持续约两小时。','关键贡献不只是会调光，而是根据细胞响应调整控制。'),
card(9,'跨细胞验证 / FIGURE 4','七个细胞不同，也能达到同一个目标？','每个细胞表达量不同，统一给光未必得到统一结果。',['C10'],['F4ab'],
     '使用脉宽调制分别控制七个细胞的光强并测量核荧光。','七细胞接受不同光强，核荧光却能趋向共同设定值。','相同目标不要求相同输入，这体现了反馈的实际价值。'),
card(10,'全文结论 / SYNTHESIS','论文真正证明了什么，还有哪些边界？','回到最初的科学问题：显微镜能否主动引导细胞？',['C11','C05','C08'],[],
     '整合运动控制、蛋白定位、个体差异和多细胞反馈证据。','在特定光敏工程化细胞中完成了目标驱动控制的概念验证。','不能推断任意细胞、组织或生物过程都能精准控制。',['直接观察','证据支持','重要限制','未来验证'])]
story={'contract':'sharepack-story-v1','origin':'DIRECT_PDF_AGENT_REVIEWED_PARTIAL',
 'paper':{'title':old['paper']['title'],'authors_short':'Passmore et al.',
          'journal':'Nature Communications 17:1087 (2026)','doi':old['paper']['doi']},
 'pdf_sha256':provenance['pdf_sha256'],'profile':'standard','review_status':'PARTIAL',
 'formal_ready':False,'sources':sources,'claims':claims,'cards':cards,
 'warning':'Card text was manually prepared from the current article and prior retest; not a general automatic model.'}
save(out/'passmore_reviewed_story.json',story)
# Reuse the 12 previously tested full-page-point coordinates; remove unrelated hardcoded PDF path.
regions={'source_pdf_sha256':provenance['pdf_sha256'],'regions':[
 {'id':a['id'],'figure':a['figure'],'pdf_page':a['pdf_page'],'crop_pdf_pt':a['crop_pdf_pt'],
 'review_status':'PENDING','license_note':'Passmore et al. 2026 CC BY 4.0; derivative panel crop'}
 for a in provenance['panels']]}
save(out/'passmore_regions.json',regions)
print('fixture',len(claims),'claims',len(cards),'cards',len(regions['regions']),'regions')
