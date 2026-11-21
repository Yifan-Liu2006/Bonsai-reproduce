r"""Rewrite parts 3 and 4 of the class deck with our own reproduction results.

Reads  ../../Bonsai_课堂汇报.pptx   (the team deck, never modified)
Writes ../../Bonsai_课堂汇报_v2.pptx

The deck's content slides share a fixed "furniture" (shape ids 2-7): header
label, bottom rule, title, title rule, source line, page number.  Everything
with id >= 9 is content and gets rebuilt, so the visual language (Microsoft
YaHei, #A20000 red, #287D79 teal, #252525 ink, #737373 grey) is preserved.

Run:  PYTHONPATH=. python experiment/rewrite_deck.py
"""

from __future__ import annotations

import copy
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

REPO = Path(__file__).resolve().parents[1]
SRC = REPO.parent / "Bonsai_课堂汇报.pptx"
DST = REPO.parent / "Bonsai_课堂汇报_v2.pptx"
FIG = REPO / "results" / "figures"

FONT = "Microsoft YaHei"
RED = RGBColor(0xA2, 0x00, 0x00)
TEAL = RGBColor(0x28, 0x7D, 0x79)
INK = RGBColor(0x25, 0x25, 0x25)
GREY = RGBColor(0x73, 0x73, 0x73)

FURNITURE = {2, 3, 4, 5, 6, 7}


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def by_id(slide, sid: int):
    for sh in slide.shapes:
        if sh.shape_id == sid:
            return sh
    raise KeyError(f"shape {sid} not on slide")


def set_text(shape, text: str) -> None:
    """Replace a text frame's content, keeping the first run's formatting."""
    tf = shape.text_frame
    p0 = tf.paragraphs[0]
    if not p0.runs:
        p0.add_run().text = ""

    # drop every pre-existing paragraph except the first one
    for extra in tf.paragraphs[1:]:
        extra._p.getparent().remove(extra._p)

    lines = text.split("\n")
    # clone the original paragraph so every additional line keeps its style
    for _ in lines[1:]:
        p0._p.getparent().append(copy.deepcopy(p0._p))

    for i, line in enumerate(lines):
        para = tf.paragraphs[i]
        for r in para.runs[1:]:
            r._r.getparent().remove(r._r)
        para.runs[0].text = line


def clear_content(slide) -> None:
    for sh in list(slide.shapes):
        if sh.shape_id not in FURNITURE:
            sh._element.getparent().remove(sh._element)


