##### IMPORTS
import streamlit as st
import pandas as pd
from datetime import datetime
import folium
import re
from streamlit_folium import folium_static
import matplotlib.pyplot as plt
from dms2dec.dms_convert import dms2dec
import pydeck as pdk
import plotly.express as px
import numpy as np 
import pykrige.kriging_tools as kt 
from pykrige.ok import OrdinaryKriging
import plotly.graph_objects as go

##### FUNCTIONS
def geoloc_convert(loc_degree):
    """ Convert degrees minutes seconds coordinate to decimal latitude or longitude  """
    loc_decimal = dms2dec(loc_degree)
    if loc_degree[-1] == 'O':
        loc_decimal = -loc_decimal
    return loc_decimal


def scatter_map(df):
    """ Build scatter map with color gradient for iptcc """
    #select date
    df = df.groupby('station').mean()[['iptcc', 'latitude', 'longitude']]
    mark_size = [100 for i in df.index]
    fig = px.scatter_mapbox(df, lat="latitude", lon="longitude", hover_data=["iptcc"],
          color="iptcc", color_continuous_scale=['#7BD150', '#F6E626', '#F6E626', '#FC9129', '#FF1B00', '#6E1E80'], size=mark_size, size_max=10, zoom=4, height=450)
    fig.update_layout(mapbox_style="open-street-map")
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    return fig

def heat_map():
    """ Build heatmap with color gradient for iptcc """
#     mark_size = [100 for i in df.index]
    fig = px.density_mapbox(df, lat='latitude', lon='longitude', z='iptcc', radius=30, center=dict(lat=0, lon=180), zoom=4, height=450)
#     fig = px.scatter_mapbox(df, lat="latitude", lon="longitude", hover_data=["iptcc"],
#           color="iptcc", color_continuous_scale=['#7BD150', '#F6E626', '#F6E626', '#FC9129', '#FF1B00', '#6E1E80'], size=mark_size, size_max=10, zoom=4, )
    fig.update_layout(mapbox_style="open-street-map")
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    return fig

def ok_map():
    fig = plt.Figure(figsize=(12,7))
    # Compute the ordinary kriging 
    OK = OrdinaryKriging(df['latitude'], df['longitude'], df['iptcc'], variogram_model='linear', verbose=False, 
                         enable_plotting=False)
    z, ss = OK.execute('points', df['latitude'], df['longitude']) 
    df_gradient = df_grid[['Y', 'X']]
    df_gradient['iptcc'] = pd.Series(z)
    mark_size = [100 for i in df_gradient.index]
    fig = px.scatter_mapbox(df_gradient, lat="Y", lon="X", hover_data=["iptcc"],
          color="iptcc", color_continuous_scale=['#7BD150', '#F6E626', '#F6E626', '#FC9129', '#FF1B00', '#6E1E80'],
          size=mark_size, size_max=4, zoom=4, height=450)
    fig.update_layout(mapbox_style="open-street-map")
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    return fig
    
def station_bar_chart(title=""):
    st.subheader(title)
    delta_date = max(df_station['date']) - min(df_station['date'])
    df_station_week = df_station.copy()
    if delta_date > pd.Timedelta("150 days"):
        df_station_week = df_station_week.set_index('date').resample('W').mean().reset_index()

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df_station_week.date, 
        y=df_station_week.iptcc,
        showlegend=False,
        marker=dict(
            color=df_station_week.iptcc,
            colorscale=['#7BD150', '#F6E626', '#F6E626', '#FC9129', '#FF1B00', '#6E1E80']
        )))
    fig.add_trace(go.Scatter(
        x=df_station.date, 
        y=df_station.iptcc_rolling_mean,
        name="Moyenne mobile 30 jours",
        line=dict(
            color="black", #"#FF4B4B",
        )))
    fig.update_layout(
        legend_orientation='h'
    )
    return fig

