# V12 v4 screen 决策记录

- 数据：新 18-source panel，日期 `6/6/6`，与 v3 screen、formal100 均零重叠。
- 完整性：29 pairs、1,044 games、每 source 双席位、全部 `DONE/DONE`、0 error；
  `screen_audit.integrity_passed=true`。
- A (`v12a_terminal_branch_guard`)：direct-parent score `69.444%`；共同对手
  paired uplift `+3.968pp`；最差单一对手 `-2.778pp`（`baseline_v8`）。
  direct/common 通过，worst `-2pp` guardrail 失败，`screen_formal_ready=false`。
- B-v2 (`v12b_v2_winrisk_feedback_gate`)：direct-parent score `50.000%`；共同对手
  paired uplift `+0.397pp`；最差单一对手 `0pp`；三项 gate 全通过，
  `screen_formal_ready=true`。
- B-v2 对父策略的 252 个同对手/source/seat 逐局转移：`L→L=128`、`L→W=1`、
  `T→T=15`、`W→W=108`、`W→L=0`；7 类对手得分均未下降。
- 当前冻结协议以 A 为 fixed-sequence primary，且 formal 入口要求全部 screen-ready，
  因而整体仍为 fail-closed；未创建任何 formal result 文件。
- `validation_config.json` SHA256：
  `e65f6a447a479757a1d5ccfafb7736ae03a4fc41e5d3720373342d9d80a69c86`
- `screen_panel.json` SHA256：
  `da4f2b2edbb74fa0d2f3c9866d375e3381c96721a0b637b05f56a77df1b9df00`
- `screen_audit.json` SHA256：
  `649b146113bad72cd69f0abc04b9c259b2edfd798fda3a620c20ca92118db81f`

如需让 B-v2 单独进入 formal，必须在 formal100 尚未打开时另行冻结 B-only 主检验
协议；不得直接绕过当前 A-first / all-candidate screen gate。

