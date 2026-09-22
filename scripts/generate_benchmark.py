"""Generate fictional Chinese PDFs and hand-authored relation labels; no client data."""
import json
from pathlib import Path
import pymupdf as fitz

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'benchmark/synthetic_case'
RECORDS=[
 ('01_张某_第一次讯问','张某','2026-03-20',[
  ('z1_presence','2026年3月17日21时，我没有进入鑫源宾馆。'),
  ('z1_bag','2026年3月17日21时，我没有在鑫源宾馆向李某交付黑色手提袋。')]),
 ('02_张某_第二次讯问','张某','2026-03-22',[
  ('z2_presence','2026年3月17日21时，我进入了鑫源宾馆。'),
  ('z2_bag','2026年3月17日21时，我没有在鑫源宾馆向李某交付黑色手提袋。')]),
 ('03_张某_第三次讯问','张某','2026-03-25',[
  ('z3_presence','2026年3月17日21时30分左右，我进入了鑫源宾馆。'),
  ('z3_bag','2026年3月17日21时，我在鑫源宾馆向李某交付了黑色手提袋。')]),
 ('04_张某_第四次讯问','张某','2026-03-27',[
  ('z4_presence','2026年3月17日21时左右，我进入了鑫源宾馆。'),
  ('z4_bag','2026年3月17日21时，我在鑫源宾馆向李某交付了黑色手提袋。')]),
 ('05_李某_第一次讯问','李某','2026-03-20',[
  ('l1_bag','2026年3月17日21时，张某在鑫源宾馆向李某交付了黑色手提袋。'),
  ('l1_money','2026年3月17日22时，张某在鑫源宾馆收取了李某支付的十万元现金。')]),
 ('06_李某_第二次讯问','李某','2026-03-24',[
  ('l2_bag','2026年3月17日21时，张某在鑫源宾馆向李某交付的唯一手提袋是红色的。'),
  ('l2_money','2026年3月17日22时，张某在鑫源宾馆收取了李某支付的八万元现金，这就是当晚唯一的一笔现金交付。')]),
 ('07_李某_第三次讯问','李某','2026-03-26',[
  ('l3_money','2026年3月17日晚，张某在鑫源宾馆没有收取李某的任何现金。'),
  ('l3_meeting','2026年3月17日22时，张某在鑫源宾馆参与了项目商议。')]),
 ('08_王某_第一次讯问','王某','2026-03-21',[
  ('w1_presence','2026年3月17日21时，我亲眼看见张某进入鑫源宾馆。'),
  ('w1_meeting','2026年3月17日22时，张某没有在鑫源宾馆参与项目商议。')]),
 ('09_王某_第二次讯问','王某','2026-03-24',[
  ('w2_presence','2026年3月17日20时40分左右，我亲眼看见张某进入鑫源宾馆。'),
  ('w2_meeting','2026年3月17日22时，张某在鑫源宾馆参与了项目商议。')]),
 ('10_王某_第三次讯问','王某','2026-04-03',[
  ('w3_hearsay','李某告诉我，2026年3月17日21时张某在鑫源宾馆向李某交付了黑色手提袋。'),
  ('w3_other','2026年4月1日21时，我看见张某进入鑫源宾馆。')]),
 ('11_赵某_第一次讯问','赵某','2026-03-22',[
  ('r1_money','2026年3月17日22时，张某在鑫源宾馆收取了李某支付的100000元现金。'),
  ('r1_bag','2026年3月17日21时，张某在鑫源宾馆向李某交付了黑色手提袋。')]),
 ('12_赵某_第二次讯问','赵某','2026-03-28',[
  ('r2_money','2026年3月17日22时，张某在鑫源宾馆收取了李某支付的八万元现金，这就是当晚唯一的一笔现金交付。'),
  ('r2_recipient','2026年3月17日21时，张某在鑫源宾馆交付的唯一黑色手提袋，其接收人是钱某，不是李某。')]),
 ('13_周某_证人证言','周某','2026-03-21',[
  ('p_presence','2026年3月17日21时，我亲眼看见张某进入鑫源宾馆。'),
  ('p_other','2026年4月2日21时，我亲眼看见张某进入鑫源宾馆。')]),
 ('14_吴某_证人证言','吴某','2026-03-23',[
  ('u_unknown','2026年3月17日21时，我没有注意到张某是否进入鑫源宾馆，不能确认其是否进入。'),
  ('u_bag','2026年3月17日21时，我亲眼看见张某在鑫源宾馆向李某交付了黑色手提袋。')]),
 ('15_银行流水摘要',None,'2026-03-29',[
  ('bank','2026年3月18日10时，张某账户收到李某账户转入的100000元，摘要为货款。')]),
 ('16_监控摘要',None,'2026-03-29',[
  ('camera','监控画面显示：2026年3月17日21时，张某进入鑫源宾馆。')]),
 ('17_聊天记录摘要',None,'2026-03-29',[
  ('chat','2026年3月19日10时，张某通过聊天软件联系孙某，商议购买电脑。'),
  ('chat2','2026年3月19日11时，孙某通过聊天软件联系钱某，商议购买电脑。')]),
]
LABELS=[
 ('z1_presence','z2_presence','CONTRADICTS','同一时间地点，进入与未进入'),
 ('z1_presence','w1_presence','CONTRADICTS','本人否认与目击陈述'),
 ('z1_presence','camera','CONTRADICTS','否认进入与监控记录'),
 ('z1_bag','z3_bag','CONTRADICTS','同一交付行为的前后变化'),
 ('z2_bag','l1_bag','CONTRADICTS','否认与接收方肯定'),
 ('l1_money','l3_money','CONTRADICTS','现金收款与完全否认'),
 ('r1_money','l3_money','CONTRADICTS','现金收款与完全否认'),
 ('w1_meeting','w2_meeting','CONTRADICTS','同一人员改变商议陈述'),
 ('w1_meeting','l3_meeting','CONTRADICTS','同一商议是否参与'),
 ('l1_bag','l2_bag','CONTRADICTS','唯一手提袋颜色互斥'),
 ('z2_presence','w1_presence','SUPPORTS','进入时间地点一致'),
 ('z4_presence','camera','SUPPORTS','约九点与监控九点一致'),
 ('z3_bag','z4_bag','SUPPORTS','交付对象物品时间一致'),
 ('l1_money','r1_money','SUPPORTS','十万元等于100000元'),
 ('z2_bag','z1_bag','SUPPORTS','两次均否认同一交付'),
 ('w1_presence','w2_presence','PARTIAL_DIFFERENCE','相差20分钟的近似到达时间'),
 ('z3_presence','z4_presence','PARTIAL_DIFFERENCE','九点半左右与九点左右'),
 ('w3_other','p_other','INDEPENDENT','同地点但不同日期'),
 ('l1_money','bank','INDEPENDENT','次日货款转账不等于前一晚现金'),
 ('u_unknown','camera','INDEPENDENT','未注意不等于否认发生，无法确认属于相反陈述'),
]

