"""Generate a fictional, video-friendly EvidenceWeave demo case."""
import json
from pathlib import Path
import pymupdf as fitz

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "benchmark" / "video_demo_case"

RECORDS = [
    ("01_陈某_第一次讯问", "被讯问人", "陈某", "2026-08-14", [
        ("c1_presence", "问：案发当晚你是否进入锦庭酒店？", "答：2026年8月12日21时左右，我没有进入锦庭酒店。"),
        ("c1_cash", "问：你是否收取过赵某交付的现金？", "答：2026年8月12日21时20分，我没有在锦庭酒店收取赵某支付的任何现金。"),
        ("c1_contact", "问：当晚此前你是否联系赵某约见？", "答：2026年8月12日19时30分，我没有通过聊天软件联系赵某约定见面。"),
    ]),
    ("02_陈某_第二次讯问", "被讯问人", "陈某", "2026-08-16", [
        ("c2_presence", "问：你是否去过锦庭酒店？", "答：2026年8月12日21时10分左右，我进入了锦庭酒店。"),
        ("c2_cash", "问：赵某是否给过你现金？", "答：2026年8月12日21时20分，我没有在锦庭酒店收取赵某支付的任何现金。"),
        ("c2_bag", "问：你离开时手里的黑色袋子从哪里来？", "答：2026年8月12日21时20分，我在锦庭酒店从赵某处拿走一个黑色文件袋，里面是合同材料。"),
    ]),
    ("03_陈某_第三次讯问", "被讯问人", "陈某", "2026-08-19", [
        ("c3_presence", "问：请再次说明你到酒店的时间。", "答：2026年8月12日21时05分左右，我进入锦庭酒店808房间。"),
        ("c3_cash", "问：你是否收取赵某现金？", "答：2026年8月12日21时20分，我在锦庭酒店收取赵某交付的八万元现金。"),
        ("c3_depart", "问：你何时离开？", "答：2026年8月12日21时35分左右，我离开锦庭酒店。"),
    ]),
]
RECORDS += [
    ("04_赵某_第一次讯问", "被讯问人", "赵某", "2026-08-15", [
        ("z1_presence", "问：你是否见到陈某进入酒店？", "答：2026年8月12日21时10分，我亲眼看见陈某进入锦庭酒店。"),
        ("z1_cash", "问：当晚是否有现金交付？", "答：2026年8月12日21时20分，陈某在锦庭酒店收取了我支付的十万元现金。"),
    ]),
    ("05_赵某_第二次讯问", "被讯问人", "赵某", "2026-08-18", [
        ("z2_cash", "问：请确认当晚现金数额。", "答：2026年8月12日21时20分，陈某在锦庭酒店收取了我支付的八万元现金，这就是当晚唯一的一笔现金交付。"),
        ("z2_bag", "问：现金如何交付？", "答：2026年8月12日21时20分，我把装有现金的黑色文件袋交给陈某。"),
    ]),
    ("06_刘某_证人证言", "证人", "刘某", "2026-08-15", [
        ("l1_presence", "问：你在酒店门口看到了什么？", "答：2026年8月12日21时05分左右，我亲眼看见陈某进入锦庭酒店。"),
        ("l1_cash_unknown", "问：你是否看到陈某收钱？", "答：2026年8月12日21时20分，我没有看见陈某是否收取现金，不能确认其是否收款。"),
    ]),
    ("07_孙某_证人证言", "证人", "孙某", "2026-08-17", [
        ("s1_hearsay", "问：你为何知道现金交付一事？", "答：赵某告诉我，2026年8月12日21时20分陈某在锦庭酒店收取了十万元现金。"),
        ("s1_other", "问：你本人当晚是否在场？", "答：2026年8月12日21时20分，我没有进入锦庭酒店。"),
    ]),
]
RECORDS += [
    ("08_锦庭酒店监控摘要", None, None, "2026-08-20", [
        ("camera_in", "", "监控画面显示：2026年8月12日21时06分，陈某进入锦庭酒店。"),
        ("camera_out", "", "监控画面显示：2026年8月12日21时34分，陈某离开锦庭酒店，右手持有黑色文件袋。"),
    ]),
    ("09_聊天记录摘要", None, None, "2026-08-20", [
        ("chat_contact", "", "2026年8月12日19时32分，陈某通过聊天软件联系赵某，发送内容为“21点，老地方见，材料带上”。"),
        ("chat_reply", "", "2026年8月12日19时34分，赵某通过聊天软件联系陈某，回复内容为“好，我准时到”。"),
    ]),
    ("10_网约车行程摘要", None, None, "2026-08-20", [
        ("ride_arrive", "", "网约车订单显示：2026年8月12日20时58分，陈某到达锦庭酒店东门。"),
        ("ride_leave", "", "网约车订单显示：2026年8月12日21时40分，陈某从锦庭酒店东门乘车离开。"),
    ]),
    ("11_银行交易摘要", None, None, "2026-08-20", [
        ("bank_withdraw", "", "银行记录显示：2026年8月12日18时05分，赵某账户取现100000元。"),
        ("bank_nextday", "", "银行记录显示：2026年8月13日10时15分，陈某账户收到赵某账户转入100000元，摘要为咨询费。"),
    ]),
]

