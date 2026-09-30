# WATER 证书 v1

阶段 A 只检查当前日已到场工人的无材料 WATER 服务。它不是经营策略，不改变 R9 准入。生成器在 `scheduler.py`，独立检查器在 `checker.py`，后者不得导入生成器或候选。

`problem`：

```json
{
  "schema": "r10-water-problem-v1",
  "day": 2,
  "start_step": 48,
  "end_step": 65,
  "board_size": 10,
  "units": [{"unit": 0, "start": [4,4], "available_from": 48,
             "available_until": 65, "return_to": [4,4]}],
  "services": [{"service_id": "water:2:MELON:0:3,4",
                "asset_id": {"position": [3,4], "crop": "MELON", "planted_day": 0},
                "position": [3,4], "earliest_step": 48, "deadline_step": 65}],
  "eligible_water_positions": [[3,4]],
  "observation_evidence": {
    "step":48,"day":2,"hour":0,
    "units":[{"unit":0,"position":[4,4]}],
    "tiles":[{"position":[3,4],"tile":{"kind":"PLANT","crop":"MELON",
      "planted_day":0,"watered_today":false,"max_lifespan_step":312}}]
  }
}
```

end/deadline/available_until 均包含端点；禁止跨日，day29 最晚 step718。unit0 是农夫，其它 unit 对应 hands 下标+1；阶段 A 的 adapter 只能从真实当前观测读取起点和已存在的 unit。`return_to=null` 表示没有返仓要求；其它值是必须到达的明确坐标。通用checker精确检查这个终点；当前adapter只允许四个仓口作为返仓终点，不将起点替换为最近仓。该 schema 不允许市场、雇工、新工、物料或商品搬运。

证书：

```json
{
  "schema": "r10-water-certificate-v1",
  "status": "FEASIBLE",
  "problem_sha256": "canonical problem hash",
  "actions": [{"step":48,"unit":0,"action":["WEST"],"service_id":null}],
  "scheduled_service_ids": ["water:2:MELON:0:3,4"],
  "terminal_positions": {"0":[4,4]},
  "reason": null
}
```

canonical hash 为 `sha256(json.dumps(problem,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode())`。FEASIBLE 必须对每个工人的全部可用时槽显式给一动作，动作仅四向 MOVE、PASS、WATER；WATER 带唯一 service_id。每个服务恰好一次、地点/asset/资格对应，且符合 earliest/deadline；最终位置及返仓要求一致。不得以 `completed_service_ids` 替代真实动作。`NO_CERTIFICATE` 不是 checker 通过，也不证明不存在其它路线。

检查器 `check_certificate(problem,certificate)` 返回 `{valid, errors:[{code,detail,...}], stats}`。它独立核 unit 起点、服务资格/出生身份与 observation_evidence 相同，不能只相信裸 eligible 集合。该证据真实性仍由adapter原obs及SHA负责。`max_lifespan_step>=0` 时服务deadline必须裁到该step（单位动作先于该步末decay）；如果已小于当前step，阶段A保守拒绝。-1表示当前无预设decay时点。服务不能因开始时尚活而忽略到达前衰退。官方短控制的成功 WATER 与末坐标，才是实际完成证据。给证书写 `scheduled_service_ids`，不写伪造的完成收据。
