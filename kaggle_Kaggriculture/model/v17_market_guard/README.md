# V17 market guard（市场护栏）

线上 700 名根因（开局扰动打断资金链 + 门控口径错位）的直接对策。调查全文见
`../v16_online_fidelity/REPORT.md`，实验记录见 `../experiments.md`。

- `main.py`：V120 底盘 + 防御护栏（开局两步清单重排 [动物,雇,种,品] + 第 1-2 天牛羊补买）
- `main_attack.py`：防御 + 进攻扰动（t0 买 53 小麦 / t1 卖 48；`RESORT_DAY0=True` 第 0 天全天重排，经验最优）
- `build_submission.py [--attack]`：生成单文件提交 `main_submission(_attack).py`（尾部内联守卫，
  入口 `kaggriculture_agent` 为最后可调用——注意 dict 保序，重定义旧名 `agent` 不改变键位置）
- 门控（M6 64 场景×双席位）：进攻版 vs V120 96.9% (+18.7k)，vs V76/V20 90.6%；防御版 vs V120 margin −16/局（镜像归零）
- 家族矩阵（8 seed×双席位）：进攻版对 6 个线上家族 12/16~16/16（+20k~+40k），对扰动同行 C 型 4/16 对轰近平
- 提交：55981569（attack）/ 55981574（defense），2026-09-03
