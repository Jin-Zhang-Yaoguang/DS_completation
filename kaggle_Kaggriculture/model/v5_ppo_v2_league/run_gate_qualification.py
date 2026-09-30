from pathlib import Path

from train_ppo import _qualify_snapshot


if __name__ == "__main__":
    path = Path("checkpoints/full28q_s17/policy_iter_005.npz")
    print(_qualify_snapshot(path, workers=4, seeds=16))
