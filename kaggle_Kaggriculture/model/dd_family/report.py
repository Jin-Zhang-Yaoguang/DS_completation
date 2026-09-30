"""Build a current evidence ledger; qualification requires both frozen complete panels."""
from pathlib import Path
import json,datetime
B=Path(__file__).resolve().parent
def main():
    reg=json.loads((B/'registry.json').read_text());lines=['# dd 家族实验记录','',
        '目标：3 个独立通过全 y68 家族门控与新种子确认的模型。当前没有模型通过。','',
        '对手池：33 个源码哈希不同的 y68，官方引擎 1.32.7。开发结果不能代替门控。','',
        '| 版本 | 技术变化 | 开发面板 | 胜/局 | 平均胜差 | 状态 |','|---|---|---|---:|---:|---|']
    for v in reg['versions']:
        d=B/v['version'];runs=[]
        for p in (d/'runs').glob('*/summary.json'):
            s=json.loads(p.read_text());plan=json.loads((p.parent/'plan.json').read_text())
            if plan['panel']=='development':runs.append((s['completed'],len(plan['seeds']),p,s))
        if runs:
            _,seed_count,p,s=max(runs,key=lambda z:(z[0],z[1],str(z[2])));panel=f'{p.parent.name} / {seed_count} seeds';score=f"{s['wins']}/{s['completed']}";margin=f"{s['mean_margin']:,.2f}"
        else:score='—';margin='—';panel='—'
        lines.append(f"| {v['version']} | {v['method']} | {panel} | {score} | {margin} | {v['status']} |")
    lines+=['','## 已确认的边界','',
        '- dda/ddb/ddc/ddd/dde/ddf 是非参数原型模仿或执行对照，不是神经网络权重蒸馏。',
        '- ddg/ddh 是从回放提取任务顺序的原型；简单时序压缩与补资源尚未成功。',
        '- ddi 是固定整局动作计划的研究对照，明确不计入三个独立模型。',
        '- ddj 学习决策树条件策略，运行时不读取示范状态和动作表。',
        '- ddn 对 M & M & P & Q 的 146 条完整教师计划进行了 868 局开发筛选，选出原型 35。',
        '- ddq 在该计划上提前出售部分已有库存；原 4 seed 开发集 24/32 胜，不能称为稳定胜出。',
        '- 每版开发面板的 seed 数见表，实际 seed/席位/对手见 runs/<run>/plan.json；同名 broad01 在不同版本不一定采用相同面板。',
        '- 旧教师训练 271 局、新教师训练 121 局的源文件 SHA 和抽样时间对齐均已审计。',
        '- 旧教师训练/验证/测试：271/57/53；新教师 193 局已重新切分，不能再称为 dd 的版本外推测试。',
        '- 所有开发 seed 已用于研发；只有冻结候选后的独占新种子面板可作为门控和确认。',
        '- 无 Kaggle 提交；没有把保存文件、完成训练或通过接口检查算作实战成功。','',
        '稳定标准与版本说明见 [家族说明](README.md)，冻结对手和种子协议见 [protocol.json](protocol.json)。',
        '逐局现金、动作轨迹、推理计时和源码数据哈希位于每版 runs/<run>/。','',
        f"更新：{datetime.datetime.now(datetime.timezone.utc).isoformat()}"]
    (B/'EXPERIMENTS.md').write_text('\n'.join(lines)+'\n');print('\n'.join(lines[:20]))
if __name__=='__main__':main()
