# experiment/ —— Bonsai 复现实验脚本

所有脚本都在 `Bonsai/` 目录下用 `PYTHONPATH=.` 运行。完整实验设计见仓库根目录的
`Bonsai_两天复现实验实施清单.md`。

## 环境

```bash
# 本机 macOS（无需 GPU）
python -m venv pytorch_env && source pytorch_env/bin/activate
pip install torch torch-geometric scikit-learn scipy tqdm tensorboardX networkx
```

> 官方 `requirements.txt` 钉的是 `torch==1.13.1+cu117` + `torch_sparse`，是 Linux/CUDA 的轮子。
> 本目录的代码不依赖 `torch_sparse`（已做可选化），CPU 也能跑。

## 数据

Cora / Citeseer 由 PyG 的 `Planetoid` 读取。若 `raw.githubusercontent.com` 不通
（国内常见），手动放到 `datasets/<name>/raw/`：

```bash
mkdir -p datasets/citeseer/raw && cd datasets/citeseer/raw
for f in x tx allx y ty ally graph test.index; do
  curl -sSLO "https://cdn.jsdelivr.net/gh/kimiyoung/planetoid@master/data/ind.citeseer.$f"
done
```

## 预算口径（和论文一致）

论文：`S_r = 凝缩图字节 / 原图字节`。原图字节按 `main.py:size()` 算：

```
full = (n_nodes * d + n_edges * 2) * 2        # int 特征 2 B
```

Random / Herding 允许的节点数按 `baselines/README.md` 的 dense-float 模型反推：

```
n = (sqrt(d^2 + t) - d) / 2       t = S_r * full
```

| 数据集 | 0.5% | 1% | 3% |
|---|---|---|---|
| Cora (d=1433) | 6 | 13 | 39 |
| Citeseer (d=3703) | 8 | 16 | 49 |

`experiment/budget_table.py` 会打印这张表，并把 Bonsai 凝缩图的逻辑大小/实际文件大小
一起写进 `results/budget_table.csv`。

## 脚本

| 文件 | 作用 |
|---|---|
| `budget_table.py` | 打印/落表各格子的预算字节与节点数 |
| `train_baseline.py` | Full / Random / Herding 训练，支持 5 seeds |
| `train_condensed.py` | 训练已凝缩的图（Bonsai 及消融变体），与 baseline 共用同一后端 |
| `collect_results.py` | 汇总 CSV，输出 `summary_*.csv` 与 markdown 表 |
| `run_exp1.sh` | 实验一全矩阵（含凝缩、4 种方法、收敛后自动汇总） |
| `run_exp2.sh` | 实验二：同一份凝缩图 × GCN/GAT/GIN |

## 快速开始

```bash
cd Bonsai
export PY=../pytorch_env/bin/python

# 实验一（Cora + Citeseer，3 个预算，5 seeds；本机约 3 分钟）
bash experiment/run_exp1.sh

# 实验二（复用实验一的凝缩图）
bash experiment/run_exp2.sh

# 只跑一格
$PY experiment/train_baseline.py --dataset cora --method random \
   --budget 0.01 --model GCN --seeds 5
$PY experiment/train_condensed.py --dataset cora --budget 0.01 \
   --graph saved_ours/cora-0.01/data_m_0.9.pt --method bonsai --model GAT --seeds 5
```

可用环境变量覆盖批处理参数：`DATASETS`、`BUDGETS`、`SEEDS`、`MODELS`、`NEPOCHS`、`PY`。

## 结果文件

- 每次训练一行，追加到 `results/experiment1.csv` / `experiment2.csv`
- 汇总：`results/summary_experiment1.csv` 等
- 日志：`outputs/training/<dataset>_<budget>_<method>_<model>.log`
- 构造出的 baseline 图：`outputs/condensation/<dataset>-<budget>_<method>/data.pt`

字段见 CSV 表头；关键字段含义：

| 字段 | 含义 |
|---|---|
| `budget` | `S_r`；Full 一行为 `full` |
| `n_features` | Bonsai 是筛选后的维度（Cora 174），baseline 是原始维度（1433） |
| `logical_KB` | 论文口径 `(nnz + 2×边数) × 2 / 1024` |
| `file_bytes` | PyG 实际落盘字节（含 int64 边与 pickle 开销） |
| `n_nodes` / `n_edges` | 训练图规模；`n_edges` 是**有向**边数 |

## 常见问题

1. **`ModuleNotFoundError: torch_sparse`** —— 官方文件里已改为可选导入；若你用别的 clone，
   需要同样处理（`torch.sparse.mm` 可完全替代）。
2. **`UnpicklingError: Weights only load failed`** —— torch ≥ 2.6 的
   `torch.load` 默认 `weights_only=True`；加载凝缩图要显式 `weights_only=False`。
3. **每次凝缩结果不同** —— `utils.py` 的决策树原先没固定种子，`features_used` 会在
   169–184 之间跳。已加 `random_state=0`，现在稳定为 174 维。
4. **`saved_ours/train_bonsai.py` 不打印准确率** —— 它丢弃了返回值；用
   `train_condensed.py` 代替（同一后端，但会写 CSV）。
5. **数据集下载卡住** —— 见上文 jsdelivr 镜像；PyG 的 `fs.cp` 走 GitHub 时容易超时。

## 已知偏差（与论文）

Cora 1%：Bonsai 85.72±1.18（论文 85.76±0.24）、Herding 48.2±0.7（52.1±0.0）、
Random 38.1±3.8（27.8±2.1）。Random 偏高是因为 n=13 时诱导子图没有任何边，
GCN 退化为 13 个样本上的 MLP，结果强烈依赖抽到哪些点（换 selection seed 实测 39–49）。
定性结论（Bonsai ≫ Random/Herding）不受影响。