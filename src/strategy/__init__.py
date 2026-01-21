"""
Strategy module for F1 strategy platform.

This module contains functions for optimizing pit stop strategies
and simulating race scenarios.
"""

from src.strategy.pit_strategy import optimize_pit_strategy, should_pit, simulate_race_strategy

__all__ = ["should_pit", "optimize_pit_strategy", "simulate_race_strategy"]
