#!/usr/bin/env python
# coding: utf-8

# In[ ]:


# app.py

import pandas as pd
import numpy as np
import calendar
import re
from datetime import datetime
from dash import Dash, dcc, html
import plotly.express as px
import plotly.graph_objects as go

# Load dataset
df = pd.read_csv('storm_data_search_results3.csv')

# Preprocessing
df['BEGIN_DATE'] = pd.to_datetime(df['BEGIN_DATE'])
df['END_DATE'] = pd.to_datetime(df['END_DATE'])
df['DURATION'] = (df['END_DATE'] - df['BEGIN_DATE']).dt.total_seconds() / 3600
df['YEAR'] = df['BEGIN_DATE'].dt.year
df['MONTH'] = df['BEGIN_DATE'].dt.month
df['MONTH_NAME'] = df['MONTH'].apply(lambda x: calendar.month_abbr[x])

# Clean coordinates
def clean_coordinates(coord):
    if pd.isna(coord):
        return np.nan
    try:
        if ' ' in str(coord):
            return float(str(coord).split(' ')[0])
        return float(coord)
    except:
        return np.nan

df['BEGIN_LAT'] = df['BEGIN_LAT'].apply(clean_coordinates)
df['BEGIN_LON'] = df['BEGIN_LON'].apply(clean_coordinates)

# Create sub-dataframes
geo_df = df.dropna(subset=['BEGIN_LAT', 'BEGIN_LON']).copy()
damage_df = df[df['DAMAGE_PROPERTY_NUM'] > 0].copy()
impact_df = df[(df['DEATHS_DIRECT'] > 0) | (df['INJURIES_DIRECT'] > 0)]

# BEGIN_TIME to BEGIN_HOUR
def convert_to_hour(time_str):
    try:
        time_str = re.sub(r'\D', '', str(time_str))
        if len(time_str) == 3:
            return int(time_str[:1])
        elif len(time_str) == 4:
            return int(time_str[:2])
        else:
            return np.nan
    except:
        return np.nan

df['BEGIN_HOUR'] = df['BEGIN_TIME'].apply(convert_to_hour)

# App init
app = Dash(__name__)
app.title = "Flash Flood Dashboard"

# --------------------
# Plotly Figures
# --------------------

# 1. Annual Event Frequency
annual_counts = df['YEAR'].value_counts().sort_index()
fig1 = px.bar(x=annual_counts.index, y=annual_counts.values,
              labels={'x': 'Year', 'y': 'Number of Events'},
              title='Annual Flash Flood Events')

# 2. Monthly Distribution
monthly_counts = df['MONTH_NAME'].value_counts().reindex([calendar.month_abbr[i] for i in range(1, 13)])
fig2 = px.bar(x=monthly_counts.index, y=monthly_counts.values,
              labels={'x': 'Month', 'y': 'Number of Events'},
              title='Seasonal Distribution of Flash Floods')

# 3. Property Damage Over Time
if not damage_df.empty:
    fig3 = px.scatter(damage_df,
                      x='BEGIN_DATE',
                      y=np.log10(damage_df['DAMAGE_PROPERTY_NUM'] + 1),
                      title='Log Property Damage Over Time',
                      labels={'x': 'Date', 'y': 'Log10(Damage in USD)'},
                      hover_data=['DAMAGE_PROPERTY_NUM'])
else:
    fig3 = go.Figure().update_layout(title="No Property Damage Data Available")

# 4. Top Affected Locations
top_locations = df['BEGIN_LOCATION'].value_counts().head(10)
fig4 = px.bar(y=top_locations.index, x=top_locations.values,
              orientation='h',
              title='Top 10 Most Affected Locations',
              labels={'x': 'Number of Events', 'y': 'Location'})

# 5. Event Duration Distribution
fig5 = px.box(df, x='DURATION',
              title='Distribution of Event Durations',
              labels={'DURATION': 'Duration (Hours)'})

# 6. Damage vs Duration
if not damage_df.empty:
    fig6 = px.scatter(damage_df,
                      x='DURATION',
                      y=np.log10(damage_df['DAMAGE_PROPERTY_NUM'] + 1),
                      size='DAMAGE_PROPERTY_NUM',
                      color='YEAR',
                      title='Damage vs Duration (Log Scale)',
                      labels={'DURATION': 'Duration (Hours)', 'y': 'Log10(Damage)'})
else:
    fig6 = go.Figure().update_layout(title="No Damage vs Duration Data Available")

