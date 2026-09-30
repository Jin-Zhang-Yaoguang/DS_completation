fib_costs = [1, 1, 2, 3, 5, 8, 13, 21]
workers = list(range(1, len(fib_costs) + 1))
cumulative_cost = np.cumsum(fib_costs)
actions_gained = [w * 24 for w in workers]

fig_labour = go.Figure()
fig_labour.add_trace(go.Bar(x=workers, y=cumulative_cost, name='Cumulative Hiring Cost ($)', marker_color='#EF553B'))
fig_labour.add_trace(go.Scatter(x=workers, y=actions_gained, name='Total Actions Gained', yaxis='y2', line=dict(color='#00CC96', width=3)))

fig_labour.update_layout(
    title='Fibonacci Labour Scaling Curve: Optimal Frontier at N=2',
    yaxis=dict(title='Daily Cost ($)'),
    yaxis2=dict(title='Actions per Day', overlaying='y', side='right'),
    template='plotly_dark'
)
fig_labour.show()