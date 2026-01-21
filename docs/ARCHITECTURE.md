# F1 AI Strategy Platform – Architecture

```
[FastF1 Data] --> [data_loader] --> [feature_engineering]
                                  |--> [models]
                                  |      |- tyre_deg_model (compound + driver)
                                  |      |- lap_time_model (RF forecast)
                                  |      `- outcome_simulator (Monte Carlo)
                                  |
                                  |--> [strategy]
                                  |      |- pit_strategy (legacy + wrapper)
                                  |      |- simulation_engine (1-3 stops)
                                  |      `- recommendation (AI verdict)
                                  |
                                  `--> [prediction]
                                         |- _2026_strategy
                                         `- outcome_simulator

[Flask server]
    |- /api/race, /api/tyre-degradation
    |- /api/strategy/simulate (what-if + AI verdict)
    |- /api/lap-time-forecast (horizon + CI)
    |- /api/driver-comparison, /api/outcomes
    |- /api/explainability

[Frontend]
    |- static/js/app.js (controls, charts, what-if)
    |- templates/index.html (tabs, AI Verdict, explainability)
    `- static/css/style.css (dark F1 theme)
```

## Module responsibilities
- **simulation_engine.py**: multi-stop simulation, undercut/overcut, pit windows, scenario controls.
- **recommendation.py**: ranks strategies, emits confidence and explanation strings.
- **tyre_deg_model.py**: compound + driver-specific degradation fits and style classification.
- **lap_time_model.py**: RandomForest training, feature importance, horizon forecasts with confidence intervals.
- **outcome_simulator.py**: Monte Carlo race/championship projections.

## Data flow
1. Race data loaded via `data_loader` (FastF1 cache), normalized by `feature_engineering`.
2. Models fit per compound/driver; strategy engine evaluates scenarios.
3. Flask exposes JSON APIs consumed by the dashboard.
4. Frontend what-if controls call `/api/strategy/simulate`, updating AI Verdict + tables in real time.
5. Explainability surfaces feature importances, strategy rationale, and assumptions.

## Reuse & extensibility
- New inputs (weather, fuel models) can be injected into `whatIfState` and forwarded to `/api/strategy/simulate`.
- Strategy candidates are generated in `generate_candidate_strategies`; adjust heuristics there for custom tracks.
- Forecast horizon and CI logic live in `predict_future_laps` for easy swapping to other models.
