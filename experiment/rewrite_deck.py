r"""Rewrite the fourth part of the class deck with our three experiments.

Structure agreed with the team:
  part 3 (slides 15-19)  = the paper's own experiments, kept verbatim
  part 4 (slide 20+)     = *our* reproduction: one slide per experiment

Reads  ../../Bonsai_课堂汇报.pptx   (never modified)
Writes ../../Bonsai_课堂汇报_v2.pptx

Two content slides are duplicated (they already carry the part-4 header and
page furniture) and moved after slide 21, so part 4 becomes:

  20  divider            (labels: 凝缩效果 / 跨架构复用 / 消融归因)
  21  experiment 1       accuracy vs budget          (fig1)
  22  experiment 2       same graph, three backbones (fig2)
  23  experiment 3       ablation                     (fig3)
  24  verdict + limits   (was "复现计划")
  25  when to use it     (was 适用场景, numbers refreshed)
  26  references         (unchanged)
  ...
  B7  the "1%" accounting slide (fig4) appended as a backup

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


def kicker(slide, text, color=RED):
    add_text(slide, 0.94, 1.66, 11.4, 0.42, text, size=19, bold=True, color=color,
             anchor=MSO_ANCHOR.MIDDLE)


def conclusion(slide, text):
    add_text(slide, 0.68, 6.62, 11.9, 0.42, text, size=17.5, bold=True, color=RED,
             anchor=MSO_ANCHOR.MIDDLE)


def duplicate_slide(prs, index: int):
    """Copy a slide's shapes into a new slide appended at the end."""
    src = prs.slides[index]
    new = prs.slides.add_slide(src.slide_layout)
    for shp in list(new.shapes):
        shp._element.getparent().remove(shp._element)
    for shp in src.shapes:
        new.shapes._spTree.append(copy.deepcopy(shp._element))
    # carry the speaker notes over as well (the notes placeholders live in the
    # notes slide, not in the slide layout, so add_slide starts without them)
    if src.has_notes_slide:
        for shp in src.notes_slide.shapes:
            new.notes_slide.shapes._spTree.append(copy.deepcopy(shp._element))
    return new


def move_slide(prs, from_index: int, to_index: int) -> None:
    lst = prs.slides._sldIdLst
    ids = list(lst)
    el = ids[from_index]
    lst.remove(el)
    lst.insert(to_index, el)


def renumber(prs) -> None:
    for i, s in enumerate(prs.slides, 1):
        for sh in s.shapes:
            if not sh.has_text_frame:
                continue
            try:
                near = abs(sh.left - Inches(12.12)) < 20000 and abs(sh.top - Inches(7.05)) < 20000
            except TypeError:
                near = False
            if near and sh.text_frame.text.strip().isdigit():
                set_text(sh, str(i))


# --------------------------------------------------------------------------- #
# part 4 content
# --------------------------------------------------------------------------- #
def exp1(prs):
    s = prs.slides[20]
    clear_content(s)
    set_text(by_id(s, 4), "实验一：同预算下，Bonsai 是否真的领先？")
    set_text(by_id(s, 6), "来源：results/experiment1.csv；两种数据集 × 3 档预算 × 4 方法 × 5 seeds")

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
              "这是我们自己的 100 次训练：两个数据集、三档预算、四种方法、五个种子。\n"
              "三个数字：领先 Random 20–60 点，领先 Herding 11–39 点，但比论文低 1.9 点。"
              "低 1.9 点是因为我们固定了论文没固定的随机种子，属于可解释的系统差，不是跑错。\n"
              "另外提醒：1% 和 3% 的柱子一样高，因为预算在 1% 就饱和了，细节在备份 B7。")


def exp2(prs):
    s = prs.slides[21]
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
              "同一份凝缩图，没有为三个架构分别重新凝缩。点线是各架构的全图上限，所以看的是"
              "相对自己掉多少。\n"
              "Cora 极差 5.3 点，GIN 最稳甚至超过全图，GAT 掉 4 点；Citeseer 三架构只差 1.3 点。"
              "结论：可复用是真的，但不同训练器对同一份压缩信息反应不同。")


def exp3(prs):
    s = prs.slides[22]
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
              "左边准确率、右边同一批图的逻辑大小，必须一起看，否则会把「图更大」当成「选得更好」。\n"
              "结论三点：PPR 关键，0.1% 掉 5 点；随机选树只掉 1.2 点；但两个都去掉反而比只去 PPR "
              "高 4 点，说明 PPR 在选点质量差时会退化成随机删点。第三点是论文没写的。")


def verdict(prs):
    s = prs.slides[23]
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
              "三个实验各对应一条结论：实验一证明精度优势是真的，六格全部领先，和论文只差 1.9 点；"
              "实验二证明同一份图能跨架构复用，Cora 极差 5.3 点、Citeseer 只有 1.3 点；"
              "实验三把增益拆开，PPR 是主因，选树顺序只值 1 点，而且两者有交互。\n"
              "\n"
              "提问预案（不上屏）：\n"
              "- 问「线性时间呢」：只在小图上跑过，没有测缩放，只能引用代码里的 O(n²) 距离矩阵。\n"
              "- 问「和 GCond/GDEM 比呢」：仓库自带的合成图是占位数据，三种方法跑出来都只有 46.2%，"
              "所以这一列只能引用论文数值，我们没有复现。\n"
              "- 问「为什么比论文低 1.9 点」：我们固定了论文没固定的决策树随机种子，特征固定 174 维；"
              "论文每次在 169–184 之间浮动取平均，相当于多试了几种特征子集。")


