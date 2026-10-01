"""生成仓库的复盘页面；Kaggriculture 的既有参赛复盘保留原有构建方式。"""
from pathlib import Path
import runpy

from render_competition_report import render

root = Path(__file__).resolve().parents[1]
kag = root / "kaggle_Kaggriculture" / "比赛总结"
ev = root / "kaggle_Predicting_Electric_Vehicle_Purchases" / "比赛总结"
runpy.run_path(str(kag / "build.py"), run_name="__main__")
render(kag / "优胜方案总结.md", kag / "assets/solution_sources.json", kag / "solutions.html", "Kaggriculture", "solutions")
render(ev / "参赛复盘.md", ev / "assets/review_data.json", ev / "index.html", "S6E9 电动车购买")
render(ev / "优胜方案总结.md", ev / "assets/solution_sources.json", ev / "solutions.html", "S6E9 电动车购买", "solutions")
