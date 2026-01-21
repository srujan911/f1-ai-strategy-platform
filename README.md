# 🏎️ F1 AI Strategy Platform

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

An AI-powered Formula 1 race strategy system that analyzes real F1 telemetry data to model tyre degradation, predict lap-time behavior, and support pit-stop decisions across different circuits.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Usage](#usage)
- [Model Performance](#model-performance)
- [Contributing](#contributing)
- [License](#license)

---

## 🚀 Overview

Formula 1 race strategy is one of the most critical factors in determining race outcomes. This project leverages real race telemetry data from FastF1 to:

- **Predict lap times** using machine learning models trained on actual race data
- **Model tyre degradation** curves for different compounds across various circuits
- **Optimize pit strategies** by simulating multiple stop scenarios
- **Analyze multi-track patterns** to understand how different circuits affect tyre behavior
- **Visualize insights** through an interactive Flask web dashboard

By combining data science with domain expertise in Formula 1 racing, this platform enables data-driven decision making for strategy optimization.

---

## 🧠 Key Features

### 📊 Lap Time Prediction
- **Machine Learning Model**: Random Forest regression trained on real F1 race telemetry
- **Performance**: ~1.11s MAE on Monza 2023 race data (improved from baseline ~1.28s)
- **Features**: Lap number, tyre life, stint number, tyre compound
- **Driver Normalization**: Accounts for individual driver performance variations

### 🛞 Tyre Degradation Modeling
- **Polynomial Regression**: Quadratic models per tyre compound
- **Multi-Track Analysis**: Degradation curves compared across 15+ circuits
- **Fuel Correction**: Accounts for fuel load variations throughout the race
- **Accuracy Filtering**: Only uses representative laps (filters safety car, VSC, pit in/out)

### 🧮 Pit-Stop Strategy Engine
- **Multi-Stop Optimization**: Evaluates 1-stop and 2-stop strategies
- **Degradation vs Pit Loss**: Calculates optimal pit timing based on degradation projections
- **Strategy Simulation**: Simulates race progression with different compound combinations

### 🌍 Multi-Track Strategy Analysis
- **Cross-Circuit Comparison**: Analyzes degradation patterns across different tracks
- **Trend Identification**: Identifies correlations between track characteristics and tyre wear

### 🖥️ Interactive Web Dashboard
- **Flask Web UI**: Real-time visualization of race data and predictions with REST API
- **Dynamic Controls**: Select tracks, compounds, and view strategy analysis
- **Multiple Views**: Lap time predictions, tyre degradation curves, strategy simulations
- **What-If Analysis**: Simulate different race scenarios and strategy outcomes

---

## 🏗️ Architecture

```
                           ┌───────────────┐
                           │  FastF1 Data  │
                           └───────┬───────┘
                                   │
                        ┌──────────▼──────────┐
                        │ Data Processing     │
                        │ (Loading/Cleaning)  │
                        └──────────┬──────────┘
                                   │
      ┌────────────────────────────┼────────────────────────────┐
      │                            │                            │
      ▼                            ▼                            ▼
┌──────────────┐        ┌─────────────────┐       ┌──────────────────┐
│ Feature Eng  │        │ Tyre Degrad.    │       │ Strategy Engine  │
│ (Lap Time)   │        │ Modeling        │       │ (Pit Logic)      │
└──────┬───────┘        └────────┬────────┘       └────────┬─────────┘
       │                         │                         │
       └─────────────────────────┼─────────────────────────┘
                                 │
                        ┌────────▼─────────┐
                        │  Random Forest   │
                        │  ML Model        │
                        └────────┬─────────┘
                                 │
                        ┌────────▼─────────┐
                        │ Flask Web UI     │
                        │ + REST API       │
                        └──────────────────┘
```

### Module Breakdown

| Module | Purpose | Key Functions |
|--------|---------|--------------|
| `data_loader.py` | FastF1 data retrieval | `load_race_data()`, `load_multiple_races()` |
| `feature_engineering.py` | Data preprocessing | `add_driver_normalization()`, `preprocess_laps()` |
| `models/lap_time_model.py` | Lap time prediction | `train_lap_time_model()` |
| `models/tyre_deg_model.py` | Tyre degradation | `fit_tyre_degradation()`, `create_degradation_model()` |
| `strategy/pit_strategy.py` | Strategy optimization | `optimize_pit_strategy()`, `should_pit()` |
| `visualization.py` | Plotting utilities | `plot_tyre_degradation()`, `plot_race_strategy()` |
| `analysis/multi_race_analysis.py` | Cross-race analysis | `compare_tracks()` |
| `server.py` | Main web application | Flask API server with REST endpoints |

---

## 🛠️ Tech Stack

### Core Dependencies
- **Python 3.8+** - Programming language
- **FastF1** - F1 telemetry data provider
- **Flask** - Web framework and REST API
- **Pandas** - Data manipulation and analysis
- **NumPy** - Numerical computing
- **Scikit-learn** - Machine learning models
- **Plotly** - Interactive visualizations

### Development Tools
- **pytest** - Unit testing framework
- **black** - Code formatting
- **flake8** - Linting
- **mypy** - Static type checking

---

## 📦 Installation

### Prerequisites
- Python 3.8 or higher
- pip or conda package manager

### Setup Instructions

```bash
# Clone the repository
git clone https://github.com/srujan911/f1-ai-strategy-platform.git
cd f1-ai-strategy-platform

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies (optional)
pip install -r requirements-dev.txt
```

---

## 🚀 Quick Start

### Run the Web Server
```bash
# Start the Flask API server
python server.py
```

The API server will start at `http://localhost:5000`

### Run with Make
```bash
# Using Make for development
make run
```

Open your browser and navigate to `http://localhost:5000` to access the dashboard.

### Use as a Library
```python
from src.data_loader import load_race_data
from src.models.tyre_deg_model import fit_tyre_degradation

# Load and analyze race data
laps, results = load_race_data(2023, "Monza")
coeffs = fit_tyre_degradation(laps, "SOFT")
print(f"Degradation coefficients: {coeffs}")
```

---

## 📁 Project Structure

```
f1-ai-strategy-platform/
├── .flake8
├── .gitignore
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
├── Makefile
├── README.md
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── setup.cfg
├── setup.py
├── server.py                     # Flask API server (main entrypoint)
├── data/
│   ├── processed/                # Processed datasets
│   └── raw/                      # FastF1 cache data
├── docs/                         # Documentation
├── notebooks/                    # Analysis notebooks
├── src/
│   ├── __init__.py
│   ├── analysis/
│   │   └── multi_race_analysis.py
│   ├── models/
│   │   ├── lap_time_model.py
│   │   └── tyre_deg_model.py
│   ├── prediction/
│   │   ├── 2026_strategy.py
│   │   └── outcome_simulator.py
│   ├── strategy/
│   │   ├── pit_strategy.py
│   │   ├── recommendation.py
│   │   └── simulation_engine.py
│   ├── data_loader.py
│   ├── feature_engineering.py
│   └── visualization.py
├── static/                       # Frontend assets (CSS, JS)
├── templates/                    # HTML templates
├── visualizations/               # Generated charts and graphs
├── tests/                        # Unit tests (tests/ and root test_*.py)
├── test_api.py
├── test_endpoint.py
└── test_fastest_lap.py
```

---

## 💻 Usage

### Dashboard Features

1. **Lap Time Analysis** - View lap distributions and driver performance
2. **Tyre Degradation** - Select track and compound to view degradation curves
3. **Strategy Optimization** - Input race parameters to get pit stop recommendations
4. **Multi-Track Comparison** - Compare degradation patterns across circuits

---

## 📊 Model Performance

### Lap Time Prediction
- **Algorithm**: Random Forest Regressor
- **MAE**: ~1.11 seconds on Monza 2023
- **Features**: Lap number, tyre life, stint, compound
- **Training data**: 300+ laps per race

### Tyre Degradation
- **Algorithm**: Polynomial Regression (2nd degree)
- **R² Score**: 0.75-0.92 depending on circuit
- **Factors**: Fuel load, driver variation, track conditions

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src
```

---

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Follow code standards:
   - PEP 8 style guide
   - Type hints for all functions
   - Docstrings for classes/functions
   - Tests for new features
4. Commit changes (`git commit -m 'Add amazing feature'`)
5. Push to branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

---

## ⚠️ Disclaimer

This is an educational project for analyzing F1 race data. It is not affiliated with Formula 1 or FIA. FastF1 data is for educational purposes only.

---

## 📧 Contact

- **GitHub Issues**: [Report bugs or suggest features](https://github.com/srujan911/f1-ai-strategy-platform/issues)
- **GitHub**: [@srujan911](https://github.com/srujan911)

---

## 🙏 Acknowledgments

- [FastF1](https://github.com/theOehrly/Fast-F1) - F1 telemetry data
- [Flask](https://flask.palletsprojects.com/) - Web framework
- [Scikit-learn](https://scikit-learn.org/) - Machine learning
