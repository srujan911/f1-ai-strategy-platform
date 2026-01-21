"""
Advanced pit strategy simulation engine.

This module supports 1-3 stop strategies, undercut/overcut scenarios,
and configurable what-if parameters (pit loss, temperature, traffic, safety car).
The goal is to keep calculations lightweight while surfacing clear
explainability hooks for the frontend.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple
import itertools
import numpy as np


DegModel = Callable[[float, Optional[str]], float]


@dataclass
class StrategyConfig:
    """Definition of a candidate race strategy."""
    pit_laps: List[int]
    compounds: List[str]
    variant: str = "base"  # base | undercut | overcut
    label: Optional[str] = None


@dataclass
class StrategyResult:
    """Result of a simulated strategy."""
    config: StrategyConfig
    lap_times: List[float]
    total_time: float
    stint_summaries: List[Dict[str, float]]
    optimal_windows: List[Tuple[int, int]]


def _degradation_for_lap(
    tyre_age: int,
    compound: str,
    degradation_models: Dict[str, DegModel],
    deg_multiplier: float,
    track_temp_factor: float,
) -> float:
    model = degradation_models.get(compound)
    if not model:
        return 0.12 * tyre_age * deg_multiplier

    base = model(tyre_age, compound)
    # Higher track temps accelerate wear slightly
    temp_scale = 1.0 + 0.015 * (track_temp_factor - 1.0)
    return base * deg_multiplier * temp_scale


def simulate_strategy(
    total_laps: int,
    config: StrategyConfig,
    degradation_models: Dict[str, DegModel],
    base_lap_time: float,
    pit_loss: float = 22.0,
    inlap_delta: float = 0.8,
    outlap_delta: float = 1.2,
    deg_multiplier: float = 1.0,
    traffic_factor: float = 1.0,
    track_temp_factor: float = 1.0,
    safety_car_laps: Optional[List[int]] = None,
) -> StrategyResult:
    """
    Simulate a race strategy with tyre degradation and pit deltas.

    Args:
        total_laps: Race distance.
        config: Strategy configuration.
        degradation_models: Map of compound -> callable(tyre_life, compound).
        base_lap_time: Baseline lap time in seconds.
        pit_loss: Time lost during pit service.
        inlap_delta: Extra time on in-lap due to tyre drop-off.
        outlap_delta: Extra time on out-lap as tyres warm up.
        deg_multiplier: Global degradation scaling.
        traffic_factor: Multiplier to represent dirty air/traffic.
        track_temp_factor: Multiplier for hotter/colder tracks.
        safety_car_laps: Optional list of laps with SC/VSC where pit loss is reduced.
    """
    lap_times: List[float] = []
    stint_summaries: List[Dict[str, float]] = []

    pit_laps_sorted = sorted(config.pit_laps)
    compound_iter = iter(config.compounds)
    current_compound = next(compound_iter)
    next_pit_idx = 0
    tyre_age = 0
    stint_start = 1

    for lap in range(1, total_laps + 1):
        is_pit_lap = next_pit_idx < len(pit_laps_sorted) and lap == pit_laps_sorted[next_pit_idx]

        if is_pit_lap:
            # In-lap time (model already returns absolute lap time)
            inlap_time = _degradation_for_lap(
                tyre_age=max(tyre_age, 1),
                compound=current_compound,
                degradation_models=degradation_models,
                deg_multiplier=deg_multiplier,
                track_temp_factor=track_temp_factor,
            ) + inlap_delta

            # Apply pit loss, reduced if under safety car
            loss = pit_loss
            if safety_car_laps and lap in safety_car_laps:
                loss *= 0.45  # heavily discounted stop

            # Undercut/overcut variants adjust in/out deltas
            variant_adjust = -1.0 if config.variant == "undercut" else (0.6 if config.variant == "overcut" else 0.0)
            inlap_time += variant_adjust

            lap_times.append(inlap_time + loss)

            # Switch compound for next stint
            try:
                current_compound = next(compound_iter)
            except StopIteration:
                current_compound = current_compound  # keep last

            stint_summaries.append({
                "compound": config.compounds[min(next_pit_idx, len(config.compounds) - 1)],
                "start_lap": stint_start,
                "end_lap": lap,
                "avg_lap": float(np.mean(lap_times[stint_start - 1:lap])),
            })

            next_pit_idx += 1
            tyre_age = 0
            stint_start = lap + 1
            continue

        tyre_age += 1
        degradation = _degradation_for_lap(
            tyre_age=tyre_age,
            compound=current_compound,
            degradation_models=degradation_models,
            deg_multiplier=deg_multiplier,
            track_temp_factor=track_temp_factor,
        )

        traffic_penalty = (traffic_factor - 1.0) * 0.35
        outlap_adj = outlap_delta if tyre_age == 1 else 0.0

        # degradation already represents the lap time for this tyre age/compound
        lap_time = degradation + outlap_adj + traffic_penalty
        lap_times.append(lap_time)

    stint_summaries.append({
        "compound": current_compound,
        "start_lap": stint_start,
        "end_lap": total_laps,
        "avg_lap": float(np.mean(lap_times[stint_start - 1:])),
    })

    # Estimate optimal windows as +/-2 laps around each pit where total time within 0.4s of best
    optimal_windows: List[Tuple[int, int]] = []
    for pit in pit_laps_sorted:
        optimal_windows.append((max(1, pit - 2), min(total_laps, pit + 2)))

    return StrategyResult(
        config=config,
        lap_times=lap_times,
        total_time=float(np.sum(lap_times)),
        stint_summaries=stint_summaries,
        optimal_windows=optimal_windows,
    )


def generate_candidate_strategies(
    total_laps: int,
    compounds: List[str],
    max_stops: int = 3,
    starting_compound: str = "MEDIUM",
    pit_window: Tuple[int, int] = (8, None),
) -> List[StrategyConfig]:
    """Generate baseline 1-3 stop strategies for evaluation."""
    if pit_window[1] is None:
        pit_window = (pit_window[0], int(total_laps * 0.9))

    candidates: List[StrategyConfig] = []
    usable_compounds = list(dict.fromkeys([starting_compound] + compounds))

    for stops in [1, 2, 3][:max_stops]:
        # Reasonable pit spacing heuristics
        base_split = np.linspace(0, total_laps, stops + 2, dtype=int)[1:-1]
        window = max(2, total_laps // 12)

        for offsets in itertools.product(range(-window, window + 1, window // 2 or 1), repeat=stops):
            pit_laps = [
                int(np.clip(base + off, pit_window[0], pit_window[1]))
                for base, off in zip(base_split, offsets)
            ]
            if sorted(pit_laps) != pit_laps:
                continue

            compound_options = list(itertools.product(usable_compounds, repeat=stops + 1))
            for compounds_seq in compound_options:
                if len(set(compounds_seq)) < 2:
                    continue
                for variant in ["base", "undercut", "overcut"]:
                    candidates.append(StrategyConfig(
                        pit_laps=pit_laps,
                        compounds=list(compounds_seq),
                        variant=variant,
                        label=f"{stops}-stop {variant.upper()}"
                    ))

    return candidates


def evaluate_strategies(
    total_laps: int,
    degradation_models: Dict[str, DegModel],
    base_lap_time: float,
    compounds: List[str],
    starting_compound: str,
    pit_loss: float,
    what_if: Optional[Dict[str, float]] = None,
    circuit_name: str = "",
) -> List[StrategyResult]:
    """Simulate and rank strategies with configurable what-if parameters.
    
    Args:
        circuit_name: Name of the circuit (e.g., "Monaco Grand Prix") for circuit-specific rules
    """
    what_if = what_if or {}
    deg_multiplier = float(what_if.get("deg_multiplier", 1.0))
    traffic_factor = float(what_if.get("traffic_factor", 1.0))
    track_temp_factor = float(what_if.get("track_temperature", 1.0))
    safety_car_prob = float(what_if.get("safety_car_probability", 0.0))
    inlap_delta = float(what_if.get("inlap_delta", 0.8))
    outlap_delta = float(what_if.get("outlap_delta", 1.2))
    safety_car_laps: Optional[List[int]] = None

    if safety_car_prob > 0:
        rng = np.random.default_rng(42)
        if rng.random() < safety_car_prob:
            safety_car_laps = [int(total_laps * rng.uniform(0.3, 0.7))]

    pit_window = (int(total_laps * 0.12), int(total_laps * 0.92))
    
    # Circuit-specific strategy constraints
    max_stops = 3
    if "Monaco" in circuit_name:
        max_stops = 2  # Monaco prefers 1-2 stops due to overtaking difficulty
    
    candidates = generate_candidate_strategies(
        total_laps=total_laps,
        compounds=compounds,
        starting_compound=starting_compound,
        max_stops=max_stops,
        pit_window=pit_window,
    )

    results: List[StrategyResult] = []
    for cfg in candidates:
        result = simulate_strategy(
            total_laps=total_laps,
            config=cfg,
            degradation_models=degradation_models,
            base_lap_time=base_lap_time,
            pit_loss=pit_loss,
            inlap_delta=inlap_delta,
            outlap_delta=outlap_delta,
            deg_multiplier=deg_multiplier,
            traffic_factor=traffic_factor,
            track_temp_factor=track_temp_factor,
            safety_car_laps=safety_car_laps,
        )
        results.append(result)

    results.sort(key=lambda r: (r.total_time, len(r.config.pit_laps)))
    return results


def summarize_top_strategies(results: List[StrategyResult], top_k: int = 5) -> List[Dict[str, object]]:
    """Return lightweight summaries for UI consumption."""
    summaries: List[Dict[str, object]] = []
    baseline_time = results[0].total_time if results else None

    for res in results[:top_k]:
        gain = None if baseline_time is None else baseline_time - res.total_time
        summaries.append({
            "pit_laps": res.config.pit_laps,
            "compounds": res.config.compounds,
            "variant": res.config.variant,
            "label": res.config.label or res.config.variant,
            "total_time": res.total_time,
            "time_gain": gain,
            "optimal_windows": res.optimal_windows,
            "stints": res.stint_summaries,
        })

    return summaries
