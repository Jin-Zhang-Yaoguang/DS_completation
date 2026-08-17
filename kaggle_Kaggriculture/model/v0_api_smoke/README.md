# v0_api_smoke

首个可提交的 Kaggriculture 基线。目标不是冲榜，而是用最小策略验证完整 API、720 回合稳定性和提交包格式。

## 策略

- 无状态、仅依赖当前 observation，双方席位和进程复用时不会串局。
- 管理初始解锁区内、靠近仓库的 3 块小麦田。
- 每日优先浇水，成熟后集中收获并送回仓库，再通过市场出售。
- 第 29 天只执行能够在终局前完成出售的收获链。
- 不雇临时工，但总会为已有 `hands` 返回等长的 `PASS` 动作。
- 异常 observation 会降级为完整的安全 `PASS`，不输出日志、不使用网络或第三方依赖。

## 文件

- `main.py`：自包含提交 Agent；根入口为文件中最后定义的 `agent(obs)`。
- `smoke_test.py`：合成边界用例、动作合法性审计、短局及 720 回合对局矩阵。
- `build_submission.py`：生成可复现的 `submission.tar.gz`，并检查归档根目录只有 `main.py`。
- `submission.tar.gz`：可直接上传 Kaggle 的提交包。

## 本地运行

从仓库根目录执行：

```bash
env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python \
  kaggle_Kaggriculture/model/v0_api_smoke/smoke_test.py

env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python \
  kaggle_Kaggriculture/model/v0_api_smoke/build_submission.py
```

测试环境为 Python 3.12 与 `kaggle-environments==1.32.2`。提交代码本身只使用 Python 内置能力。
