import numpy as np
import plotly.graph_objects as go
import plotly.express as px

def plot_tyre_degradation(df, compound, coeffs):
    data = df[df["Compound"] == compound]

    if coeffs is None or len(data) == 0:
        return None

    x = data["TyreLife"].values
    y = data["LapTimeSeconds"].values

    x_curve = np.linspace(x.min(), x.max(), 100)
    y_curve = coeffs[0]*x_curve**2 + coeffs[1]*x_curve + coeffs[2]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=y, mode='markers', name='Data Points',
                             marker=dict(color='rgba(255, 0, 0, 0.5)', size=6),
                             hovertemplate='Tyre Life: %{x}<br>Lap Time: %{y:.2f}s'))
    fig.add_trace(go.Scatter(x=x_curve, y=y_curve, mode='lines', name='Fitted Curve',
                             line=dict(color='red', width=3)))

    fig.update_layout(
        title=f"{compound} Tyre Degradation (Fuel Corrected)",
        xaxis_title="Tyre Life (laps)",
        yaxis_title="Fuel-Corrected Lap Time (s)",
        yaxis=dict(range=[0, 150], tickmode='linear', tick0=0, dtick=15),
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    return fig

def plot_compound_comparison(models, max_laps=50):
    """Plots degradation curves for multiple compounds on one chart."""
    fig = go.Figure()
    x = np.linspace(1, max_laps, 100)

    # F1 Tyre Colors
    colors = {"SOFT": "red", "MEDIUM": "#DAA520", "HARD": "white"}

    for name, model in models.items():
        y = [model(val) for val in x]
        fig.add_trace(go.Scatter(x=x, y=y, mode='lines', name=name,
                                 line=dict(color=colors.get(name, "blue"), width=3),
                                 hovertemplate=f'{name}<br>Tyre Life: %{{x}}<br>Lap Time: %{{y:.2f}}s'))

    fig.update_layout(
        title="Tyre Compound Pace Comparison (Fuel Corrected)",
        xaxis_title="Tyre Life (laps)",
        yaxis_title="Fuel-Corrected Lap Time (s)",
        yaxis=dict(range=[0, 150], tickmode='linear', tick0=0, dtick=15),
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        showlegend=True
    )
    return fig

def plot_race_strategy(lap_times, pits, compounds):
    """Plots the simulated race pace with pit stops and compound colors."""
    fig = go.Figure()
    laps = list(range(1, len(lap_times) + 1))

    colors = {"SOFT": "red", "MEDIUM": "#DAA520", "HARD": "white"}

    # Plot segments for each stint
    current_lap = 0
    for i, compound in enumerate(compounds):
        end_lap = pits[i] if i < len(pits) else len(lap_times)

        segment_indices = range(current_lap, end_lap)
        segment_laps = [laps[j] for j in segment_indices]
        segment_times = [lap_times[j] for j in segment_indices]

        fig.add_trace(go.Scatter(x=segment_laps, y=segment_times, mode='lines',
                                 name=f"Stint {i+1} ({compound})",
                                 line=dict(color=colors.get(compound, "blue"), width=3),
                                 hovertemplate=f'{compound}<br>Lap: %{{x}}<br>Time: %{{y:.2f}}s'))

        current_lap = end_lap

    # Add pit stop markers
    for pit in pits:
        fig.add_trace(go.Scatter(x=[pit], y=[lap_times[pit-1]], mode='markers',
                                 name='Pit Stop', marker=dict(color='white', size=10, symbol='x'),
                                 showlegend=False))

    # Add animation slider for race progression
    fig.update_layout(
        title="Optimized Race Strategy Simulation",
        xaxis_title="Lap Number",
        yaxis_title="Lap Time (s)",
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        showlegend=True,
        updatemenus=[dict(
            type="buttons",
            buttons=[dict(label="Play",
                          method="animate",
                          args=[None, dict(mode="immediate",
                                          frame=dict(duration=300, redraw=False),
                                          fromcurrent=True,
                                          transition=dict(duration=300))]),
                     dict(label="Pause",
                          method="animate",
                          args=[[None], dict(mode="immediate",
                                           frame=dict(duration=0, redraw=False),
                                           transition=dict(duration=0))])])]
    )

    # Create frames for animation
    frames = []
    cumulative_laps = []
    cumulative_times = []
    current_lap = 0
    for i, compound in enumerate(compounds):
        end_lap = pits[i] if i < len(pits) else len(lap_times)
        segment_indices = range(current_lap, end_lap)
        segment_laps = [laps[j] for j in segment_indices]
        segment_times = [lap_times[j] for j in segment_indices]

        cumulative_laps.extend(segment_laps)
        cumulative_times.extend(segment_times)

        frame_data = []
        for j in range(len(cumulative_laps)):
            frame_data.append(go.Scatter(x=cumulative_laps[:j+1], y=cumulative_times[:j+1],
                                       mode='lines', line=dict(color=colors.get(compound, "blue"), width=3)))

        frames.append(go.Frame(data=frame_data, name=f"Lap {len(cumulative_laps)}"))

        current_lap = end_lap

    fig.frames = frames

    return fig
