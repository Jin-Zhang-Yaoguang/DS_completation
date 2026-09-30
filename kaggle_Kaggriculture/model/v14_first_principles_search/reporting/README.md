# V14 可复现报告资产

这组脚本只生成分析资产，不会运行新 screen/confirm、不会读取 test outcome、不会提交 Kaggle。

从项目根目录执行：

```bash
PYTHONPYCACHEPREFIX=/tmp/v14-report-pycache \
  .venv/bin/python \
  kaggle_Kaggriculture/model/v14_first_principles_search/reporting/build_v14_notebook.py

PYTHONPYCACHEPREFIX=/tmp/v14-report-pycache \
  .venv/bin/python \
  kaggle_Kaggriculture/model/v14_first_principles_search/reporting/execute_notebook.py \
  kaggle_Kaggriculture/model/v14_first_principles_search/v14_analysis.ipynb

PYTHONPYCACHEPREFIX=/tmp/v14-report-pycache \
  .venv/bin/python \
  kaggle_Kaggriculture/model/v14_first_principles_search/reporting/build_v14_report.py
```

若线上提交后另存了 receipt，可显式传入：

```bash
PYTHONPYCACHEPREFIX=/tmp/v14-report-pycache \
  .venv/bin/python \
  kaggle_Kaggriculture/model/v14_first_principles_search/reporting/build_v14_report.py \
  --submission-json /absolute/path/to/v14_submission_status.json
```

输出：

- `../v14_analysis.ipynb`：已从头执行、带输出的可复现 notebook；
- `report_snapshot.json`：Notebook 与 HTML 共用的证据快照；
- `artifact.json`：canonical Data Analytics report artifact；
- `v14_technical_report.html`：自包含 portable HTML；
- `report_build_receipt.json`：builder/verification receipt。