def departement_bar_chart(title=""):
    st.subheader(title)

    df_departement_week = df_departement.copy()
    delta_date = max(df_departement['date']) - min(df_departement['date'])
    if delta_date > pd.Timedelta("150 days"):
        df_departement_week = df_departement_week.set_index('date').resample('W').mean().reset_index()

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df_departement_week.date, 
        y=df_departement_week.iptcc,
        showlegend=False,
        marker=dict(
            color=df_departement_week.iptcc,
            colorscale=['#7BD150', '#F6E626', '#F6E626', '#FC9129', '#FF1B00', '#6E1E80']
        )))
    fig.add_trace(go.Scatter(
        x=df_departement.date, 
        y=df_departement.iptcc_rolling_mean,
        name="Moyenne mobile 30 jours",
        line=dict(
            color="black", #"#FF4B4B",
        )))
    fig.update_layout(
        legend_orientation='h'
    )
    return fig

@st.cache
def load_data():
    """ Load the cleaned data with latitudes, longitudes & timestamps """
    # Load IPTCC data
    df = pd.read_csv("IPTCC-20210423-153416.csv", sep="|", parse_dates=['DATE'])
    df.columns = [col_name.lower() for col_name in df.columns]
    df['latitude'] = df['latitude'].apply(geoloc_convert)
    df['longitude'] = df['longitude'].apply(geoloc_convert)
    df['iptcc'] = df['iptcc'].str.replace(',', '.').astype(float)
    df['station'] = df['station'].astype(int)
    
    #Load coordinates France grid
    df_grid = pd.read_csv("L93_10K.csv")
    return df, df_grid[:112]


st.title("Climat Covid - IPTCC")

# Load the dataset
df, df_grid = load_data()

# Calculate the timerange for the slider
min_ts = min(df["date"]).to_pydatetime()
max_ts = max(df["date"]).to_pydatetime()

##### SIDEBAR
#slider to chose date
st.sidebar.subheader("Inputs")
time_window = st.sidebar.radio('Time Window', ['Time Range', 'Single Date',])
if time_window!='Time Range':
    day_date = pd.to_datetime(st.sidebar.slider("Date to chose", min_value=min_ts, max_value=max_ts, value=max_ts))
select_station = "" 
select_departement = ""
# day = st.sidebar.text_input("Day", value='22')
# month = st.sidebar.text_input("Month", value='04')
# year = st.sidebar.text_input("Year", value='2021')
    
if time_window=='Time Range':
    min_selection, max_selection = st.sidebar.slider("Timeline", min_value=min_ts, max_value=max_ts, value=[min_ts, max_ts])

    # Filter data for timeframe
    st.write(f"Filtering between {min_selection.date()} & {max_selection.date()}")
    
    df = df[(df["date"] >= min_selection) & (df["date"] <= max_selection)]
    st.write(f"Stations: {len(df)}")
    
    select_station = st.sidebar.selectbox("Stations", options= np.append([""], df['nom'].sort_values().unique()), index=0)
    select_departement = st.sidebar.selectbox("Departments", options= np.append([""], df['departement'].sort_values().unique()), index=0)
    if select_station != "":
        df_station = df[df['nom'] == select_station]
        df_station["iptcc_rolling_mean"] = df_station.iptcc.rolling(window=30, center=True).mean()
    if select_departement != "":
        df_departement = df[df['departement'] == select_departement]
        df_departement["iptcc_rolling_mean"] = df_departement.iptcc.rolling(window=30, center=True).mean()

else:
    # Get last day data 
#     day_date = pd.to_datetime(year + month + day, format='%Y%m%d')
    st.write(f"Data for {day_date.date()}")
    df = df[(df["date"] == day_date)]
    st.write(f"Data Points: {len(df)}")



##### MAPS
# Plot the stations on the map
# st.map(df)
st.plotly_chart(scatter_map(df), use_container_width=True)
# st.plotly_chart(heat_map(df), use_container_width=True)
# st.plotly_chart(ok_map(), use_container_width=True)

##### CHARTS
if select_station != "":
    st.plotly_chart(station_bar_chart(title='Sation ' + select_station), use_container_width=True)
if select_departement != "":
    st.plotly_chart(departement_bar_chart(title='Departement ' + select_departement), use_container_width=True)