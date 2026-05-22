"""v0.5 Phase B: GameplayMetrics + profile defaults."""

from __future__ import annotations

import pytest

from mapir.generation.gameplay_metrics import (
    GameplayMetrics,
    GameplayProfile,
    default_metrics_for_profiles,
)


def test_gameplay_metrics_defaults() -> None:
    m = GameplayMetrics()
    assert m.road.arterial_width_m > m.road.collector_width_m
    assert m.road.collector_width_m > m.road.local_width_m
    assert m.road.local_width_m > m.road.alley_width_m


def test_driving_profile_widens_arterials() -> None:
    base = GameplayMetrics().road.arterial_width_m
    tuned = default_metrics_for_profiles([GameplayProfile.DRIVING])
    assert tuned.road.arterial_width_m >= base


def test_shooter_profile_tightens_cover() -> None:
    tuned = default_metrics_for_profiles([GameplayProfile.SHOOTER])
    assert tuned.shooter.cover_interval_m <= 6.0


def test_stealth_profile_requires_routes() -> None:
    tuned = default_metrics_for_profiles([GameplayProfile.STEALTH])
    assert tuned.stealth.alternate_route_count_min >= 2


def test_parkour_profile_lifts_verticality() -> None:
    tuned = default_metrics_for_profiles([GameplayProfile.PARKOUR])
    assert tuned.parkour.verticality_score >= 0.5


def test_exploration_profile_requires_landmarks() -> None:
    tuned = default_metrics_for_profiles([GameplayProfile.EXPLORATION])
    assert tuned.exploration.landmark_count_min >= 3


@pytest.mark.parametrize("profile", list(GameplayProfile))
def test_metric_bundles_are_serializable(profile: GameplayProfile) -> None:
    m = default_metrics_for_profiles([profile])
    blob = m.model_dump_json()
    restored = GameplayMetrics.model_validate_json(blob)
    assert restored.gameplay_profiles == m.gameplay_profiles
