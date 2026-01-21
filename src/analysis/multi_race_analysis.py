import streamlit as st
from src.data_loader import load_race_data
from src.feature_engineering import add_driver_normalization
from src.models.tyre_deg_model import fit_tyre_degradation

TRACK_NAMES = [
    "Bahrain", "Saudi Arabia", "Australia", "Japan", "China", "Miami", "Imola",
    "Monaco", "Canada", "Spain", "Austria", "Britain", "Hungary", "Belgium",
    "Netherlands", "Monza", "Azerbaijan", "Singapore", "Austin", "Mexico",
    "Brazil", "Las Vegas", "Qatar", "Abu Dhabi"
]
YEARS = [2023, 2024, 2025]
TRACKS = [(year, track) for year in YEARS for track in TRACK_NAMES]

@st.cache_data
def compare_tracks(compound="MEDIUM"):
    """Compare tyre degradation coefficients across multiple races for a given compound."""
    results = {}

    for year, gp in TRACKS:
        try:
            df = load_race_data(year, gp)
            df = add_driver_normalization(df)

            coeffs = fit_tyre_degradation(df, compound)
            if coeffs is not None:
                results[f"{year} {gp}"] = coeffs
        except Exception as e:
            # Skip silently for dashboard
            pass

    return results
