"""
Race strategy optimization and pit stop decision logic.

This module now contains two layers:
- A lightweight heuristic optimizer (legacy) used by older endpoints
- A richer simulation interface backed by the advanced engine in
    `simulation_engine.py` for 1-3 stop scenarios and what-if analysis.
"""

import numpy as np
from typing import List, Tuple, Dict, Callable

from .simulation_engine import (
        StrategyConfig,
        evaluate_strategies,
        summarize_top_strategies,
)


def should_pit(
    current_lap_time: float,
    predicted_next_lap: float,
    pit_loss_seconds: float = 22.0,
    lookahead_laps: int = 5
) -> bool:
    """
    Decide whether to pit based on degradation vs pit loss tradeoff.

    Compares projected degradation over the next N laps against the time
    lost during a pit stop to make a strategic pit decision.

    Args:
        current_lap_time (float): Current lap time in seconds
        predicted_next_lap (float): Predicted next lap time in seconds
        pit_loss_seconds (float): Time penalty for pit stop (default: 22.0)
        lookahead_laps (int): Number of laps to forecast (default: 5)

    Returns:
        bool: True if pitting is beneficial, False otherwise

    Example:
        >>> should_pit(85.5, 87.2, pit_loss_seconds=22.0, lookahead_laps=5)
        True
    """
    degradation_per_lap = predicted_next_lap - current_lap_time
    projected_loss = degradation_per_lap * lookahead_laps

    return projected_loss > pit_loss_seconds


