import pandas as pd

route_rules = pd.DataFrame([
    (360, "first shop is BAKERY and fertilizer inventory is low", "alternate route"),
    (360, "first shop is PET_CAFE and rival plant count is moderate", "alternate route"),
    (360, "otherwise", "anchor route"),
], columns=["step", "public condition", "route"])
print(route_rules.to_string(index=False))