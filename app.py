import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output
import plotly.graph_objects as go

# Cargar datos
spotify_df = pd.read_csv("Popular_Spotify_Songs.csv", encoding="latin1")

# Preprocesamiento robusto de fechas
for col in ['released_year', 'released_month', 'released_day']:
    spotify_df[col] = pd.to_numeric(spotify_df[col], errors='coerce')
spotify_df = spotify_df.dropna(subset=['released_year', 'released_month', 'released_day'])
spotify_df[['released_year', 'released_month', 'released_day']] = spotify_df[['released_year', 'released_month', 'released_day']].astype(int)
spotify_df['release_date'] = pd.to_datetime(dict(
    year=spotify_df['released_year'],
    month=spotify_df['released_month'],
    day=spotify_df['released_day']
), errors='coerce')
spotify_df = spotify_df.dropna(subset=['release_date'])
spotify_df['streams'] = pd.to_numeric(spotify_df['streams'], errors='coerce')

# App
app = Dash(__name__)
app.title = "Spotify Popular Songs Dashboard"

# Agregar esta línea para que Gunicorn pueda encontrar el servidor
server = app.server

# Layout
app.layout = html.Div([
    html.H1("🎵 Spotify Popular Songs (2010–2023)", style={'textAlign': 'center'}),

    html.Div([
        html.Label("Rango de fechas:"),
        dcc.DatePickerRange(
            id='date_range',
            min_date_allowed=spotify_df['release_date'].min(),
            max_date_allowed=spotify_df['release_date'].max(),
            start_date=spotify_df['release_date'].min(),
            end_date=spotify_df['release_date'].max()
        ),
    ], style={'marginBottom': '20px', 'textAlign': 'center'}),

    html.Div([
        html.Div([
            html.H3("Evolución de Streams por Fecha"),
            dcc.Graph(id='line_graph'),
            html.Div([
                html.Label("Color de fondo:"),
                dcc.RadioItems(
                    id='line_color_selector',
                    options=[
                        {'label': 'Claro', 'value': 'white'},
                        {'label': 'Oscuro', 'value': 'black'}
                    ],
                    value='white',
                    labelStyle={'display': 'inline-block', 'marginRight': '10px'}
                )
            ], style={'textAlign': 'center'})
        ], style={'width': '48%', 'display': 'inline-block', 'verticalAlign': 'top'}),

        html.Div([
            html.H3("Número de Canciones por Año"),
            dcc.Graph(id='histogram_chart', style={'height': '500px'})
        ], style={'width': '48%', 'display': 'inline-block', 'verticalAlign': 'top'})
    ]),

    html.Div([
        html.Div([
            html.H3("Top 10 por Playlists"),
            dcc.Dropdown(
                id='platform_dropdown',
                options=[
                    {'label': 'Spotify', 'value': 'in_spotify_playlists'},
                    {'label': 'Apple', 'value': 'in_apple_playlists'}
                ],
                value='in_spotify_playlists'
            ),
            dcc.Graph(id='bar_chart')
        ], style={'width': '48%', 'display': 'inline-block', 'verticalAlign': 'top'}),

        html.Div([
            html.H3("Distribución por Tonalidad Musical"),
            html.Label("Selecciona Plataforma:"),
            dcc.Dropdown(
                id='platform_dropdown_pie',
                options=[
                    {'label': 'Spotify', 'value': 'in_spotify_playlists'},
                    {'label': 'Apple', 'value': 'in_apple_playlists'}
                ],
                value='in_spotify_playlists'
            ),
            dcc.Graph(id='pie_chart')
        ], style={'width': '48%', 'display': 'inline-block', 'verticalAlign': 'top'})
    ], style={'textAlign': 'center'})
])

# Callbacks
@app.callback(
    Output('line_graph', 'figure'),
    Input('date_range', 'start_date'),
    Input('date_range', 'end_date'),
    Input('line_color_selector', 'value')
)
def update_line(start, end, color):
    filtered = spotify_df[(spotify_df['release_date'] >= start) & (spotify_df['release_date'] <= end)]
    trend = filtered.groupby('release_date')['streams'].sum().reset_index()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=trend['release_date'], y=trend['streams'], mode='lines', name='Streams'))
    fig.update_layout(
        title='Streams Over Time',
        plot_bgcolor=color,
        xaxis=dict(rangeslider=dict(visible=True), type='date')
    )
    return fig

@app.callback(
    Output('bar_chart', 'figure'),
    Input('platform_dropdown', 'value')
)
def update_bar(platform):
    top = spotify_df.nlargest(10, platform)
    fig = px.bar(top, x='track_name', y=platform, color='artist(s)_name',
                 title=f'Top 10 Canciones por {platform.replace("_", " ").title()}',
                 labels={'track_name': 'Canción', platform: 'Cantidad'})
    fig.update_layout(xaxis_tickangle=-45, height=500)
    return fig

@app.callback(
    Output('pie_chart', 'figure'),
    Input('date_range', 'start_date'),
    Input('date_range', 'end_date'),
    Input('platform_dropdown_pie', 'value')
)
def update_pie(start, end, platform):
    filtered = spotify_df[(spotify_df['release_date'] >= start) & (spotify_df['release_date'] <= end)].copy()

    # Verificar que haya datos disponibles
    if filtered.empty:
        fig = go.Figure()
        fig.add_annotation(text="No hay datos disponibles para este rango de fechas.",
                           x=0.5, y=0.5, showarrow=False, font=dict(size=20))
        fig.update_layout(title="Distribución por Tonalidad Musical")
        return fig

    filtered = filtered.dropna(subset=[platform, 'key'])

    # Verificar si después del filtro los datos siguen disponibles
    if filtered.empty:
        fig = go.Figure()
        fig.add_annotation(text="No hay valores disponibles para esta plataforma.",
                           x=0.5, y=0.5, showarrow=False, font=dict(size=20))
        fig.update_layout(title="Distribución por Tonalidad Musical")
        return fig

    aggregated = filtered.groupby('key')[platform].sum().reset_index()

    if aggregated[platform].sum() == 0:
        fig = go.Figure()
        fig.add_annotation(text="No hay valores disponibles para esta plataforma.",
                           x=0.5, y=0.5, showarrow=False, font=dict(size=20))
        fig.update_layout(title="Distribución por Tonalidad Musical")
        return fig

    fig = px.pie(aggregated, names='key', values=platform,
                 title=f'Distribución por Tonalidad Musical ({platform.replace("_", " ").title()})',
                 labels={'key': 'Tonalidad'}, hole=0.3)
    return fig

@app.callback(
    Output('histogram_chart', 'figure'),
    Input('date_range', 'start_date'),
    Input('date_range', 'end_date')
)
def update_histogram(start, end):
    filtered = spotify_df[(spotify_df['release_date'] >= start) & (spotify_df['release_date'] <= end)].copy()
    filtered['year'] = filtered['release_date'].dt.year
    fig = px.histogram(filtered, x='year', nbins=15, title='Número de Canciones por Año',
                       labels={'year': 'Año', 'count': 'Cantidad'})
    fig.update_layout(height=500)
    return fig

# Agregar esta línea para que Gunicorn pueda encontrar el servidor
if __name__ == '__main__':
    app.run_server(debug=True)