def add_text(slide, x, y, w, h, text, size=14, bold=False, color=INK,
             align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, spacing=1.0):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0)
    tf.margin_top = tf.margin_bottom = Inches(0)
    tf.vertical_anchor = anchor
    for i, line in enumerate(text.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = spacing
        run = p.add_run()
        run.text = line
        f = run.font
        f.name = FONT
        f.size = Pt(size)
        f.bold = bold
        f.color.rgb = color
    return tb


def add_block(slide, x, y, w, head, body, head_size=15, body_size=12.5, h=1.15):
    add_text(slide, x, y, w, 0.34, head, size=head_size, bold=True, color=RED)
    add_text(slide, x, y + 0.40, w, h - 0.40, body, size=body_size, color=GREY,
             spacing=1.15)


def set_notes(slide, text: str) -> None:
    slide.notes_slide.notes_text_frame.text = text


def add_fig(slide, name, x, y, w):
    return slide.shapes.add_picture(str(FIG / name), Inches(x), Inches(y), width=Inches(w))


def kicker(slide, text, color=RED):
    add_text(slide, 0.94, 1.66, 11.4, 0.42, text, size=19, bold=True, color=color,
             anchor=MSO_ANCHOR.MIDDLE)


def conclusion(slide, text):
    add_text(slide, 0.68, 6.62, 11.9, 0.42, text, size=17.5, bold=True, color=RED,
             anchor=MSO_ANCHOR.MIDDLE)


# --------------------------------------------------------------------------- #
# slide rewrites
# --------------------------------------------------------------------------- #
def slide15(prs):
    s = prs.slides[14]
    clear_content(s)
    set_text(by_id(s, 4), "复现范围：两个数据集，三个预算，五个种子")
    set_text(by_id(s, 6), "来源：results/*.csv；论文 §4.1 的字节预算定义")

    kicker(s, "先对齐口径，再谈差距")

    for x, num, lab, col in [(0.94, "2", "数据集", RED),
                             (5.00, "3", "字节预算", TEAL),
                             (9.06, "5", "训练种子", RED)]:
        add_text(s, x, 2.20, 3.1, 1.0, num, size=62, bold=True, color=col)
        add_text(s, x + 0.06, 3.36, 3.2, 0.44, lab, size=22, color=INK)

    add_text(s, 0.94, 4.28, 5.2, 0.55, "Cora / Citeseer", size=27, bold=True, color=RED)
    add_text(s, 6.30, 4.28, 6.2, 0.55, "0.5% · 1% · 3%", size=27, bold=True, color=INK)
    add_text(s, 0.94, 5.10, 11.6, 0.48,
             "对照：Full / Random / Herding / Bonsai；跨架构：GCN / GAT / GIN",
             size=18, color=GREY)
    add_text(s, 0.94, 5.62, 11.6, 0.48,
             "baseline 节点数 n = (√(d²+t)−d)/2 —— Cora 1% 只分到 13 个节点",
             size=15, color=GREY)

    conclusion(s, "凝缩一次 0.73 s；全部 350 次训练在本机 CPU 完成")
    set_notes(s,
              "主讲 B，1.5 分钟。\n"
              "先交代我们实际跑的范围：两个数据集、三档预算、四个方法、五个种子，"
              "共 350 次训练，全部在 CPU 上跑完，凝缩一次 0.73 秒。\n"
              "重点说最后一行：预算按字节算，换到 baseline 只有 13 个节点 —— 后面"
              "所有 baseline 的方差都来自这里。")


def slide16(prs):
    s = prs.slides[15]
    clear_content(s)
    set_text(by_id(s, 4), "主结果：Bonsai 领先 11–60 点，但先看全图基准")
    set_text(by_id(s, 6), "来源：results/experiment1.csv；论文表 4（GCN，5 seeds）")

    kicker(s, "全图基准对齐了，才敢谈凝缩效果")
    add_fig(s, "fig1_accuracy_vs_budget_zh.png", 0.62, 2.20, 7.85)

    add_block(s, 8.72, 2.28, 3.9, "Full 六格：平均只差 0.63 点",
              "评估协议、划分与论文一致", h=1.1)
    add_block(s, 8.72, 3.62, 3.9, "Bonsai 稳定低 1.9 点",
              "Cora −1.4 / Citeseer −2.4\n幅度不随预算扩大", h=1.25)
    add_block(s, 8.72, 5.10, 3.9, "1% 之后曲线走平",
              "预算已饱和，见下一页", h=1.0)

    conclusion(s, "管线可信；差距集中在凝缩图本身，不在评估环节")
    set_notes(s,
              "主讲 B，2 分钟，重点页。\n"
              "先让听众看虚线：Full 是全图参照，我们六格平均只差 0.63 点，说明训练、划分、"
              "评估这一套是对的。再看实线：Bonsai 比论文低 1.9 点，但幅度不随预算扩大，"
              "这是系统性差异的特征，不是噪声。\n"
              "最后指一下 1% 以后的水平段，把话头交给下一页。")


def slide17(prs):
    s = prs.slides[16]
    clear_content(s)
    set_text(by_id(s, 4), "预算加六倍，凝缩图却一模一样")
    set_text(by_id(s, 6), "来源：results/budget_table.csv、efficiency.csv；main.py:size()")

    kicker(s, "「1%」不是 27 个节点，而是 2522 个")
    add_fig(s, "fig4_budget_accounting_zh.png", 0.62, 2.18, 7.6)

    add_block(s, 8.55, 2.24, 4.05, "1% 与 3%：逐字节相同",
              "2522 节点 / 10854 边", h=1.12)
    add_block(s, 8.55, 3.50, 4.05, "节点保留 2522 / 2708 = 93%",
              "1% 装下的其实是全部训练节点", h=1.12)
    add_block(s, 8.55, 4.76, 4.05, "逻辑 71.7 KB，落盘 1.87 MB",
              "论文按稀疏 int 记账，PyG 存 float32 + int64 边", h=1.25)

    conclusion(s, "「1% 还能到 85%」不是压缩强，而是几乎没压缩")
    set_notes(s,
              "主讲 B，2 分钟。\n"
              "这页回答两个问题。第一，为什么 1% 和 3% 结果一样：因为图逐字节相同，预算在 1% 就已经"
              "装下全部训练节点，再多预算也选不出新点。第二，1% 到底是多少：逻辑上是 71.7 KB，"
              "符合论文口径；但 PyG 落盘是 1.87 MB，节点保留了 93%。\n"
              "所以「1% 还有 85%」的真正原因是特征从 1433 维筛到 174 维、并且几乎没删节点，"
              "不是把图压缩了一百倍。这是全场最需要讲清楚的一页。")


def slide18(prs):
    s = prs.slides[17]
    clear_content(s)
    set_text(by_id(s, 4), "消融：PPR 是主因，选树顺序只值 1 点")
    set_text(by_id(s, 6), "来源：results/experiment3.csv（Cora，5 seeds）；论文图 4")

    kicker(s, "同时看准确率与图的真实大小")
    add_fig(s, "fig3_ablation_zh.png", 0.62, 2.22, 7.9)

    add_block(s, 8.72, 2.26, 3.9, "去 PPR：−5.0 点",
              "0.1% 预算，5 seeds", h=1.1)
    add_block(s, 8.72, 3.50, 3.9, "随机 Exemplar：−1.2 点",
              "把预算调到 0.08% 对齐大小后", h=1.1)
    add_block(s, 8.72, 4.74, 3.9, "随机 + 去 PPR：77.4",
              "反而高于只去 PPR 的 73.4", h=1.1)

    conclusion(s, "PPR 的收益依赖选点质量 —— 论文没有讨论这个交互")
    set_notes(s,
              "主讲 B，2 分钟。\n"
              "左边是准确率，右边是同一批图的逻辑大小 —— 必须一起看，否则会把「图更大」误当成"
              "「选得更好」。\n"
              "结论三点：PPR 是关键，0.1% 掉 5 点；随机选树只掉约 1 点；但两个都去掉反而比只去"
              "PPR 好 4 点，说明 PPR 在选点质量差的时候会退化成随机删点。第三点是论文没写的。")


def slide19(prs):
    s = prs.slides[18]
    clear_content(s)
    set_text(by_id(s, 4), "同一张图，三种训练器：复用成立，保真不均")
    set_text(by_id(s, 6), "来源：results/experiment2.csv、full_reference.csv；论文表 5")

    kicker(s, "Cora 最大差 5.3 点；Citeseer 只差 1.3 点")
    add_fig(s, "fig2_cross_arch_zh.png", 0.62, 2.20, 7.85)

    add_block(s, 8.72, 2.28, 3.9, "排序与论文一致",
              "GIN > GCN > GAT（Cora）", h=1.1)
    add_block(s, 8.72, 3.52, 3.9, "相对各自 Full",
              "−2.0 ~ +4.9 点，GIN 反而超过 Full", h=1.1)
    add_block(s, 8.72, 4.76, 3.9, "Citeseer 三架构几乎重合",
              "74.2 / 72.9 / 73.9", h=1.1)

    conclusion(s, "model-agnostic 有实验支持；「同等保真」仍不成立")
    set_notes(s,
              "主讲 B，1.5 分钟。\n"
              "同一份凝缩图 × 三种架构，没有为每个架构重新凝缩。点线是各架构的全图上限，"
              "所以看的是「相对自己掉多少」。\n"
              "Cora 上 GIN 甚至比全图还高 2 点，GAT 掉 4 点；Citeseer 三个架构几乎重合。"
              "结论：可复用是真的，"
              "但不同架构对同一份压缩信息的反应不同，不能说同等保真。")


def divider(prs, idx, subtitle, labels):
    s = prs.slides[idx]
    set_text(by_id(s, 11), subtitle)
    for sid, text in zip((13, 15, 17), labels):
        set_text(by_id(s, sid), text)


def slide21(prs):
    s = prs.slides[20]
    set_text(by_id(s, 6), "来源：本组实验一至三；本组综合判断")
    set_text(by_id(s, 14), "不成立（默认全量流程）")
    set_text(by_id(s, 16), "默认距离矩阵 O(n²)；我们只在小图上验证，未测缩放")
    set_text(by_id(s, 22), "有条件成立")
    set_text(by_id(s, 24), "同一张图三架构差 ≤5.3 点（Cora）/ 1.3（Citeseer）")
    set_text(by_id(s, 31), "成立，但幅度可解释")
    set_text(by_id(s, 33), "领先 Random 20–60 点、Herding 11–39 点；比论文低 1.9 点")
    set_text(by_id(s, 35), "证据支持「方法有效」，不支持「普适最优」")
    set_notes(s,
              "主讲 B，1.5 分钟。\n"
              "三条主张现在都有我们自己的数据，但判定强度不同：线性时间这条是代码证据，我们的实验"
              "不能证明也不能反驳；架构复用是实验支持但范围有限；精度优势成立，但幅度要拆开看。\n"
              "最后一句是全场的落点：方法有效，不等于普适最优。")


def slide22(prs):
    s = prs.slides[21]
    set_text(by_id(s, 4), "复现到了什么，没复现什么")
    set_text(by_id(s, 6), "来源：本组实验一至四；baselines/saved_* 核验")
    set_text(by_id(s, 7), "22")
    set_text(by_id(s, 10), "复现成功")
    set_text(by_id(s, 11), "主结果趋势、跨架构复用、消融归因、凝缩成本")
    set_text(by_id(s, 14), "复现受限")
    set_text(by_id(s, 15), "GCond / GDEM / GCSR：仓库合成图是占位数据，三种方法都只到 46.2%")
    set_text(by_id(s, 18), "未覆盖")
    set_text(by_id(s, 19), "Pubmed 及以上大图、线性渐近性、k=5 峰值")
    set_text(by_id(s, 21), "缺的是对比强度，不是可复现性")
    set_notes(s,
              "主讲 B，1 分钟。\n"
              "这一页把边界说清楚：能复现的都复现了；神经 baseline 因为官方仓库只给占位合成图，"
              "跑出来三种方法都是 46.2%（等于多数类），所以只能引用论文数值；大图和渐近性没有覆盖。\n"
              "一句话收：我们缺的是对比强度，不是可复现性。")


def slide23(prs):
    s = prs.slides[22]
    set_text(by_id(s, 20), "值得作为候选\n凝缩 0.73 s，重训 0.2 s")
    set_text(by_id(s, 26), "与 Full 实测比较\n我们 Full 87.8 / Bonsai 84.5")
    set_text(by_id(s, 32), "现有证据不足\n只覆盖两层模型与两个小图")
    set_notes(s,
              "主讲 B，1 分钟。\n"
              "基于我们的实测给使用建议：图固定、反复训练浅层模型，值得试，因为凝缩一次不到 1 秒；"
              "只训练一次或者精度优先，就和 Full 实测比，我们自己差 3.3 点；更深的模型和更大的图，"
              "现有证据不足。")


def backup_b2(prs):
    s = prs.slides[26]
    set_text(by_id(s, 4), "消融到底拆开了什么？")
    set_text(by_id(s, 6), "备份：本组 experiment3 的实测结果，不是计划")
    set_text(by_id(s, 10), "变体")
    set_text(by_id(s, 13), "0.1% 准确率")
    set_text(by_id(s, 16), "逻辑大小")
    set_text(by_id(s, 19), "Bonsai")
    set_text(by_id(s, 22), "78.34 ± 0.85")
    set_text(by_id(s, 25), "7.2 KB")
    set_text(by_id(s, 28), "随机 Exemplar")
    set_text(by_id(s, 31), "79.15 ± 0.43")
    set_text(by_id(s, 34), "8.6 KB")
    set_text(by_id(s, 35), "去 PPR：73.36 ± 1.27 / 6.8 KB")
    set_text(by_id(s, 36), "随机 + 去 PPR：77.38 ± 1.16 / 7.9 KB")
    set_text(by_id(s, 38), "同预算比较必须同时看大小：随机 Exemplar 的图大 19%")
    set_notes(s,
              "备用页。如果被问到「怎么证明是 PPR 在起作用」，翻到这页。\n"
              "四个变体的数字来自 experiment3.csv，0.1% 预算、5 个种子。注意随机 Exemplar 的图比 Bonsai "
              "大 19%，所以同预算下它并不吃亏；把预算调到 0.08% 对齐大小后是 77.12，比 Bonsai 低 1.2 点。\n"
              "关键结论：只去 PPR 掉 5 点，但随机 + 去 PPR 反而回到 77.4 —— 两个组件存在交互。")


def backup_b5(prs):
    s = prs.slides[29]
    set_text(by_id(s, 17), "特征 1433 → 174 维")
    set_text(by_id(s, 23), "每节点只按非零元计 2 B")
    set_text(by_id(s, 20), "共同预处理下覆盖还能增益多少")
    set_text(by_id(s, 26), "最终 2522 节点 / 10854 边 / 1516 训练目标")
    set_text(by_id(s, 28), "我们实测：逻辑 71.7 KB，占原图 0.93%")
    set_notes(s,
              "备用页。如果被追问「筛特征是不是作弊」，用我们自己的数字回答：\n"
              "论文按稀疏 int 记账，筛完特征后每节点只算非零元的 2 字节，所以 1% 预算能装下 2522 "
              "个节点；换成 dense float 落盘就是 1.87 MB，占原图 24%。\n"
              "公平比较要固定预算分母，并且同时报告最终维度、节点、边和监督目标数量。")


def agenda(prs):
    s = prs.slides[1]
    set_text(by_id(s, 19), "主结果 / 消融归因 / 复用与成本")
    set_text(by_id(s, 23), "三项判定 / 复现边界 / 适用场景")


def main() -> None:
    prs = Presentation(str(SRC))

    agenda(prs)

    divider(prs, 13, "我们复现了什么，证据能支撑到哪一步？",
            ["主结果", "消融归因", "复用与成本"])
    slide15(prs)
    slide16(prs)
    slide17(prs)
    slide18(prs)
    slide19(prs)

    divider(prs, 19, "复现之后，哪些主张站得住？",
            ["三项判定", "复现边界", "适用场景"])
    slide21(prs)
    slide22(prs)
    slide23(prs)

    backup_b2(prs)
    backup_b5(prs)

    prs.save(str(DST))
    print(f"wrote {DST}")


if __name__ == "__main__":
    main()