def generate():
    OUT.mkdir(parents=True,exist_ok=True); statements={}
    for index,(name,person,day,items) in enumerate(RECORDS):
        pdf=fitz.open(); page=pdf.new_page()
        role='证人' if index in (12,13) else '被讯问人'
        header=f'EvidenceWeave 合成测试材料\n{name}\n本材料完全虚构，仅用于软件测试。\n'
        if person: header+=f'{role}：{person}\n'
        header+=f'记录日期：{day}\n案件被告人：张某、李某、王某、赵某、孙某。\n'
        page.insert_textbox(fitz.Rect(48,65,547,450),header,fontname='china-s',fontsize=14,lineheight=1.7)
        page=pdf.new_page()
        body='\n\n'.join(quote for _,quote in items)
        page.insert_textbox(fitz.Rect(48,80,547,650),body,fontname='china-s',fontsize=14,lineheight=1.8)
        pdf.save(OUT/(name+'.pdf'));pdf.close()
        for key,quote in items: statements[key]={'document':name+'.pdf','page':2,'quote':quote,'source_person':person}
    gold={'synthetic':True,'description':'全部虚构，人工设计的固定评价集；不是法律结论。','persons':{'defendants':['张某','李某','王某','赵某','孙某'],'witnesses':['周某','吴某'],'others':['钱某']},
          'statements':statements,'labels':[{'a':a,'b':b,'relation_type':r,'reason':reason} for a,b,r,reason in LABELS]}
    (OUT/'gold_labels.json').write_text(json.dumps(gold,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'Generated {len(RECORDS)} PDFs, {len(LABELS)} gold pairs')

if __name__=='__main__': generate()
