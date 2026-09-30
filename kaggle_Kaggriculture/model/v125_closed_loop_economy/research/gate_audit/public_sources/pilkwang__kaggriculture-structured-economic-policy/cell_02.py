from pathlib import Path
from IPython.core.magic import register_cell_magic

WORK_DIR = (
    Path("/kaggle/working")
    if Path("/kaggle/working").is_dir()
    else Path.cwd() / "policy_bundle_output"
)
WORK_DIR.mkdir(parents=True, exist_ok=True)
MAIN_PATH = WORK_DIR / "main.py"

@register_cell_magic
def agentfile(line, cell):
    mode = "a" if line.strip() == "append" else "w"
    with MAIN_PATH.open(mode, encoding="utf-8") as handle:
        handle.write(cell)
