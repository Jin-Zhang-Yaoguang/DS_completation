import hashlib
import importlib.util
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

def pip_install(*packages):
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", *packages], check=True)
    importlib.invalidate_caches()

packages = {"numpy": "numpy", "pandas": "pandas", "sklearn": "scikit-learn>=1.3",
            "joblib": "joblib", "matplotlib": "matplotlib"}
missing = [package for module, package in packages.items() if importlib.util.find_spec(module) is None]
if missing:
    pip_install(*missing)

encoder_check = subprocess.run(
    [sys.executable, "-c", "from sklearn.preprocessing import TargetEncoder"], capture_output=True)
if encoder_check.returncode:
    if any(name in sys.modules for name in ("sklearn", "numpy", "scipy")):
        raise RuntimeError("This session needs scikit-learn >=1.3. Start a fresh session before updating it.")
    pip_install("scikit-learn>=1.3")

probe = subprocess.run(
    [sys.executable, "-c", "import ctboost,json; print(json.dumps(ctboost.build_info()))"],
    capture_output=True, text=True)
try:
    installed = json.loads(probe.stdout.strip().splitlines()[-1])
except (ValueError, IndexError):
    installed = {}

if any(installed.get(key) != "0.1.58" for key in ("version", "package_version")) or not installed.get("cuda_enabled"):
    if "ctboost" in sys.modules:
        raise RuntimeError("Restart the notebook session, then Run All to load the CTBoost GPU build.")
    tag = f"cp{sys.version_info.major}{sys.version_info.minor}"
    wheel_hashes = {
        "cp310": "c0a67a5e2d91d74c6f72566f79b3d4da4d8145c0a94b004c2603b0f41c94de79",
        "cp311": "3ee9a28777d1a3b7afdaadaeb7a46204164cdaffd8493bfcf9990a56bc815a61",
        "cp312": "ff868712ac6b93f9038c646aedfe9fba0b9a9e7b95297ae0aa211157ee014a8b",
        "cp313": "36edbf6674a2cc6ce5fdf21caba40fa589e672712d20381dce88b70defd8faeb",
        "cp314": "d334bba5296731800ff24f782c939e8631a0afecc585a95277987357e443136c",
    }
    if tag not in wheel_hashes or not sys.platform.startswith("linux"):
        raise RuntimeError("Run this notebook in a Kaggle Linux GPU session with Python 3.10–3.14.")
    wheel = Path("/tmp") / f"ctboost-0.1.58-{tag}-{tag}-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl"
    url = "https://github.com/captnmarkus/ctboost/releases/download/v0.1.58/" + wheel.name
    for attempt in range(3):
        try:
            if not wheel.exists() or hashlib.sha256(wheel.read_bytes()).hexdigest() != wheel_hashes[tag]:
                request = urllib.request.Request(url, headers={"User-Agent": "CTBoost-notebook"})
                with urllib.request.urlopen(request, timeout=120) as response:
                    wheel.write_bytes(response.read())
            if hashlib.sha256(wheel.read_bytes()).hexdigest() != wheel_hashes[tag]:
                raise RuntimeError("Incomplete wheel download. Check Internet access and rerun setup.")
            break
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2)
    pip_install("--force-reinstall", "--no-deps", str(wheel))


import gc
import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sklearn
import ctboost
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import TargetEncoder
from IPython.display import display

build = ctboost.build_info()
if ctboost.__version__ != "0.1.58" or any(build.get(key) != "0.1.58" for key in ("version", "package_version")) or not build.get("cuda_enabled"):
    raise RuntimeError("Restart the session and Run All to load CTBoost 0.1.58 GPU.")
gpu_data = np.random.default_rng(42).normal(size=(128, 4)).astype(np.float32)
gpu_check = ctboost.CTBoostClassifier(iterations=3, max_depth=2, task_type="GPU", verbose=False)
gpu_check.fit(gpu_data, (gpu_data[:, 0] > 0).astype(np.int32))
assert gpu_check.get_booster()._handle.export_state()["task_type"] == "GPU"
del gpu_check, gpu_data
plt.rcParams.update({"figure.figsize": (9, 4), "axes.spines.top": False, "axes.spines.right": False})
print(f"CTBoost {ctboost.__version__} GPU is ready | scikit-learn {sklearn.__version__}")


