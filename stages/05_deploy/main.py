# Generate histogram with KDE over it. 

import plotly.express as px
import streamlit as st
import pandas as pd
from numpy.random import default_rng as rng
import numpy as np
from scipy import stats
import plotly.graph_objects as go
import os
import sys
from pathlib import Path
import query
from scipy.ndimage import gaussian_filter1d

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from pool_data import parse_time

STATES = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT",  "DC", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
]
YEARS = [2025,2026]
EVENTS = ["100m", "200m", "400m", "800m", "1600m"]
REGIONS = {
    "Northeast": ["CT", "ME", "MA", "NH", "RI", "VT", "NJ", "NY", "PA"],
    "Midwest": ["IL", "IN", "MI", "OH", "WI", "IA", "KS", "MN", "MO", "NE", "ND", "SD"],
    "South": ["DE", "FL", "GA", "MD", "NC", "SC", "VA", "WV", "AL", "KY", "MS", "TN", "AR", "LA", "OK", "TX"],
    "West": ["AZ", "CO", "ID", "MT", "NV", "NM", "UT", "WY", "AK", "CA", "HI", "OR", "WA"],
}

sex, event, years, states, query_time = None, None, None, None, None
fit, boot, counts = query.load_data()

sex = st.segmented_control("Male or Female", ["male", "female"])
if sex is not None:
    if sex == "female" and sex != False:
        event = st.segmented_control("Event group", ["100m", "200m", "400m", "800m", "1500m"])
    else:
        event = st.segmented_control("Event group", ["100m", "200m", "400m", "800m", "1600m"])

if event is not None:
    years = st.multiselect("Years considered in the model", YEARS, default=YEARS)
if years is not None:
    states = st.multiselect("States considered in the model", STATES, default= STATES)
if query_time is None:
    query_time = st.text_input("Time (10.31 or 1:57.29)")

data = pd.DataFrame()
if years is not None and states is not None:
    for year in years:
        for state in states:
            path = f"stages/01_scrape/output/{year}/{state}/{sex[0]}/{event[:-1]}r.csv"
            tempDF = pd.read_csv(path)
            data = pd.concat([data, tempDF])
    times = data["time"].apply(parse_time)
    max_time = times.quantile(.75) + 3 * (times.quantile(.75) - times.quantile(.25))
    truncated_times = times[times<max_time]

    w = .05
    edges = np.arange(np.floor(min(times) / w) * w, max_time + w, w)
    bin_counts, _ = np.histogram(times, bins=edges)
    peak = bin_counts.max()

    fig = px.bar(x=edges[:-1] + w / 2, y=bin_counts)
    fig.update_traces(
        width=w,
        customdata=np.array([[query.fmt_time(l), query.fmt_time(r)]
                            for l, r in zip(edges[:-1], edges[1:])], dtype=object),
        hovertemplate="<b>%{customdata[0]} – %{customdata[1]}</b><br>%{y} runners<extra></extra>",
    )
    fig.update_layout(bargap=0)

    indexed_times = np.linspace(min(truncated_times), max_time, 250)
    rp = np.array([round(query.query(fit, boot, counts, event, sex[:1], parse_time(t))["rp"], 9)
                for t in indexed_times])
    smoothed_y = peak/rp
    
    fig.add_trace(go.Scatter(
        x=indexed_times, y=smoothed_y, mode="lines", name="Rarity",
        customdata=np.array([[query.fmt_time(t), peak / y]
                            for t, y in zip(indexed_times, smoothed_y)], dtype=object),
        hovertemplate="<b>%{customdata[0]}</b><br>Happens 1 in every %{customdata[1]:,.2f} athlete-seasons<extra></extra>",
    ))
    fig.update_layout(xaxis_title="SB Time", yaxis_title="# of Runners")

    if query_time == "":
        st.plotly_chart(fig)

if query_time != "" and sex is not None and event is not None:
    r = query.query(fit, boot, counts, event, sex[:1], parse_time(query_time))
    query_table = pd.DataFrame()
    fig.add_trace(go.Scatter(
        x=[parse_time(query_time)], 
        y=[peak/r["rp"]], 
        mode="markers",
        marker=dict(color="black", size=5),
        name="Time 1"
    ))
    query_table = pd.concat([query_table, pd.DataFrame(
        data = {"Query Time": query_time, "1 in x athlete-seasons": f"{round(r["rp"],2):g}"}, 
        index = [len(query_table)+1]
    )])
    col1, col2 = st.columns([3,1])
    with col1:
        st.plotly_chart(fig)
    with col2:
        st.table(query_table)
        #st.write(r["source"], round(r["rp"], 1), r["counted"]["per_season"])