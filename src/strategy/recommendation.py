"""
AI strategy recommendation layer.

Takes simulated strategies and returns a concise verdict with
confidence and explanatory factors.
"""

from __future__ import annotations

from typing import Dict, List
import math

from .simulation_engine import StrategyResult


def _confidence_from_gap(best: float, candidate: float) -> float:
    """Convert time gap to 0-1 confidence using a softmax-like curve."""
    if best <= 0:
        return 0.55
    gap = candidate - best
    return float(max(0.05, min(0.98, math.exp(-gap / 6.0))))


def recommend_strategy(
    results: List[StrategyResult],
    factors: Dict[str, float],
    baseline_label: str = "Base Simulation",
) -> Dict[str, object]:
    if not results:
        return {"message": "No viable strategies", "confidence": 0.1}

    best = results[0]
    alt = results[1] if len(results) > 1 else None

    # Calculate confidence based on gap to second-best strategy
    if alt:
        confidence = _confidence_from_gap(best.total_time, alt.total_time)
    else:
        # If no alternative, use a high confidence
        confidence = 0.85

    # Adjust confidence based on parameter extremes (more extreme = less confidence)
    deg_multiplier = factors.get("deg_multiplier", 1.0)
    track_temp = factors.get("track_temperature", 1.0)
    pit_loss = factors.get("pit_loss", 22.0)
    safety_car_prob = factors.get("safety_car_probability", 0.0)
    
    # Penalize extreme parameters
    parameter_extremeness = 0
    if deg_multiplier < 0.85 or deg_multiplier > 1.15:
        parameter_extremeness += 0.05
    if track_temp < 0.95 or track_temp > 1.05:
        parameter_extremeness += 0.05
    if pit_loss < 20 or pit_loss > 24:
        parameter_extremeness += 0.05
    if safety_car_prob > 0.2:
        parameter_extremeness += 0.1
    
    confidence = max(0.05, min(0.98, confidence - parameter_extremeness))

    explanation = [
        f"Strategy minimizes total time at {best.total_time:.1f}s with {len(best.config.pit_laps)} stops.",
        f"Pit loss modeled at {pit_loss:.1f}s; higher pit loss favors fewer stops.",
        f"Degradation multiplier {deg_multiplier:.2f} drives stint length choices.",
        f"Track temperature factor {track_temp:.2f} influences tyre wear assumptions.",
    ]

    if best.config.variant == "undercut":
        explanation.append("Undercut variant selected for out-lap advantage in traffic.")
    elif best.config.variant == "overcut":
        explanation.append("Overcut variant selected due to stable degradation assumptions.")

    if alt:
        time_delta = alt.total_time - best.total_time
        explanation.append(f"Next-best alternative is {time_delta:.2f}s slower with {len(alt.config.pit_laps)} stops.")

    return {
        "recommended": {
            "pit_laps": best.config.pit_laps,
            "compounds": best.config.compounds,
            "variant": best.config.variant,
            "total_time": best.total_time,
            "optimal_windows": best.optimal_windows,
            "stints": best.stint_summaries,
        },
        "confidence": confidence,
        "explanation": explanation,
        "baseline_label": baseline_label,
    }
