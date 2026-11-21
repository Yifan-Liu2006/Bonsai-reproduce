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
| `run_exp3.sh` | 实验三消融：Bonsai / 随机 Exemplar / 去 PPR，0.1%–1% |
| `run_exp4.sh` | 参数敏感性：k = 1/3/5/10，每个 k 重凝缩一次 |
| `measure_condensation.py` | 单独测量凝缩耗时与图大小（论文 §4.4） |
| `train_released_baseline.py` | 在 `baselines/saved_*` 的合成图上训练 GCond/GDEM/GCSR（见文末警告） |
| `main_random_exemplar.py` | 消融变体 A：Exemplar 顺序换成固定种子随机排列 |
| `main_no_ppr.py` | 消融变体 B：跳过 PPR 删点（并把 upscale 设为 1） |
| `main_random_no_ppr.py` | 消融变体 C：两个都去掉（对应论文 Fig.4 的第三个变体） |
| `shims/torch_sparse.py` | `torch_sparse` 的最小替身，仅为跑通官方 `baselines/` 代码 |

## 快速开始

```bash
cd Bonsai
export PY=../pytorch_env/bin/python

# 实验一（Cora + Citeseer，3 个预算，5 seeds；本机约 3 分钟）
bash experiment/run_exp1.sh

# 实验二（复用实验一的凝缩图）
bash experiment/run_exp2.sh

# 实验三（消融，Cora，0.1%–1%，5 seeds）
bash experiment/run_exp3.sh

# 参数敏感性 k（论文 §4.5）
bash experiment/run_exp4.sh

# 凝缩成本（论文 §4.4）
$PY experiment/measure_condensation.py --datasets cora citeseer --budgets 0.005 0.01 0.03

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

## 消融的注意事项

`run_exp3.sh` 的预算默认是 `0.001 0.002 0.005 0.01`，但 **1% 上两个消融都是空操作**：
预算已经覆盖全部训练节点，任何 Exemplar 顺序都选出同一批点，去 PPR 后图只差 1 个节点。
真正有信息的是 0.1%–0.5%。

实测（Cora，5 seeds）：

| S_r | Bonsai | 随机 Exemplar | 去 PPR | 随机 + 去 PPR |
|---|---|---|---|---|
| 0.1% | 78.34 | 79.15（图大 19%） | **73.36** | 77.38 |
| 0.2% | 79.96 | 79.37 | 78.08 | 80.22 |
| 0.5% | 82.92 | 82.69 | 82.47 | 82.81 |
| 1% | 84.47 | 84.47（同图） | 84.47（同图） | — |

- PPR 是主要贡献者，且预算越紧影响越大（0.1% 掉 5 点）。
- 随机 Exemplar 在同预算下不明显掉点，但图大 19%；把预算降到 0.08% 做大小对齐后
  是 77.12（−1.2 点），即 Rev-k-NN/Coverage 在 Cora 上约值 1 个点。


## ⚠️ baselines/saved_* 里的合成图是占位示例，不要用来产生结果

`baselines/saved_gcond`、`saved_GCSR`、`saved_GDEM` 下有 Cora/Citeseer 的
`adj_*.pt / feat_*.pt / label_*.pt`，文件名看起来齐全，但它们是仓库里
"example" 性质的占位数据（见 `baselines/README.md`）。

实测（三者完全一致，说明特征里没有类别信息）：

| 检查 | 结果 |
|---|---|
| 在合成图上训练 GCN | 三种方法都只到 **46.2%**，正好等于多数类（6/13） |
| 逻辑回归留一验证 | 三者都是 **46.2%** |
| 特征缩放 1/4/14/40 倍重训 | 测试准确率 18–32%，无改善 |
| 论文 Table 4（GCond, Cora 1%） | **77.30** |

因此 `train_released_baseline.py` 目前跑出来的数字**不能写进报告**；它的价值是
"拿到真实合成图后可以直接跑"。GCond/GDEM/GCSR 的对比只能引用论文数值。
