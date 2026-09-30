# V12 screen-only 决策记录

- 状态：`frozen_v3` 仅作为 V12A / V12B-v1 的独立 screen 证据保留；未打开 formal panel。
- 决策：V12A 通过 screen，V12B-v1 淘汰并重做；两者都没有取得正式晋级结论。
- 完整性：29 pairs、1,044 games、18 个 source（日期 6/6/6）、双席位、全部
  `DONE/DONE`、0 error；`screen_audit.integrity_passed=true`。
- V12A：direct-parent score `0.77778`；共同对手 paired uplift `+0.03968`；
  最差单对手 uplift `0.00000`；三项 screen gate 全部通过。
- V12B-v1：direct-parent score `0.52778`；共同对手 paired uplift `-0.01190`；
  最差单对手 uplift `-0.05556`；common 与 worst gate 失败。
- `validation_config.json` SHA256：
  `e93571f88271e4819fa87104eb08c98e1ca54eeb7c9a9bb825776e239919de9f`
- `screen_audit.json` SHA256：
  `e5afb49691c597efb0d9ae58d2930805a34f882f0774137d4521dbb63eeddb13`
- V12A archive SHA256：
  `88749064c1c87c26d3c13926f7d6d5c0d8681adc94c02b616db02d5cad53c6e2`
- V12B-v1 archive SHA256：
  `385961583deaa8f3c225f2a6a22dd0a6be55336345f2b69ddaf000a7bb76eef9`

后续 V12B-v2 必须使用新的 `frozen_v4/` 与 `runs_v4/`，并把其全部 smoke、
control、clean-match、package-QA 种子纳入 exposure exclusion；不得 resume 本目录结果。

