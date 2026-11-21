# Bonsai: Gradient-free Graph Distillation for Node Classification

This is the PyTorch implementation for Bonsai: Gradient-free Graph Distillation for Node Classification

# 课程复现说明

本仓库是上述论文的复现 fork（数据可视化课程大作业）。原始代码基本未改动，新增内容都在 `experiment/`、`results/` 下，并做了四处平台适配。

**复现范围**：Cora 与 Citeseer × 0.5% / 1% / 3% 三档字节预算 × {Full, Random, Herding, Bonsai} × 5 个训练种子，共 350 次训练、约 30 次凝缩，在 Apple M5 CPU 上约 10 分钟跑完。另有跨架构（同一份凝缩图 × GCN/GAT/GIN）、消融（随机 Exemplar / 去 PPR）、凝缩成本与参数 k 敏感性四组实验。

**主要结果**（与论文对照）：

| 项目 | 本次复现 | 论文 |
|---|---|---|
| 全图基准（6 格平均偏差） | 0.63 pp | — |
| Bonsai（Cora 1%） | 84.47 ± 0.54 | 85.76 ± 0.24 |
| Bonsai vs Random / Herding | 领先 20–60 / 11–39 pp | 同向 |
| 同一凝缩图跨三架构极差 | 5.28（Cora）/ 1.29（Citeseer） | 排序一致 |
| 凝缩耗时（Cora） | 0.73 s | 2.60 s（96 核 Xeon） |

**三个值得注意的发现**：（1）小图上预算在 1% 处饱和，Cora 1% 与 3% 的凝缩图逐字节相同；（2）"1%" 是稀疏 int 记账口径（逻辑 71.7 KB），实际落盘 1.87 MB、保留 93% 的节点；（3）PPR 的收益依赖选树质量——随机化 Exemplar 后移除 PPR 反而使准确率回升 4 点，论文未讨论该交互。

**已知限制**：`baselines/saved_*` 中的合成图经检验为占位示例（三种方法在同一协议下均为 46.2%，等于多数类），故 GCond/GDEM/GCSR 三列只能引用论文数值；Pubmed 及更大规模的图未覆盖；决策树随机种子被固定（论文未固定），这是 Bonsai 比论文低约 1.9 点最可能的原因。

**快速开始**（详见 `experiment/README.md`）：

```bash
PY=../pytorch_env/bin/python
$PY experiment/budget_table.py --datasets cora citeseer --budgets 0.005 0.01 0.03
bash experiment/run_exp1.sh    # 凝缩效果对比
bash experiment/run_exp2.sh    # 跨架构泛化
bash experiment/run_exp3.sh    # 消融
$PY experiment/plot_results.py # 出图
```

**与官方 `requirements.txt` 的差异**：`torch_sparse` 改为可选（WL 用 `torch.sparse.mm`，数值等价）、`torch.load` 显式 `weights_only=False`、决策树固定 `random_state=0`、数据集改由镜像下载。Python 3.13 + PyTorch 2.15 + PyG 2.8。

# Download Datasets

For Cora, Citeseer, and Pubmed, the code will directly download them from PyTorch Geometric. For Flickr, Ogbn-arxiv, and Reddit, we use the datasets provided by [GraphSAINT](https://github.com/GraphSAINT/GraphSAINT). They are available on [this Google Drive link](https://drive.google.com/open?id=1zycmmDES39zVlbVCYs88JTJ1Wm5FbfLz) provided by the GraphSAINT team. Download the files and unzip them to `datasets` at the root directory.

# Instructions

1. Please install dependencies from requirements.txt in `python==3.9.19`
2. You can directly run `bash run.sh 0`. Here, `0` is the index of the GPU to run on it. If no index is passed, the code runs on CPU. 
3. The outputs will be saved to `saved_ours` directory. It also contains `train_bonsai.py` script along with `train_all.sh` to train a `GCN`, `GAT`, and `GIN` on the saved outputs to get the results.

# Some fine-details

## Sampling for scalable Rev-k-NN computation

The code doesn't perform sampling by default, but it can be enabled by passing `0 < frac_to_sample < 1` to `repr_to_dist` function in `main.py` in Ln. 610.

## Dataset train/val/test split

We over-ride the default train/val/test split in Ln. 545-550 of `main.py` for all datasets. Specifically,  
```python3
train, idx_test = train_test_split(range(nnodes), test_size=0.2, random_state=42)
rng = np.random.RandomState(seed=0)
idx_train = rng.choice(train, size=int(0.7 * len(train)), replace=False)
idx_val = list(set(range(nnodes)) - set(idx_train).union(set(idx_test)))
splits = {"train": idx_train, "val": idx_val, "test": idx_test}
```

# MAG240M

Please refer to the `mag240m` directory's `README` for the instructions.

# How to cite this work

```
@inproceedings{
gupta2025bonsai,
title={Bonsai: Gradient-free Graph Condensation for Node Classification},
author={Mridul Gupta and Samyak Jain and Vansh Ramani and Hariprasad Kodamana and Sayan Ranu},
booktitle={The Thirteenth International Conference on Learning Representations},
year={2025},
url={https://openreview.net/forum?id=5x88lQ2MsH}
}
```
