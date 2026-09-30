"""只由冻结 R3 副本和执行层组装独立单文件，不运行父 agent。"""
from pathlib import Path
import hashlib

p = Path(__file__).resolve().parent
s = (p / 'parent_r3.py').read_text()
assert hashlib.sha256(s.encode()).hexdigest() == 'd8b964487d2d635a680d0a33d83db054a593619eb29bed76bf3fcb80000df71d'
a, b = s.index('def allocate('), s.index('def market_orders(')
s = s[:a] + (p / 'execution_layer.py').read_text() + '\n\n' + s[b:]
s = s.replace('CANDIDATE_ID = "V125-R3"', 'CANDIDATE_ID = "V125-R4-PROTOTYPE"')
s = s.replace('    confirm_orders(st, observation)', '    confirm_execution(st, observation)\n    confirm_orders(st, observation)')
s = s.replace('"purchase_misses": st["procurement"]', '"purchase_misses": st["procurement"],\n                        "active_contracts": st.get("contracts", {}),\n                        "contract_events": st.get("contract_events", [])')
s = s.replace('"""V125：由可见状态生成经营目标、任务和动作，所有完成以观测确认。"""', '"""V125-R4 执行合约原型：同 R3 经营谱系，动作收据推进短期合约。"""')
a, b = s.index('def agent('), s.index('def diagnostics(')
s = s[:a] + s[b:].rstrip() + '\n\n\n' + s[a:b].rstrip() + '\n'
compile(s, str(p / 'main.py'), 'exec')
(p / 'main.py').write_text(s)
print(hashlib.sha256(s.encode()).hexdigest())
