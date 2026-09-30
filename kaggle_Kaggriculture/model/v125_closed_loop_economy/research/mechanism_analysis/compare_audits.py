#!/usr/bin/env python3
"""比较同seed同seat的已存机制账本，不增加引擎或候选调用。"""
import argparse, gzip, hashlib, json, statistics
from pathlib import Path

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def read(d):
    m=json.load(open(d/'audit_manifest.json'));a=json.load(open(d/'analysis.json'));f=json.load(open(d/'findings.json'));v=json.load(open(d/'validation.json'))
    assert v['all_item_inventory_conservation_zero_residual'] and v['terminal_full_snapshot_matches_source']
    s=m['candidate_seat'];x=a['seats'][s];y=f['seats'][s];n=x['denominators'];term=json.load(open(d/'terminal_states.json'))[s]
    daily=json.load(gzip.open(d/'daily_states.json.gz'))
    metrics={'cash':a['cash_result'][s],'plantings':n['plantings_all'],'planting_day_eod_exposures':n['planting_day_eod_observed'],
             'planting_day_watered':n['planting_day_watered'],'planting_day_not_watered':n['planting_day_not_watered'],
             'plant_eod_exposures':n['plant_eod_exposures'],'drought_deaths_all':n['plant_eod_drought_deaths'],
             'drought_deaths_still_productive':y['drought_loss_still_productive_count'],'drought_deaths_exhausted_zero':y['drought_loss_exhausted_zero_count'],
             'animal_eod_exposures':n['animal_eod_exposures'],'animal_unfed_eod_exposures':n['animal_unfed_eod_exposures'],
             'animal_escapes':n['animal_eod_escapes'],'animal_placed':n['animal_placed'],
             'animal_inventory_step_integral':y['animal_inventory_step_integral'],'animal_delay_median':x['animal_placement']['delay_steps_median'],
             'animal_delay_max':x['animal_placement']['delay_steps_max'],'animal_no_product_window':y['animal_product_window_missed_count'],
             'eod_overflow_quantity':sum(x['overflow']['eod_qty'].values()),'eod_overflow_quote_value':x['overflow']['eod_quote_value'],
             'terminal_mature_unharvested_quantity':sum(x['terminal_assets']['mature_unharvested_qty'].values()),
             'terminal_mature_quote_value':x['terminal_assets']['mature_quote_value'],'nonpass_nonmove_count':y['nonpass_nonmovement_submitted'],
             'unchanged_nonpass_count':y['unchanged_nonpass_count_all_ops'],'wheat_bought':x['inventory_balance'].get('WHEAT',{}).get('buy_product',0),
             'wheat_sold':x['inventory_balance'].get('WHEAT',{}).get('sell',0),'wheat_feed':x['inventory_balance'].get('WHEAT',{}).get('feed',0),
             'wheat_same_step_both_buy_sell':y['wheat_both_buy_sell_same_step_count']}
    return {'key':(m['seed'],s),'directory':str(d),'candidate_entry_sha256':m['candidate_entry_sha256'],'source_game_key':a['source_game_key'],
            'source_trace_sha256':m['source_trace']['sha256'],'metrics':metrics,'shops':term['town']['unlocked_shops'],
            'daily_shops':{z['recorded_step']:z['states'][s]['town']['unlocked_shops'] for z in daily},
            'inputs':{p.name:sha(p) for p in [d/'audit_manifest.json',d/'analysis.json',d/'findings.json',d/'validation.json']}}

def aggregate(rows):
    z={k:statistics.mean(r['metrics'][k] for r in rows) for k in rows[0]['metrics'] if all(r['metrics'][k] is not None for r in rows)}
    sums={k:sum(r['metrics'][k] for r in rows) for k in ['planting_day_eod_exposures','planting_day_watered','plant_eod_exposures','drought_deaths_all','plantings','drought_deaths_still_productive','animal_eod_exposures','animal_escapes','animal_unfed_eod_exposures']}
    ratios={'planting_day_watered':sums['planting_day_watered']/sums['planting_day_eod_exposures'] if sums['planting_day_eod_exposures'] else None,
            'all_drought_deaths_per_plant_eod':sums['drought_deaths_all']/sums['plant_eod_exposures'] if sums['plant_eod_exposures'] else None,
            'all_drought_deaths_per_planting':sums['drought_deaths_all']/sums['plantings'] if sums['plantings'] else None,
            'still_productive_deaths_per_planting':sums['drought_deaths_still_productive']/sums['plantings'] if sums['plantings'] else None,
            'animal_escapes_per_animal_eod':sums['animal_escapes']/sums['animal_eod_exposures'] if sums['animal_eod_exposures'] else None}
    return {'games':len(rows),'mean_metrics':z,'pooled_numerators_denominators':sums,'pooled_mechanism_rates_descriptive_only':ratios}

