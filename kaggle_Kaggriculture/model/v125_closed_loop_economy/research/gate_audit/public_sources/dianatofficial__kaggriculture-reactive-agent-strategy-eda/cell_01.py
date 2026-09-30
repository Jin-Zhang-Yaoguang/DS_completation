# 1. Environment & Economic Analysis Setup <a id='1'></a>
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Economic specifications from official Kaggle rulebook
crops_data = [
    {"Crop": "Wheat", "Seed Cost": 10, "Base Price": 25, "Harvest Days": 2, "Max Yield": 4, "ROI_Multiple": (4 * 25) / 10},
    {"Crop": "Carrot", "Seed Cost": 20, "Base Price": 35, "Harvest Days": 2, "Max Yield": 3, "ROI_Multiple": (3 * 35) / 20},
    {"Crop": "Tomato", "Seed Cost": 50, "Base Price": 60, "Harvest Days": 8, "Max Yield": 8, "ROI_Multiple": (8 * 60) / 50},
    {"Crop": "Melon", "Seed Cost": 80, "Base Price": 250, "Harvest Days": 10, "Max Yield": 6, "ROI_Multiple": (6 * 250) / 80},
    {"Crop": "Strawberry", "Seed Cost": 100, "Base Price": 120, "Harvest Days": 10, "Max Yield": 8, "ROI_Multiple": (8 * 120) / 100},
]

df_crops = pd.DataFrame(crops_data)
df_crops['Net Profit per Seed'] = (df_crops['Max Yield'] * df_crops['Base Price']) - df_crops['Seed Cost']
df_crops['Daily Yield Velocity'] = df_crops['Net Profit per Seed'] / df_crops['Harvest Days']

fig = px.bar(
    df_crops,
    x='Crop',
    y='Daily Yield Velocity',
    color='ROI_Multiple',
    title='Kaggriculture: Daily Yield Velocity & ROI by Crop Type',
    template='plotly_dark'
)
fig.show()