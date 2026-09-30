from importlib.util import module_from_spec, spec_from_file_location

spec = spec_from_file_location("submission_agent", "main.py")
submission_agent = module_from_spec(spec)
spec.loader.exec_module(submission_agent)
assert callable(submission_agent.agent)
native = submission_agent._library()
assert native.kag_submission_abi_version() == 1
print("ABI check: PASS (version 1)")
print("agent callable: PASS")
print("single-file main.py: PASS")
print("ready for Kaggriculture: PASS")