def main():
    p=argparse.ArgumentParser();p.add_argument('--left',nargs='+',type=Path,required=True);p.add_argument('--right',nargs='+',type=Path,required=True)
    p.add_argument('--left-name',required=True);p.add_argument('--right-name',required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    left=[read(x.resolve()) for x in args.left];right=[read(x.resolve()) for x in args.right]
    L={tuple(x['key']):x for x in left};R={tuple(x['key']):x for x in right};assert L.keys()==R.keys() and len(L)==len(left)==len(right)
    pairs=[]
    for key in sorted(L):
        l,r=L[key],R[key];shared=sorted(set(l['daily_shops'])&set(r['daily_shops']))
        first=next((step for step in shared if l['daily_shops'][step]!=r['daily_shops'][step]),None)
        delta={k:r['metrics'][k]-v for k,v in l['metrics'].items() if v is not None and r['metrics'][k] is not None}
        pairs.append({'seed':key[0],'seat':key[1],'left':l,'right':r,'delta':delta,'same_final_shop_sequence':l['shops']==r['shops'],
                      'first_different_shops_recorded_step':first,'first_different_shops_day':first//24 if first is not None else None})
    overall={'left':aggregate(left),'right':aggregate(right),'cash_improved_pairs':sum(z['delta']['cash']>0 for z in pairs),
             'cash_tied_pairs':sum(z['delta']['cash']==0 for z in pairs),'cash_mean_delta':statistics.mean(z['delta']['cash'] for z in pairs),
             'cash_median_delta':statistics.median(z['delta']['cash'] for z in pairs),'shop_sequences_changed_pairs':sum(not z['same_final_shop_sequence'] for z in pairs)}
    seats={str(s):{'left':aggregate([x for x in left if x['key'][1]==s]),'right':aggregate([x for x in right if x['key'][1]==s]),
                   'cash_mean_delta':statistics.mean(z['delta']['cash'] for z in pairs if z['seat']==s)} for s in sorted({k[1] for k in L})}
    out={'evidence_role':'PAIRED_EXISTING_TRACE_MECHANISM_DIAGNOSTIC_NOT_NEW_MATCH_OR_PROMOTION',
         'left_name':args.left_name,'right_name':args.right_name,'games_per_candidate':len(pairs),'unique_seeds':len({k[0] for k in L}),
         'mechanism_rates_policy':'按生物体日/播种事件并列描述，两个席位分开。并非独立同分布样本，不以这些率替代冻结门。',
         'shops_policy':'相同seed并不保证策略变动后商店完全相同；自然日终RNG会受场地状态影响。本表保留真实过程并披露商店变化，现金差不能全部归因于单个生产机制。',
         'overall':overall,'by_seat':seats,'pairs':pairs,'engine_runs':0,'candidate_calls':0}
    args.output.parent.mkdir(parents=True,exist_ok=True);dump(args.output.with_suffix('.json'),out)
    lines=[f'# {args.left_name} 与 {args.right_name}：已存动作机制比较','',f'每候选{len(pairs)}局、{out["unique_seeds"]}个seed；只比较已生成trace，新增候选调用0。现金改善{overall["cash_improved_pairs"]}/{len(pairs)}，平均差{overall["cash_mean_delta"]:+.1f}，中位差{overall["cash_median_delta"]:+.1f}。',
           f'相同seed/seat中有{overall["shop_sequences_changed_pairs"]}/{len(pairs)}的最终商店序列不同。自然RNG保留；此处不把现金差全部归因于单个机制。','',
           '| seed | seat | 左现金 | 右现金 | 现金差 | 在途积分 左→右 | 仍有产能缺水 左→右 | 逃逸 左→右 | 溢出件数 左→右 | 成熟残留标值 左→右 | 商店改变 |',
           '|---:|---:|---:|---:|---:|---|---|---|---|---|---|']
    for z in pairs:
        l,r=z['left']['metrics'],z['right']['metrics']
        arrow=lambda k:f'{l[k]}→{r[k]}'
        lines.append(f'| {z["seed"]} | {z["seat"]} | {l["cash"]:.0f} | {r["cash"]:.0f} | {z["delta"]["cash"]:+.0f} | {arrow("animal_inventory_step_integral")} | {arrow("drought_deaths_still_productive")} | {arrow("animal_escapes")} | {arrow("eod_overflow_quantity")} | {arrow("terminal_mature_quote_value")} | {"是" if not z["same_final_shop_sequence"] else "否"} |')
    lines+=['','| 指标（每局均值） | 左 | 右 |','|---|---:|---:|']
    labels={'animal_inventory_step_integral':'动物在途积分','animal_no_product_window':'没有产出窗口的放置动物数','drought_deaths_still_productive':'仍有产能缺水死亡','drought_deaths_all':'全部缺水消失','animal_escapes':'动物逃逸','eod_overflow_quantity':'EOD丢弃件数','eod_overflow_quote_value':'EOD丢弃当时报价标值','terminal_mature_quote_value':'终局成熟未收获标值','wheat_same_step_both_buy_sell':'小麦同一步买卖次数'}
    for k,label in labels.items():lines.append(f'| {label} | {overall["left"]["mean_metrics"][k]:.3f} | {overall["right"]["mean_metrics"][k]:.3f} |')
    lines+=['','两个席位的分母、完整逐局指标与原动作带SHA见同名JSON。尾期零产量退出候选单列，没有事后豁免。丢弃/残留标值不是可保证实现的现金。来源现金与交易/采收及物料守恒校验均通过；本比较不授予G1、G2或金牌资格。']
    args.output.with_suffix('.md').write_text('\n'.join(lines)+'\n')
    dump(args.output.with_suffix('.manifest.json'),{'script_path':str(Path(__file__).resolve()),'script_sha256':sha(__file__),'output_sha256':sha(args.output.with_suffix('.json')),
                                                   'source_audits':{x['directory']:x['inputs'] for x in left+right}})
    print(json.dumps({'output':str(args.output.with_suffix('.json')),'overall':overall},ensure_ascii=False))

if __name__=='__main__':main()