def optimize_pit_strategy(
    total_laps: int,
    degradation_models: Dict[str, Callable],
    pit_loss: float = 22.0,
    starting_compound: str = "MEDIUM",
    available_compounds: List[str] = ["SOFT", "MEDIUM", "HARD"],
    circuit_name: str = ""
) -> Dict:
    """
    Optimize pit strategy by simulating different compound combinations and pit stops.

    Evaluates candidate strategies (1-stop and 2-stop options) and finds the
    compound/pit lap combination that minimizes total race time.

    Args:
        total_laps (int): Total number of laps in the race
        degradation_models (Dict[str, Callable]): Dictionary mapping compound names to
                                                 degradation functions
        pit_loss (float): Time penalty for pit stop in seconds (default: 22.0)
        starting_compound (str): Starting tyre compound (default: "MEDIUM")
        available_compounds (List[str]): Available tyre compounds (default: all)

    Returns:
        Dict: Optimal strategy with keys:
            - "pits": List of lap numbers where pit stops occur
            - "compounds": List of compounds used in each stint
            - "total_time": Total race time in seconds
            - "pit_loss": Time penalty applied

    Example:
        >>> strategy = optimize_pit_strategy(53, models, pit_loss=22.0)
        >>> print(f"Optimal pits at laps: {strategy['pits']}")
        Optimal pits at laps: [18, 38]
    """
    
    # Wrapper to handle compound-specific models
    def composite_model(life: float, compound: str) -> float:
        if compound in degradation_models:
            return degradation_models[compound](life, compound)
        return 0.1 * life  # Fallback

    best_strategy = {
        "pits": [],
        "compounds": [starting_compound],
        "total_time": float('inf'),
        "pit_loss": pit_loss
    }

    # Generate candidate strategies
    candidates = []
    
    # 1-Stop Strategies
    for c2 in available_compounds:
        if c2 != starting_compound:
            candidates.append([starting_compound, c2])
            
    # 2-Stop Strategies
    for c2 in available_compounds:
        for c3 in available_compounds:
            if len({starting_compound, c2, c3}) >= 2:
                candidates.append([starting_compound, c2, c3])

    # Optimize pit laps for each candidate
    for compounds in candidates:
        n_stops = len(compounds) - 1
        
        if n_stops == 1:
            # Search range: 20% to 80% of race
            start, end = int(total_laps * 0.2), int(total_laps * 0.8)
            step = max(1, (end - start) // 10)
            
            for pit_lap in range(start, end + 1, step):
                strategy = {"pits": [pit_lap], "compounds": compounds, "pit_loss": pit_loss}
                time = sum(simulate_race_strategy(total_laps, strategy, composite_model))
                if time < best_strategy["total_time"]:
                    best_strategy = {**strategy, "total_time": time}
                    
        elif n_stops == 2:
            # Search around 1/3 and 2/3 distance
            p1_base, p2_base = int(total_laps * 0.33), int(total_laps * 0.66)
            window = max(2, total_laps // 15)
            
            for p1 in range(p1_base - window, p1_base + window, 2):
                for p2 in range(p2_base - window, p2_base + window, 2):
                    if p1 < p2 and p1 > 5 and p2 < total_laps - 5:
                        strategy = {"pits": [p1, p2], "compounds": compounds, "pit_loss": pit_loss}
                        time = sum(simulate_race_strategy(total_laps, strategy, composite_model))
                        if time < best_strategy["total_time"]:
                            best_strategy = {**strategy, "total_time": time}

    return best_strategy


def simulate_race_strategy(
    total_laps: int,
    pit_strategy: Dict,
    degradation_model: Callable,
    base_lap_time: float = 85.0
) -> List[float]:
    """
    Simulate a complete race with a given pit strategy.

    Calculates lap times for each lap of the race, accounting for pit stops,
    compound changes, and tyre degradation over time.

    Args:
        total_laps (int): Total race distance in laps
        pit_strategy (Dict): Strategy dict with "pits", "compounds", "pit_loss" keys
        degradation_model (Callable): Function(tyre_life, compound) -> degradation
        base_lap_time (float): Baseline lap time in seconds (default: 85.0)

    Returns:
        List[float]: Lap times for entire race (length = total_laps)

    Example:
        >>> pit_strategy = {"pits": [18], "compounds": ["MEDIUM", "HARD"], "pit_loss": 22.0}
        >>> lap_times = simulate_race_strategy(53, pit_strategy, degradation_model)
        >>> print(f"Total race time: {sum(lap_times):.1f}s")
    """
    lap_times = []
    current_compound = pit_strategy["compounds"][0]
    pit_idx = 0
    current_tyre_life = 0

    for lap in range(1, total_laps + 1):
        # Check if pitting this lap
        if pit_idx < len(pit_strategy["pits"]) and lap == pit_strategy["pits"][pit_idx]:
            # Add pit loss to this lap
            lap_time = base_lap_time + pit_strategy.get("pit_loss", 22.0)
            # Switch compound
            pit_idx += 1
            if pit_idx < len(pit_strategy["compounds"]):
                current_compound = pit_strategy["compounds"][pit_idx]
            current_tyre_life = 0
        else:
            current_tyre_life += 1
            # Normal lap - degradation model already returns absolute lap time, not delta
            lap_time = degradation_model(current_tyre_life, current_compound)

        lap_times.append(lap_time)

    return lap_times


# --- Advanced simulation wrappers ---

def run_strategy_simulation(
    total_laps: int,
    degradation_models: Dict[str, Callable],
    base_lap_time: float,
    pit_loss_seconds: float = 22.0,
    starting_compound: str = "MEDIUM",
    available_compounds: List[str] = None,
    what_if: Dict[str, float] = None,
) -> Dict[str, object]:
    """
    Evaluate multi-stop strategies via the advanced simulation engine.

    Args:
        total_laps: Race distance in laps.
        degradation_models: Map of compound -> model(tyre_life, compound).
        base_lap_time: Baseline lap time.
        pit_loss_seconds: Pit lane time loss.
        starting_compound: First stint compound.
        available_compounds: Allowed compounds; defaults to keys of degradation_models.
        what_if: Optional scenario overrides (temperature, safety car probability, etc.).

    Returns:
        Dict with top strategies, recommended strategy and metadata for UI.
    """
    if available_compounds is None:
        available_compounds = list(degradation_models.keys())

    results = evaluate_strategies(
        total_laps=total_laps,
        degradation_models=degradation_models,
        base_lap_time=base_lap_time,
        compounds=available_compounds,
        starting_compound=starting_compound,
        pit_loss=pit_loss_seconds,
        what_if=what_if,
        circuit_name=circuit_name,
    )

    summaries = summarize_top_strategies(results)

    return {
        "strategies": summaries,
        "best": summaries[0] if summaries else None,
        "all_count": len(results),
    }