def scenarios(prs):
    s = prs.slides[24]
    set_text(by_id(s, 20), "值得作为候选\n凝缩 0.73 s，重训 0.2 s")
    set_text(by_id(s, 26), "与 Full 实测比较\n我们 Full 87.8 / Bonsai 84.5")
    set_text(by_id(s, 32), "现有证据不足\n只覆盖两层模型与两个小图")
    set_notes(s,
              "主讲 B，1 分钟。\n"
              "基于实测给建议：图固定、反复训练浅层模型，值得试，凝缩不到 1 秒；"
              "只训练一次或精度优先，就和 Full 实测比，我们差 3.3 点；"
              "更深模型和更大图，现有证据不足。")


def dividers(prs):
    s = prs.slides[19]
    set_text(by_id(s, 11), "三个实验，各自验证了什么？")
    for sid, text in zip((13, 15, 17), ["凝缩效果", "跨架构复用", "消融归因"]):
        set_text(by_id(s, sid), text)
    set_notes(s, "主讲 B。分节过渡约 5–8 秒。前三部分是论文自己怎么说，这一部分是我们自己跑了什么。")


def agenda(prs):
    s = prs.slides[1]
    set_text(by_id(s, 23), "三个实验 / 判定与边界 / 适用场景")


def backup_accounting(prs):
    """New backup page B7: the two readings of "1%" plus the saturation note."""
    dup = duplicate_slide(prs, 20)
    move_slide(prs, len(prs.slides._sldIdLst) - 1, len(prs.slides._sldIdLst) - 1)
    s = prs.slides[-1]
    clear_content(s)
    set_text(by_id(s, 2), "BONSAI  /  备用补充材料")
    set_text(by_id(s, 4), "「1%」到底是多少？为什么 1% 与 3% 一样")
    set_text(by_id(s, 6), "备份：results/budget_table.csv、efficiency.csv；main.py:size()")
    set_text(by_id(s, 7), "B7")

    kicker(s, "逻辑 71.7 KB 符合 1%，落盘 1.87 MB 是原图的 24%")
    add_fig(s, "fig4_budget_accounting_zh.png", 0.62, 2.18, 7.6)

    add_block(s, 8.55, 2.24, 4.05, "1% 与 3%：逐字节相同",
              "2522 节点 / 10854 边", h=1.05)
    add_block(s, 8.55, 3.42, 4.05, "节点保留 93%",
              "2522 / 2708，1% 已装下全部训练节点", h=1.05)
    add_block(s, 8.55, 4.60, 4.05, "两种口径",
              "稀疏 int 记账 vs PyG 的 float32 + int64", h=1.05)

    conclusion(s, "「1% 还能到 85%」不是压缩强，而是几乎没压缩")
    set_notes(s,
              "备用页。如果被问到「1% 到底压掉了多少」，翻到这页。\n"
              "逻辑上 71.7 KB，确实符合论文的 1% 口径；但 PyG 落盘 1.87 MB，是原图的 24%，"
              "节点保留了 93%。所以 1% 之所以还能到 85%，主要是特征从 1433 维筛到了 174 维，"
              "加上几乎没删节点。\n"
              "顺带解释为什么 1% 和 3% 一样：预算在 1% 就已经覆盖全部训练节点，再多也选不出新点。")


def backup_b2(prs):
    s = prs.slides[28]
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
              "四个变体的数字来自 experiment3.csv，0.1% 预算、5 个种子。随机 Exemplar 的图比 "
              "Bonsai 大 19%，所以同预算下它并不吃亏；把预算调到 0.08% 对齐大小后是 77.12。\n"
              "关键结论：只去 PPR 掉 5 点，但随机 + 去 PPR 反而回到 77.4，两个组件存在交互。")


def backup_b5(prs):
    s = prs.slides[31]
    set_text(by_id(s, 17), "特征 1433 → 174 维")
    set_text(by_id(s, 23), "每节点只按非零元计 2 B")
    set_text(by_id(s, 20), "共同预处理下覆盖还能增益多少")
    set_text(by_id(s, 26), "最终 2522 节点 / 10854 边 / 1516 训练目标")
    set_text(by_id(s, 28), "我们实测：逻辑 71.7 KB，占原图 0.93%")
    set_notes(s,
              "备用页。如果被追问「筛特征是不是作弊」，用我们自己的数字回答：\n"
              "论文按稀疏 int 记账，筛完特征后每节点只算非零元的 2 字节，所以 1% 预算能装下 2522 "
              "个节点；换成 dense float 落盘就是 1.87 MB，占原图 24%。\n"
              "公平比较要固定预算分母，并同时报告最终维度、节点、边和监督目标数量。")


def main() -> None:
    prs = Presentation(str(SRC))

    # two extra content slides for experiments 2 and 3 (part 4 grows by 2)
    for _ in range(2):
        duplicate_slide(prs, 20)
        move_slide(prs, len(prs.slides._sldIdLst) - 1, 21 + _)

    agenda(prs)
    dividers(prs)
    exp1(prs)
    exp2(prs)
    exp3(prs)
    verdict(prs)
    scenarios(prs)
    backup_b2(prs)
    backup_b5(prs)
    backup_accounting(prs)
    renumber(prs)

    prs.save(str(DST))
    print(f"wrote {DST}  ({len(prs.slides)} slides)")


if __name__ == "__main__":
    main()