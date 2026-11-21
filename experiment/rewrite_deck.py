r"""Rebuild the class deck's part 3 (paper evidence) and part 4 (our work).

Part 3 now mirrors the paper's own experimental section, one slide per
subsection, with the numbers taken from the PDF (Tables 4-6, 8, Figs 4/6c):

  §4.1 setup          slides 15
  §4.2 accuracy       16
  §4.2 scale          17   (MAG240M / Reddit, the two large graphs)
  §4.3 cross-arch     18
  §4.4 efficiency     19
  §4.5 ablation       20

Part 4 keeps our three experiments (slides 22-24), verdict, scenarios.

Reads  ../../Bonsai_课堂汇报.pptx   (never modified)
Writes ../../Bonsai_课堂汇报_v2.pptx

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
    tf = shape.text_frame
    p0 = tf.paragraphs[0]
    if not p0.runs:
        p0.add_run().text = ""
    for extra in tf.paragraphs[1:]:
        extra._p.getparent().remove(extra._p)
    lines = text.split("\n")
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


def kicker(slide, text, size=19):
    add_text(slide, 0.94, 1.66, 11.4, 0.42, text, size=size, bold=True, color=RED,
             anchor=MSO_ANCHOR.MIDDLE)


def conclusion(slide, text):
    add_text(slide, 0.68, 6.62, 11.9, 0.42, text, size=17.5, bold=True, color=RED,
             anchor=MSO_ANCHOR.MIDDLE)


def duplicate_slide(prs, index: int):
    src = prs.slides[index]
    new = prs.slides.add_slide(src.slide_layout)
    for shp in list(new.shapes):
        shp._element.getparent().remove(shp._element)
    for shp in src.shapes:
        new.shapes._spTree.append(copy.deepcopy(shp._element))
    if src.has_notes_slide:
        for shp in src.notes_slide.shapes:
            new.notes_slide.shapes._spTree.append(copy.deepcopy(shp._element))
    return new


def move_slide(prs, from_index: int, to_index: int) -> None:
    lst = prs.slides._sldIdLst
    el = list(lst)[from_index]
    lst.remove(el)
    lst.insert(to_index, el)


def title_of(slide) -> str:
    try:
        return by_id(slide, 4).text_frame.text
    except KeyError:
        return ""


def find_slide(prs, needle: str) -> int:
    for i, s in enumerate(prs.slides):
        if needle in title_of(s):
            return i
    raise KeyError(needle)


def renumber(prs) -> None:
    for i, s in enumerate(prs.slides, 1):
        for sh in s.shapes:
            if not sh.has_text_frame:
                continue
            near = abs(sh.left - Inches(12.12)) < 20000 and abs(sh.top - Inches(7.05)) < 20000
            if near and sh.text_frame.text.strip().isdigit():
                set_text(sh, str(i))


# --------------------------------------------------------------------------- #
# part 3 -- one slide per subsection of the paper's section 4
# --------------------------------------------------------------------------- #
def reorder_part3(prs) -> None:
    """[acc, cross, eff, large, scope] -> [scope, acc, large, cross, eff]."""
    # the paper's own order already is setup -> accuracy -> large graphs ->
    # cross-arch -> efficiency, so only one spare page is needed (§4.5)
    duplicate_slide(prs, 15)     # copy of the accuracy page, rebuilt below
    move_slide(prs, len(prs.slides._sldIdLst) - 1, 19)


def write_part3(prs) -> None:
    # ---- 15 §4.1 setup -----------------------------------------------------
    s = prs.slides[14]
    set_text(by_id(s, 4), "实验设置：7 个数据集、3 档预算、8 个基线")
    set_text(by_id(s, 6), "来源：原文 §4.1、表 3；附录 B.1–B.2")
    set_text(by_id(s, 9), "最大 1.21 亿节点，60:20:20 划分，每格跑 5 次")
    set_text(by_id(s, 10), "7")
    set_text(by_id(s, 11), "数据集")
    set_text(by_id(s, 12), "3")
    set_text(by_id(s, 13), "档字节预算")
    set_text(by_id(s, 14), "5")
    set_text(by_id(s, 15), "次独立运行")
    set_text(by_id(s, 17), "0.5% · 1% · 3%")
    set_text(by_id(s, 18), "Cora → MAG240M")
    set_text(by_id(s, 19), "基线：GCond · GDEM · GCSR · EXGC · GC-SNTK · GEOM，外加 Random / Herding")
    set_text(by_id(s, 21), "指标：测试准确率 + 字节压缩比 Sᵣ = 凝缩图字节 / 全图字节")
    set_notes(s,
              "主讲 B，1 分钟。\n"
              "第三部分看论文自己的实验，结构跟论文第 4 节一致：设置、精度、规模、跨架构、成本、消融。\n"
              "设置一句话：7 个数据集，最大是 1.21 亿节点的 MAG240M；3 档字节预算；8 个基线，"
              "其中 6 个神经方法、2 个非神经方法；每格 5 次运行，报均值和标准差。"
              "划分是 60:20:20，MAG240M 用 80:10:10。")

    # ---- 16 §4.2 accuracy --------------------------------------------------
    s = prs.slides[15]
    set_text(by_id(s, 4), "精度：18 个场景里 12 次第一")
    set_text(by_id(s, 6), "来源：原文表 4、§4.2；5 次运行，均值 ± SD")
    set_text(by_id(s, 9), "Cora 1%：85.76，领先次优 8.2 点，距全图仅 2.8 点")
    set_text(by_id(s, 13),
             "Random 27.75 / Herding 52.07 / Bonsai 85.76 / Full 88.56")
    set_text(by_id(s, 15), "12 / 18 场景第一")
    set_text(by_id(s, 16), "多处的提升超过 5 个百分点；GDEM 是第二好的方法")
    set_text(by_id(s, 18), "距全图只差 2.8 点")
    set_text(by_id(s, 19), "Bonsai 85.76 vs Full 88.56 —— 凝缩几乎不付精度代价")
    set_text(by_id(s, 21), "在报告设置下，论文的精度优势成立")
    set_notes(s,
              "主讲 B，1.5 分钟。\n"
              "论文的精度结论是：18 个设置里 12 个第一，多处比第二名高 5 个点以上，GDEM 是第二好的方法。\n"
              "具体看 Cora 1%：Bonsai 85.76，次优 GCSR 77.56，领先 8.2 点；距全图 88.56 只差 2.8 点。"
              "所以它说「无梯度不以精度为代价」。")

    # ---- 17 §4.2 large graphs ---------------------------------------------
    s = prs.slides[16]
    set_text(by_id(s, 4), "扩到 1.21 亿节点：能跑完，但差距不随预算收敛")
    set_text(by_id(s, 6), "来源：原文表 4、§4.2；OOT = 5 小时内未完成")
    set_text(by_id(s, 9), "MAG240M 上只有 Bonsai、Random、Herding 跑完")
    set_text(by_id(s, 10), "MAG240M（1.21 亿节点）· Accuracy (%)")
    set_text(by_id(s, 11), "Reddit · Accuracy (%)")
    set_text(by_id(s, 25), "预算 6×，Bonsai 只涨 1.06 点")
    set_text(by_id(s, 26), "3% 时被 Bonsai 反超（88.90 vs 85.75）")
    set_text(by_id(s, 28), "规模优势成立；差距与排名都不承诺稳定")
    set_notes(s,
              "主讲 B，1.5 分钟。\n"
              "两张大图。左边 MAG240M 有 1.21 亿节点，论文里只有 Bonsai、Random、Herding 在 5 小时内跑完，"
              "其余全部 OOT；但预算翻 6 倍，Bonsai 只从 52.33 涨到 53.39，离全图的 69.95 还差 16.6 点。\n"
              "右边 Reddit：低预算时 GDEM 领先，3% 时被 Bonsai 反超。\n"
              "所以「能扩到超大图」成立，「一定赢」不成立。")

    # ---- 18 §4.3 cross-architecture ---------------------------------------
    s = prs.slides[17]
    set_text(by_id(s, 4), "跨架构：同一份图，GAT 78.67、GIN 84.80")
    set_text(by_id(s, 6), "来源：原文表 5、§4.3；差值为 Full − Bonsai（Cora，1%）")
    set_text(by_id(s, 9), "Cora 1%：把同一份凝缩图交给三种训练器")
    set_text(by_id(s, 11), "可复用的前提")
    set_text(by_id(s, 13), "各架构损失不同\nGCN 2.80 / GAT 7.03 / GIN 1.82")
    set_text(by_id(s, 16), "model-agnostic 成立；各架构保真不同")
    set_notes(s,
              "主讲 B，1.5 分钟。\n"
              "论文的第三个证据：GDEM 和 Bonsai 是 model-agnostic 的，同一份凝缩图可以换训练器；"
              "GCond 和 GCSR 则要为每个架构单独凝缩。\n"
              "Cora 1% 上，Bonsai 的 GAT 是 78.67、GIN 是 84.80；相对各自全图的损失是 GCN 2.80、"
              "GAT 7.03、GIN 1.82。可复用是真的，但各架构保真不同。")

    # ---- 19 §4.4 efficiency ------------------------------------------------
    s = prs.slides[18]
    set_text(by_id(s, 4), "效率：平均比最快基线快 7 倍，且全在 CPU 上")
    set_text(by_id(s, 6), "来源：原文表 6、表 8、§4.4；换算与倍数为本组计算")
    set_text(by_id(s, 9), "Reddit，0.5%：各阶段耗时（秒）")
    set_text(by_id(s, 49), "造图比全图训练还贵")
    set_text(by_id(s, 53), "Bonsai 造图 0.48× 全图训练；GCond 是 12.4×")
    set_notes(s,
              "主讲 B，1.5 分钟。\n"
              "成本这一段有两个数。第一，Bonsai 的凝缩是 CPU-bound，平均比最快的基线 EXGC 快 7 倍以上，"
              "论文摘要里对全部基线平均是 22 倍。\n"
              "第二，Reddit 0.5% 上，Bonsai 造图 1170.64 秒，全图训练一次 2425.68 秒，比值 0.48；"
              "而 GCond 造图 30112 秒，是全图训练的 12.4 倍 —— baseline 的造图成本比训练还高，"
              "这恰好抵消了凝缩的意义。")

    # ---- 20 §4.5 ablation + parameters -------------------------------------
    s = prs.slides[19]
    clear_content(s)
    set_text(by_id(s, 4), "消融：两个组件都必要，重要性随预算反转")
    set_text(by_id(s, 6), "来源：原文图 4、图 6c、§4.5、附录 B.4")

    kicker(s, "论文图 4：去掉任一组件，多数设置都显著掉点")
    rows = [
        ("完整 Bonsai", "两个组件都在，作为表中的最高参照"),
        ("去掉 PPR 剪枝", "低预算时影响小；预算变大、图变密后影响变大（Reddit 最明显）"),
        ("去掉 Rev-k-NN", "改用随机选树；0.5% 压缩率下掉点最多，预算增大后影响减弱"),
        ("两者都去掉", "在二者基础上进一步下降"),
    ]
    y = 2.24
    for name, effect in rows:
        add_text(s, 0.90, y, 3.30, 0.40, name, size=16, bold=True, color=INK)
        add_text(s, 4.30, y + 0.03, 8.30, 0.55, effect, size=13, color=GREY, spacing=1.1)
        y += 0.86
    add_text(s, 0.90, 5.62, 11.6, 0.40,
             "参数敏感性：k 变化时性能总体稳定，峰值在 k=5（图 6c）；采样比例只缩小距离计算的规模（附录 B.4）",
             size=13, color=GREY)
    conclusion(s, "组件的重要性随压缩率反转 —— 论文自己指出了这一点")
    set_notes(s,
              "主讲 B，1.5 分钟。\n"
              "论文最后做了消融：去掉 PPR、去掉 Rev-k-NN（改成随机选树）、两个都去掉。\n"
              "结论是两者都必要，但重要性随压缩率反转：0.5% 这种高压缩率下，去掉 Rev-k-NN 掉得最多；"
              "预算变大之后，PPR 反而更关键，因为图的边更密了。\n"
              "参数方面：k 变化时性能总体稳定，峰值在 5；采样比例只是把距离计算的规模缩小。")

    # divider labels
    s = prs.slides[13]
    set_text(by_id(s, 11), "论文的实验能支撑到哪一步？")
    for sid, text in zip((13, 15, 17), ["实验设置", "精度与规模", "成本与消融"]):
        set_text(by_id(s, sid), text)


# --------------------------------------------------------------------------- #
# part 4 -- our three experiments
# --------------------------------------------------------------------------- #
def exp1(prs, i):
    s = prs.slides[i]
    clear_content(s)
    set_text(by_id(s, 4), "实验一：同预算下，Bonsai 是否真的领先？")
    set_text(by_id(s, 6), "来源：results/experiment1.csv；2 数据集 × 3 预算 × 4 方法 × 5 seeds")
    kicker(s, "两个数据集、三档预算、四种方法、五个种子")
    add_fig(s, "fig1_accuracy_vs_budget_zh.png", 0.62, 2.20, 7.85)
    add_block(s, 8.72, 2.24, 3.9, "领先 Random 20–60 点",
              "6 个格子里 Random 几乎贴着随机猜测", h=1.05)
    add_block(s, 8.72, 3.42, 3.9, "领先 Herding 11–39 点",
              "低预算时 Herding 更接近 Bonsai", h=1.05)
    add_block(s, 8.72, 4.60, 3.9, "比论文低 1.9 点",
              "Cora −1.4 / Citeseer −2.4，幅度稳定", h=1.05)
    conclusion(s, "论文的精度优势成立；差距来自实现，不是评估协议")
    set_notes(s,
              "主讲 B，1.5 分钟。\n"
              "这是我们自己的 100 次训练。三个数字：领先 Random 20–60 点，领先 Herding 11–39 点，"
              "但比论文低 1.9 点。低的原因是固定了论文没固定的决策树种子。\n"
              "另外提醒：1% 和 3% 的柱子一样高，因为预算在 1% 就饱和了，细节在备份 B7。")


def exp2(prs, i):
    s = prs.slides[i]
    clear_content(s)
    set_text(by_id(s, 4), "实验二：同一份凝缩图，换个训练器还行吗？")
    set_text(by_id(s, 6), "来源：results/experiment2.csv、full_reference.csv；每格只凝缩一次")
    kicker(s, "只凝缩一次，喂给 GCN / GAT / GIN")
    add_fig(s, "fig2_cross_arch_zh.png", 0.62, 2.20, 7.85)
    add_block(s, 8.72, 2.24, 3.9, "Cora 极差 5.3 点",
              "GIN 86.9 > GCN 84.5 > GAT 81.8", h=1.05)
    add_block(s, 8.72, 3.42, 3.9, "Citeseer 极差 1.3 点",
              "74.2 / 72.9 / 73.9，几乎重合", h=1.05)
    add_block(s, 8.72, 4.60, 3.9, "相对各自 Full：−2.0 ~ +4.9",
              "Cora 上 GIN 反而高于全图", h=1.05)
    conclusion(s, "model-agnostic 成立；「各架构同等保真」不成立")
    set_notes(s,
              "主讲 B，1.5 分钟。\n"
              "同一份凝缩图，没有为三个架构分别重新凝缩。点线是各架构的全图上限。\n"
              "Cora 极差 5.3 点，GIN 最稳甚至超过全图，GAT 掉 4 点；Citeseer 三架构只差 1.3 点。")


def exp3(prs, i):
    s = prs.slides[i]
    clear_content(s)
    set_text(by_id(s, 4), "实验三：增益到底来自哪个组件？")
    set_text(by_id(s, 6), "来源：results/experiment3.csv（Cora，5 seeds）")
    kicker(s, "同预算拆开 PPR 与选树顺序，并同时看图的真实大小")
    add_fig(s, "fig3_ablation_zh.png", 0.62, 2.22, 7.9)
    add_block(s, 8.72, 2.24, 3.9, "去 PPR：−5.0 点",
              "0.1% 预算，三档里影响最大", h=1.05)
    add_block(s, 8.72, 3.42, 3.9, "随机 Exemplar：−1.2 点",
              "把预算调到 0.08% 对齐大小后", h=1.05)
    add_block(s, 8.72, 4.60, 3.9, "随机 + 去 PPR：77.4",
              "反而高于只去 PPR 的 73.4", h=1.05)
    conclusion(s, "PPR 是主因；它的收益依赖选树质量 —— 论文未讨论")
    set_notes(s,
              "主讲 B，1.5 分钟。\n"
              "左边准确率、右边同一批图的逻辑大小，必须一起看。\n"
              "PPR 关键，0.1% 掉 5 点；随机选树只掉 1.2 点；两个都去掉反而比只去 PPR 高 4 点 —— "
              "PPR 在选点质量差时会退化成随机删点。第三点是论文没写的。")


def verdict(prs, i):
    s = prs.slides[i]
    set_text(by_id(s, 4), "三个实验，分别证明了什么")
    set_text(by_id(s, 6), "来源：本组实验一至三（results/*.csv，5 seeds）")
    set_text(by_id(s, 10), "精度优势成立")
    set_text(by_id(s, 11), "六格全部领先 Random 20–60 点、Herding 11–39 点；与论文差 1.9 点")
    set_text(by_id(s, 14), "架构复用成立")
    set_text(by_id(s, 15), "同一份凝缩图跨 GCN/GAT/GIN：Cora 极差 5.3 点、Citeseer 1.3 点")
    set_text(by_id(s, 18), "增益归因已拆开")
    set_text(by_id(s, 19), "PPR 是主因（−5.0 点），选树顺序约 1.2 点，两者存在交互")
    set_text(by_id(s, 21), "三项结论都来自本组实测：350 次训练，全部可复现")
    set_notes(s,
              "主讲 B，1 分钟。\n"
              "三个实验各对应一条结论：精度优势是真的；同一份图能跨架构复用；增益可以拆开。\n"
              "提问预案（不上屏）：线性时间只在小图上跑过；GCond/GDEM/GCSR 因为仓库只给占位合成图，"
              "这一列只能引用论文数值；比论文低 1.9 点是因为我们固定了决策树种子。")


def scenarios(prs, i):
    s = prs.slides[i]
    set_text(by_id(s, 20), "值得作为候选\n凝缩 0.73 s，重训 0.2 s")
    set_text(by_id(s, 26), "与 Full 实测比较\n我们 Full 87.8 / Bonsai 84.5")
    set_text(by_id(s, 32), "现有证据不足\n只覆盖两层模型与两个小图")
    set_notes(s,
              "主讲 B，1 分钟。\n"
              "基于实测给建议：图固定、反复训练浅层模型，值得试，凝缩不到 1 秒；"
              "只训练一次或精度优先，就和 Full 实测比，我们差 3.3 点；更深模型和更大图，证据不足。")


def backup_b2(prs, i):
    s = prs.slides[i]
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
              "备用页。四个变体的数字来自 experiment3.csv，0.1% 预算、5 个种子。\n"
              "关键：只去 PPR 掉 5 点，但随机 + 去 PPR 反而回到 77.4，两个组件存在交互。")


def backup_b5(prs, i):
    s = prs.slides[i]
    set_text(by_id(s, 17), "特征 1433 → 174 维")
    set_text(by_id(s, 23), "每节点只按非零元计 2 B")
    set_text(by_id(s, 20), "共同预处理下覆盖还能增益多少")
    set_text(by_id(s, 26), "最终 2522 节点 / 10854 边 / 1516 训练目标")
    set_text(by_id(s, 28), "我们实测：逻辑 71.7 KB，占原图 0.93%")
    set_notes(s,
              "备用页。论文按稀疏 int 记账，筛完特征后每节点只算非零元的 2 字节，所以 1% 能装 2522 个节点；"
              "换成 dense float 落盘就是 1.87 MB，占原图 24%。")


def backup_accounting(prs):
    dup = duplicate_slide(prs, 14)
    s = prs.slides[-1]
    clear_content(s)
    set_text(by_id(s, 2), "BONSAI  /  备用补充材料")
    set_text(by_id(s, 4), "「1%」到底是多少？为什么 1% 与 3% 一样")
    set_text(by_id(s, 6), "备份：results/budget_table.csv、efficiency.csv；main.py:size()")
    set_text(by_id(s, 7), "B7")
    kicker(s, "逻辑 71.7 KB 符合 1%，落盘 1.87 MB 是原图的 24%")
    add_fig(s, "fig4_budget_accounting_zh.png", 0.62, 2.18, 7.6)
    add_block(s, 8.55, 2.24, 4.05, "1% 与 3%：逐字节相同", "2522 节点 / 10854 边", h=1.05)
    add_block(s, 8.55, 3.42, 4.05, "节点保留 93%", "2522 / 2708，1% 已装下全部训练节点", h=1.05)
    add_block(s, 8.55, 4.60, 4.05, "两种口径", "稀疏 int 记账 vs PyG 的 float32 + int64", h=1.05)
    conclusion(s, "「1% 还能到 85%」不是压缩强，而是几乎没压缩")
    set_notes(s,
              "备用页。如果被问到「1% 到底压掉了多少」，翻到这页。逻辑 71.7 KB 符合论文的 1% 口径，"
              "但落盘 1.87 MB、保留了 93% 的节点；1% 之所以还能到 85%，主要是特征从 1433 维筛到 174 维。")


def agenda(prs):
    s = prs.slides[1]
    set_text(by_id(s, 19), "实验设置 / 精度与规模 / 成本与消融")
    set_text(by_id(s, 23), "三个实验 / 判定与边界 / 适用场景")


def main() -> None:
    prs = Presentation(str(SRC))

    reorder_part3(prs)
    write_part3(prs)

    # part 4: two extra slots, so experiments 2 and 3 sit between exp1 and
    # the old "三项主张 / 复现计划 / 适用场景" pages
    div4 = find_slide(prs, "第四部分")
    for k in range(2):
        duplicate_slide(prs, div4 + 1)
        move_slide(prs, len(prs.slides._sldIdLst) - 1, div4 + 2 + k)

    agenda(prs)
    exp1(prs, div4 + 1)
    exp2(prs, div4 + 2)
    exp3(prs, div4 + 3)
    verdict(prs, div4 + 4)
    scenarios(prs, div4 + 5)
    backup_b2(prs, find_slide(prs, "结构覆盖与监督处理"))
    backup_b5(prs, find_slide(prs, "筛特征是否改变了预算公平性"))
    backup_accounting(prs)
    renumber(prs)

    prs.save(str(DST))
    print(f"wrote {DST}  ({len(prs.slides)} slides)")


if __name__ == "__main__":
    main()