LABELS = [
    ("c1_presence", "c2_presence", "CONTRADICTS", "陈某前后供述对是否进入酒店直接冲突"),
    ("c1_presence", "camera_in", "CONTRADICTS", "本人否认进入与监控记录冲突"),
    ("c2_presence", "z1_presence", "SUPPORTS", "本人供述与赵某目击陈述相互印证"),
    ("c3_presence", "camera_in", "SUPPORTS", "进入时间接近且地点一致"),
    ("c1_cash", "c3_cash", "CONTRADICTS", "陈某由否认收款变为承认收取八万元"),
    ("c1_cash", "z1_cash", "CONTRADICTS", "本人否认与交付方肯定陈述冲突"),
    ("c3_cash", "z2_cash", "SUPPORTS", "双方均称八万元现金"),
    ("z1_cash", "z2_cash", "CONTRADICTS", "同一唯一现金交付的金额十万元与八万元互斥"),
    ("l1_cash_unknown", "z1_cash", "INDEPENDENT", "证人未看到不等于否认发生"),
    ("c1_contact", "chat_contact", "CONTRADICTS", "否认联系与聊天记录直接冲突"),
]
def add_textbox(page, rect, text, size=12):
    rc = page.insert_textbox(rect, text, fontname="china-s", fontsize=size, lineheight=1.55)
    if rc < 0:
        raise RuntimeError(f"text overflow: {text[:30]}")

def generate():
    OUT.mkdir(parents=True, exist_ok=True)
    statements = {}
    for idx, (name, role, person, day, items) in enumerate(RECORDS):
        pdf = fitz.open()
        p1 = pdf.new_page()
        header = [
            "EvidenceWeave 视频演示测试材料",
            name,
            "本材料完全虚构，仅用于软件功能测试与比赛演示。",
            f"记录日期：{day}",
        ]
        if person:
            header.insert(3, f"{role}：{person}")
        header.append("案件相关人员：陈某、赵某、刘某、孙某。")
        add_textbox(p1, fitz.Rect(55, 70, 540, 500), "\n".join(header), 14)

        p2 = pdf.new_page()
        y = 65
        for key, question, answer in items:
            text = (question + "\n" if question else "") + answer
            add_textbox(p2, fitz.Rect(55, y, 540, y + 120), text, 12)
            y += 135
            statements[key] = {
                "document": name + ".pdf",
                "page": 2,
                "quote": answer,
                "source_person": person,
            }
        pdf.save(OUT / (name + ".pdf"))
        pdf.close()

    gold = {
        "synthetic": True,
        "description": "完全虚构的视频演示样例；人工设计预期关系，不代表真实案件或法律结论。",
        "target_person": "陈某",
        "statements": statements,
        "labels": [
            {"a": a, "b": b, "relation_type": r, "reason": reason}
            for a, b, r, reason in LABELS
        ],
    }
    (OUT / "gold_labels.json").write_text(
        json.dumps(gold, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Generated {len(RECORDS)} PDFs and {len(LABELS)} gold pairs in {OUT}")

if __name__ == "__main__":
    generate()