# 7. Cumulative Events Over Time
cumulative = df.sort_values('BEGIN_DATE').groupby('BEGIN_DATE').size().cumsum()
fig7 = go.Figure()
fig7.add_trace(go.Scatter(x=cumulative.index, y=cumulative.values, mode='lines'))
fig7.update_layout(title='Cumulative Flash Flood Events Over Time',
                   xaxis_title='Date', yaxis_title='Cumulative Events')

# 8. Human Impact (Deaths/Injuries)
if not impact_df.empty:
    deaths = impact_df.groupby('YEAR')['DEATHS_DIRECT'].sum()
    injuries = impact_df.groupby('YEAR')['INJURIES_DIRECT'].sum()
    fig8 = go.Figure()
    fig8.add_trace(go.Bar(x=deaths.index, y=deaths.values, name='Deaths', marker_color='crimson'))
    fig8.add_trace(go.Bar(x=injuries.index, y=injuries.values, name='Injuries', marker_color='orange'))
    fig8.update_layout(title='Deaths and Injuries Over Time',
                       barmode='group', xaxis_title='Year')
else:
    fig8 = go.Figure().update_layout(title="No Human Impact Data Available")

# 9. Hourly Distribution of Events
fig9 = px.histogram(df.dropna(subset=['BEGIN_HOUR']),
                    x='BEGIN_HOUR', nbins=24,
                    title='Hourly Distribution of Flash Floods',
                    labels={'BEGIN_HOUR': 'Hour of Day', 'count': 'Number of Events'})

# 10. Damage by Location (Top 10)
if not damage_df.empty:
    location_damage = damage_df.groupby('BEGIN_LOCATION')['DAMAGE_PROPERTY_NUM'].sum().nlargest(10)
    fig10 = px.bar(x=location_damage.values, y=location_damage.index,
                   orientation='h', title='Top 10 Locations by Property Damage',
                   labels={'x': 'Total Damage (USD)', 'y': 'Location'})
else:
    fig10 = go.Figure().update_layout(title="No Property Damage Data Available")

# 11. Total Damage by Year (Area)
if not damage_df.empty:
    damage_by_year = damage_df.groupby('YEAR')['DAMAGE_PROPERTY_NUM'].sum().reset_index()
    fig11 = px.area(damage_by_year,
                    x='YEAR',
                    y='DAMAGE_PROPERTY_NUM',
                    title='Total Property Damage by Year (Log Scale)',
                    labels={'DAMAGE_PROPERTY_NUM': 'Damage (USD)'},
                    log_y=True)
else:
    fig11 = go.Figure().update_layout(title="No Yearly Damage Data Available")

# 12. Map Placeholder (Explain in layout)
map_html = html.Iframe(src="https://your-map-link.com",
                       style={"height": "600px", "width": "100%"})

# --------------------
# Layout
# --------------------

app.layout = html.Div([
    html.H1("Jefferson County Flash Flood Dashboard", style={'textAlign': 'center'}),

    dcc.Tabs([
        dcc.Tab(label='Annual Event Frequency', children=[dcc.Graph(figure=fig1)]),
        dcc.Tab(label='Monthly Distribution', children=[dcc.Graph(figure=fig2)]),
        dcc.Tab(label='Property Damage (Log)', children=[dcc.Graph(figure=fig3)]),
        dcc.Tab(label='Top Affected Locations', children=[dcc.Graph(figure=fig4)]),
        dcc.Tab(label='Event Duration Distribution', children=[dcc.Graph(figure=fig5)]),
        dcc.Tab(label='Damage vs Duration', children=[dcc.Graph(figure=fig6)]),
        dcc.Tab(label='Cumulative Events Over Time', children=[dcc.Graph(figure=fig7)]),
        dcc.Tab(label='Deaths & Injuries', children=[dcc.Graph(figure=fig8)]),
        dcc.Tab(label='Hourly Distribution', children=[dcc.Graph(figure=fig9)]),
        dcc.Tab(label='Damage by Location', children=[dcc.Graph(figure=fig10)]),
        dcc.Tab(label='Yearly Damage (Log)', children=[dcc.Graph(figure=fig11)]),
        dcc.Tab(label='Map View (External)', children=[
            html.P("Interactive Map embedded from hosted folium HTML:"),
            map_html
        ]),
    ])
])

if __name__ == '__main__':
    app.run(debug=True)


# In[ ]:




