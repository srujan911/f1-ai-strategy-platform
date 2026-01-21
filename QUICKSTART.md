# Quick Start Guide

Get up and running with the F1 AI Strategy Platform in 5 minutes!

## Installation

### 1. Clone & Setup
```bash
git clone https://github.com/yourusername/f1-ai-strategy-platform.git
cd f1-ai-strategy-platform

# Create virtual environment
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Run the Dashboard
```bash
streamlit run app/dashboard.py
```

The dashboard opens at `http://localhost:8501`

## Using as a Library

### Load Race Data
```python
from src.data_loader import load_race_data

# Load 2023 Monza race
laps, results = load_race_data(2023, "Monza")
print(f"Loaded {len(laps)} laps")
```

### Analyze Tyre Degradation
```python
from src.feature_engineering import add_driver_normalization
from src.models.tyre_deg_model import fit_tyre_degradation

# Normalize for driver performance
laps = add_driver_normalization(laps)

# Fit degradation model
coeffs = fit_tyre_degradation(laps, "SOFT")
print(f"Degradation: f(x) = {coeffs[0]:.6f}x² + {coeffs[1]:.6f}x + {coeffs[2]:.6f}")
```

### Predict Lap Times
```python
from src.feature_engineering import preprocess_laps
from src.models.lap_time_model import train_lap_time_model

# Prepare data
X, y = preprocess_laps(laps)

# Train model
model, mae = train_lap_time_model(X, y)
print(f"Model MAE: {mae:.2f} seconds")

# Make predictions
predictions = model.predict(X.iloc[:5])
```

### Optimize Pit Strategy
```python
from src.models.tyre_deg_model import create_degradation_model
from src.strategy.pit_strategy import optimize_pit_strategy

# Create degradation models for each compound
soft_coeffs = fit_tyre_degradation(laps, "SOFT")
medium_coeffs = fit_tyre_degradation(laps, "MEDIUM")
hard_coeffs = fit_tyre_degradation(laps, "HARD")

models = {
    "SOFT": create_degradation_model(soft_coeffs),
    "MEDIUM": create_degradation_model(medium_coeffs),
    "HARD": create_degradation_model(hard_coeffs)
}

# Find optimal strategy for 53-lap race
strategy = optimize_pit_strategy(
    total_laps=53,
    degradation_models=models,
    pit_loss=22.0
)

print(f"Pit at laps: {strategy['pits']}")
print(f"Compounds: {strategy['compounds']}")
print(f"Total time: {strategy['total_time']:.1f}s")
```

## Development

### Run Tests
```bash
# All tests
pytest

# With coverage
pytest --cov=src
```

### Code Quality
```bash
# Format code
black src/ tests/ app/

# Check style
flake8 src/ tests/

# Type checking
mypy src/
```

### Or use Make
```bash
make test          # Run tests
make lint          # Check style
make format        # Auto-format
make quality       # Run all checks
```

## Data Files

The project includes real F1 telemetry data for:
- **2023 Season**: 15 races (Bahrain through Singapore)
- **2025 Season**: 4 races (Australia, Japan, Bahrain, Monaco)

Data is cached locally in `data/raw/` after first load.

## Documentation

- **[README.md](README.md)** - Full project documentation
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - How to contribute
- **[PROJECT_UPGRADE.md](PROJECT_UPGRADE.md)** - Upgrade details
- **[CHANGELOG.md](CHANGELOG.md)** - Version history

## Common Issues

### FastF1 Cache Issues
```python
import fastf1
# Clear cache if needed
import shutil
shutil.rmtree("data/raw")
```

### Streamlit Port Already in Use
```bash
streamlit run app/dashboard.py --server.port 8502
```

### Import Errors
```bash
# Verify all dependencies installed
pip install -r requirements.txt

# Add project to path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

## Next Steps

1. **Explore the Dashboard** - Visual analysis of races
2. **Run Tests** - Verify everything works: `pytest`
3. **Check Code** - Review well-documented modules
4. **Extend It** - Add new features (see CONTRIBUTING.md)

## Tips

- First load of a race downloads from FastF1 (takes ~30s)
- Subsequent loads are instant (cached)
- Test data is included - no additional downloads needed
- Use `make help` for all available commands

---

**Happy analyzing! 🏎️🏁**
