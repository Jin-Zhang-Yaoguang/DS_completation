# R4 原冻结微测文件来源核对

结论：**未找到原 manifest 登记的 50 项测试脚本或结果的 exact-SHA 副本；找到的是冻结后 51 项版本的两套相同副本。** 51 项脚本与结果内部 SHA 一致，且使用同一冻结候选，但不能替代原 50 项冻结证据。

本次只读检索与 SHA 计算，未运行测试，未修改原 manifest、main、测试脚本或结果。只新增本说明。

## 原冻结目标

依据 `candidates/V125-R4/manifest.json`：登记时间为 `2026-09-05T10:17:46.470966Z`，`micro_checks=50`。

| 对象 | 原 manifest 登记 SHA256 | 检索结果 |
|---|---|---|
| `test_microcases.py` | `251f9f72c6ebf91f6aa1efcc633bd881ec2c11346340f35c2792494b42338fc4` | 未找到对应字节副本 |
| `micro_results.json` | `a19234f71bcce645b58a90d097b2d40fe94f50f7e00a754768bbaa97add2d25b` | 未找到对应字节副本 |
| 冻结候选 | `8d3b634468d58c47df7c2c87644af04aa9d493e7c6381969866d4acfa3558431` | 51 项结果仍登记此候选 SHA；本问题是微测附件冻结不一致，不等于候选已改变 |

`iteration_registry.json` 也登记原结果 SHA `a19234f7…2d25b`。这些记录只能说明目标 SHA，不能凭记录恢复丢失文件或补齐证据。

## 找到的 51 项成对文件

结果 JSON 登记时间 `2026-09-05T10:17:57.177243Z`，比 manifest 时间晚约 10.7 秒；`checks=51`、`pass=true`，候选 SHA 仍为 `8d3b6344…558431`。

| 当前文件路径（相对本方案目录） | SHA256 | 字节数 |
|---|---|---:|
| `research/r4_contract_design/test_microcases.py` | `4a3a1ce03d9c1764580fe38386cfd0a19132c77a0367a2999aaf7e0b6e22d84a` | 15,773 |
| `research/r4_contract_design/micro_results.json` | `25bdb87d8850a1bcb686f60cf0eef0dce485223821213645cb9960637151e987` | 1,239,407 |
| `research/frozen_evidence/V125-R4/test_microcases.py` | `4a3a1ce03d9c1764580fe38386cfd0a19132c77a0367a2999aaf7e0b6e22d84a` | 15,773 |
| `research/frozen_evidence/V125-R4/micro_results.json` | `25bdb87d8850a1bcb686f60cf0eef0dce485223821213645cb9960637151e987` | 1,239,407 |

51 项结果中的 `harness_sha256` 正好是上述 `4a3a1ce0…2d84a`，与当前脚本字节匹配。`frozen_evidence/V125-R4/receipt.json` 已正确将脚本和结果的 `matches_freeze_manifest` 都标为 False。`HANDOFF.md` 的 51 项叙述对应这一后续版本，不对应 manifest 原先登记的 50 项附件。

另存的 `micro_results_invalidated_crossday_expectation.json` 是 41 项、`pass=false` 的早期失败结果，SHA `01fe0282d187ef150ed4e0fb2fb072f1fab9849b2c59dc342ee13c4ef7b8ceef`，候选及 harness 也与冻结版本不同，不能充作缺失的 50 项证据。

## 检索覆盖

- 使用 `rg --files --hidden` 枚举本方案 `research/` 与 `candidates/`，对当时 **637 个文件、35,661,535 字节**逐个计算 SHA；所有文件均小于 2 MB，没有因大小跳过。
- 对其中 **99 个 gzip 文件的解压内容、99,052,022 字节**另算 SHA；同样未匹配原两个冻结目标。它们是已保存的局部审计日志 / 状态数据，没有运行或重建比赛。
- 在 Kaggriculture 目录及当前仓库查找 R4 / micro / test / snapshot / backup 文件名，未找到额外的 R4 微测副本。
- `git ls-files` 和 `git log --all -- <两个原路径>` 均无这两份文件的记录，不能通过当前已知 Git 路径历史取回。没有声称搜索了系统备份、其他机器或未引用 Git 对象。

因此本范围内应保留 **`ORIGINAL_R4_MICRO_FREEZE_ARTIFACTS_NOT_FOUND`** 缺口，并将当前 51 项材料单列为“同候选的冻结后补充微测，内部哈希一致”。本次不回写原 manifest，不把新快照改名成原文件，也不依据相近检查数或相同候选 SHA 宣称原冻结证据已恢复。
