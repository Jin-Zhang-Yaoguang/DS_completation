# Kaggriculture official playable visualizer

This directory contains an unmodified production build of Kaggle's official
React playable visualizer:

- Upstream: <https://github.com/Kaggle/kaggle-environments/tree/master/kaggle_environments/envs/kaggriculture/visualizer/playable>
- Upstream commit: `28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c`
- Package manager: `pnpm@9.15.3` (the version pinned by the upstream repository)
- Build command: `pnpm --filter @kaggle-environments/kaggriculture-playable-visualizer build`

The PyPI `kaggle-environments==1.32.7` wheel includes `dist/index.html` but
omits the required `gameWorker-B6akpgl_.js`. The files under `dist/` were built
from the official source so the playable game can initialize correctly.

Run from the workspace root:

```bash
.venv/bin/python -m http.server 8766 --bind 127.0.0.1 \
  --directory kaggle_Kaggriculture/official_playable/dist
```

Then open <http://127.0.0.1:8766/>.

The official UI currently offers `Random` and `Starter` as AI opponents. The
separate app under `../playground/` is the version connected to our latest
Python submission bot.
