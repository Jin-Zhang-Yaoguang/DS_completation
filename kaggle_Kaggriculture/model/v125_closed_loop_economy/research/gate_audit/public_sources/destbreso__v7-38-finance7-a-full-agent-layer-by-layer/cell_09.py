import subprocess, sys

# One command, no flags of mine beyond -O3 and the C++17 the sources need.
# Verified against the binary I actually field: a library built exactly this
# way reproduces the shipped agent's bank to the dollar on every game tested.
LIB = "agent.dylib" if sys.platform == "darwin" else "agent.so"   # Kaggle is Linux
cmd = ["g++", "-O3", "-std=c++17", "-shared", "-fPIC",
       "-o", LIB, "submission_bridge.cpp", "policy.cpp"]
print(" ".join(cmd))
r = subprocess.run(cmd, cwd=WORK, capture_output=True, text=True)
print(r.stdout, r.stderr)
r.check_returncode()

so = WORK / LIB
print(f"{LIB}  {so.stat().st_size:,} bytes")

# It must LOAD and answer the ABI, or the submission scores nothing in a way
# the leaderboard will not explain to you.
import ctypes
lib = ctypes.CDLL(str(so))
lib.kag_submission_abi_version.restype = ctypes.c_uint32
print("ABI version:", lib.kag_submission_abi_version())
assert int(lib.kag_submission_abi_version()) == 1
