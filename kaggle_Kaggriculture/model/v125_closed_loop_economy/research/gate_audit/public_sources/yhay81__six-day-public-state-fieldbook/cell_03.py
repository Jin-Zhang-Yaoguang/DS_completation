import shutil
import subprocess
import tarfile

subprocess.run(
    [
        "g++", "-O3", "-std=c++17", "-shared", "-fPIC",
        "-I.", "-o", "/kaggle/working/agent.so",
        "policy.cpp", "submission_bridge.cpp",
    ],
    cwd=root,
    check=True,
)
shutil.copyfile(root / "agent_main.py", "/kaggle/working/main.py")
archive = "/kaggle/working/sixday-publicstate-agent.tar.gz"
with tarfile.open(archive, "w:gz") as bundle:
    bundle.add("/kaggle/working/main.py", arcname="main.py")
    bundle.add("/kaggle/working/agent.so", arcname="agent.so")
print("Built main.py, agent.so, and the top-level submission archive")
