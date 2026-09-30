import subprocess
import sys

# The engine below must be the build the schedule is specified against:
# under any other build the same action stream clears at different
# prices, and the changed cash changes which money-gated orders land.
# The preinstalled image lags, so the pin is installed and asserted.
ENGINE = "1.32.7"
subprocess.run(
    [sys.executable, "-m", "pip", "install", "-q",
     f"kaggle-environments=={ENGINE}"],
    check=True,
)
import kaggle_environments
assert kaggle_environments.__version__ == ENGINE, kaggle_environments.__version__
