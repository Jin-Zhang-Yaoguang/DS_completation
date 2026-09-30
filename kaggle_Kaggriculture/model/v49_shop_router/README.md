# V49/V50:shop-world 与市场指纹路由(A 阶段)+ 块转移图(B 阶段地基)

目标(2026-09-07):crop 级模型——局内多样性(每局路径不同)+ 快爬 2500 → 稳步 2900。
社区巡视结论(见 survey 二.27-34):前沿收敛为「块级 public-state 路由」,修复层被证伪,
每回合恰好一次查表是托管硬约束。

## 核心证据(全部本目录可复现)

### 1. 嫁接定律(graft_test.py / graft_test2.py / block_graft.py)
- fam_F 与 rb7925 前 72 步唯一差异 = rb 让 1 号帮工闲置(无布局差异);
- **t=72 双向嫁接零损耗**(±33 金):fam_F 前缀 + rb 尾部 ≈ rb 本尊;
- **cand_0 ↔ fam_F 在 144/288/432/576 全边界完美互通**(diff ≤79 金)——cand_0 是
  fam_F 同生产结构的市场变体;
- 块转移图:{F,C} 任意边界互通;{F,C}→R 可在 72/144/288 切入(432/576 LOSSY);
  R→{F,C} 仅 288 可切。B 阶段块路由必须遵守此图。

### 2. 纯带 shop 分桶矩阵(world_matrix.py,20 对手 × 64 seed × 双席位)
- 纯带总胜率:rb 0.854 > rb_var 0.852 > cand_0 0.811 > fam_F 0.748 > famF_var621 0.627;
- 异构参考:keiz 0.562、OceanMix 0.334、**Crop_Dusta 0.055**——顶队带在纯带内战中
  极弱,其线上 2800 来自别处(执行层/结构逻辑),照搬带无用;
- 三带 shop 路由可实现 0.869(vs 单带 0.854),oracle 逐局 0.899;
- 短板行(所有 graftable 带都弱):cand_0 镜像 ≈52%、pert_2 61%、fam_A 66%、Andrey 69%。

### 3. 包级(带+武器层)holdout 门控(gate.py,seeds 2000-2015,640 局/包)
- **包级排序与纯带完全不同**:v41(fam_F+层)0.819 ≈ rb7925 包 0.812 ≈ v49 0.812;
- v41 包对 fam_F 镜像/OceanMix/fam_G/cand_1 全 100%(LEAD 镜像收割),rb 包只 69/75/88/97;
- rb 包强行:fam_A 69、fam_D 91、fam_E 62、pert_2 38(v41 仅 6);
- **结论:武器层×带交互决定包级强弱,门控必须在包级做;shop 特征看不见对手,
  吃不到 v41/rb 的行互补。**

### 4. 对手可观测性(fingerprint.py / market_fp.py)
- 农场瓦片指纹 t≤144 全场同质(MELO:12/PAST:6/WHEA:7)——**顶部不读对手的真正原因:
  农场端读不出来**;
- **市场端 t≤32 可分族**(dWHEAT t0/t1,含我方 -13/+8 贡献):
  13/8 同款(fam_F/rb/cand_0)= -27/+16;pert_1 -34/+23;Andrey -44/+33;keiz -57/+46;
  pert_2 -19/+8;cand_1 -18/+8;Jesse -14/+8;海洋无扰动(Ocean/G/A/D/E)= -14/+3;
- 海洋族内:OceanMix 有 t28 卖 3 麦特征;{G,E} 与 {A,D} 在 t2/t30 可分,G vs E 要 t148。

## 方案

- **v49**(dist/main.py):fam_F 前缀 + t=72 按首店闩锁(rb/c0)。holdout 0.812,与现役
  打平,未提交——教训:shop 单特征增益(纯带 +1.6pt)被包级层交互抹平。
- **v50**(dist_v50/main.py):两级路由——市场指纹优先(13/8 同款→F 尾镜像收割;
  dw0≤-31 大扰动→rb;Ocean t28 特征→F),shop 表兜底(BRUNCH/ICE_CREAM→c0,余 rb)。
  瞄准恢复 v41 的镜像 100% 行 + 保留 rb 的弱行修复。

## 运行

```
python build_v50.py                          # 生成 dist_v50/main.py
python gate.py out.jsonl "name=sub:path,..." 2000 16   # holdout 门控
python world_matrix.py out.jsonl tape1,tape2 1000 64   # 纯带矩阵
```
