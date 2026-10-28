import plotly.express as px
import streamlit as st
import pandas as pd
from numpy.random import default_rng as rng
import numpy as np
from scipy import stats
import plotly.graph_objects as go

hist_data = [
    rng(0).standard_normal(200) - 2,
    rng(1).standard_normal(200),
    rng(2).standard_normal(200) + 2,
]
group_labels = ["Group 1", "Group 2", "Group 3"]

hist_data = pd.DataFrame(dict(zip(group_labels, hist_data)))

fig = px.histogram(hist_data, histnorm="probability density", barmode="overlay", opacity=0.5)

x_grid = np.linspace(hist_data.min().min() - 1, hist_data.max().max() + 1, 300)

y = stats.gaussian_kde(hist_data["Group 1"])(x_grid)

fig.add_trace(go.Scatter(x=x_grid, y=y, mode="lines", name=f"Group 1 curve"))
st.plotly_chart(
    fig, alt="Distribution of three groups of random samples"
)


