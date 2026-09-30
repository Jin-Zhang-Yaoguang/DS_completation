"""K3 动物经济 patch(只在刀间、driver 回滚后应用):
 a) wheat_per_animal(0-3,0=旧):麦份额下限 = 该值 × 动物数(饲料自给,榜首 17 动物配 20-38 麦地)
 b) fert_mask(0-15,15=旧):按位允许施肥的作物 1 麦 2 瓜 4 番茄 8 草莓(麦/番茄施肥 100 一份不回本)
 c) 边界:pasture_target 上界 14->20,cow_until 上界 10->20,goose_until 上界 20->26
"""
import re
from pathlib import Path
V = Path(__file__).resolve().parents[1]
p = V / "scheduler.py"; s = p.read_text()
s = s.replace("    sell_first = 0\n", "    sell_first = 0\n    wheat_per_animal = 0   # K3:麦份额下限 = 值 × 动物数(0 = 旧规则)\n    fert_mask = 15         # K3:允许施肥的作物位掩码 1 麦 2 瓜 4 番茄 8 草莓(15 = 旧规则)\n", 1)
old = '''        if d <= 24 and cur.get("WHEAT", 0) < getattr(c, "share_wheat", 10):
            return "WHEAT"'''
new = '''        wheat_sh = getattr(c, "share_wheat", 10)
        wpa = getattr(c, "wheat_per_animal", 0)
        if wpa:
            n_an = sum(1 for y2 in range(10) for x2 in range(10)
                       if isinstance(self.tiles[y2][x2], dict) and self.tiles[y2][x2].get("animal"))
            wheat_sh = max(wheat_sh, wpa * n_an)
        if d <= 24 and cur.get("WHEAT", 0) < wheat_sh:
            return "WHEAT"'''
assert old in s; s = s.replace(old, new)
old = '''                        if want:
                            tasks.append((14, (x, y), "FERTILIZE", "FERTILIZER", "fert"))'''
new = '''                        fm = getattr(c, "fert_mask", 15)
                        bit = {"WHEAT": 1, "MELON": 2, "TOMATO": 4, "STRAWBERRY": 8}.get(crop, 0)
                        if want and (fm & bit or bit == 0):
                            tasks.append((14, (x, y), "FERTILIZE", "FERTILIZER", "fert"))'''
assert old in s; s = s.replace(old, new)
p.write_text(s)
q = V / "space.py"; t = q.read_text()
t = t.replace('"pasture_target": (4, 14)', '"pasture_target": (4, 20)').replace('"cow_until": (3, 10)', '"cow_until": (3, 20)').replace('"goose_until": (10, 20)', '"goose_until": (10, 26)')
anchor = '    "inertia": (0, 1), "core_ring": (0, 1), "day_chain": (0, 1),\n'
assert anchor in t
t = t.replace(anchor, anchor + '    # K3 动物经济:麦地随动物数、施肥作物掩码\n    "wheat_per_animal": (0, 3), "fert_mask": (0, 15),\n')
t = re.sub(r'DEFAULTS: dict\[str, int\] = \{', 'DEFAULTS: dict[str, int] = {"wheat_per_animal": 0, "fert_mask": 15, ', t)
q.write_text(t)
print("K3 patched")
