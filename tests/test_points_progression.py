from __future__ import annotations

import pandas as pd
import pytest

from wostanding.analysis.points_progression import calculate_points_progression
from wostanding.script.points_progression import _result_points_frame


def test_calculate_points_progression_accumulates_driver_and_team_points():
    event_points = pd.DataFrame(
        [
            {
                "RoundNumber": 1,
                "EventName": "Australian Grand Prix",
                "Driver": "LEC",
                "Team": "Ferrari",
                "Points": 25,
            },
            {
                "RoundNumber": 1,
                "EventName": "Australian Grand Prix",
                "Driver": "HAM",
                "Team": "Ferrari",
                "Points": 18,
            },
            {
                "RoundNumber": 1,
                "EventName": "Australian Grand Prix",
                "Driver": "VER",
                "Team": "Red Bull Racing",
                "Points": 15,
            },
            {
                "RoundNumber": 2,
                "EventName": "Chinese Grand Prix",
                "Driver": "VER",
                "Team": "Red Bull Racing",
                "Points": 25,
            },
            {
                "RoundNumber": 2,
                "EventName": "Chinese Grand Prix",
                "Driver": "LEC",
                "Team": "Ferrari",
                "Points": 18,
            },
        ]
    )

    result = calculate_points_progression(event_points)

    driver_totals = _final_totals(result.driver_points, "Driver")
    assert driver_totals == {
        "LEC": 43.0,
        "VER": 40.0,
        "HAM": 18.0,
    }
    assert _driver_round_points(result.driver_points, "HAM", 2) == 18.0

    team_totals = _final_totals(result.team_points, "Team")
    assert team_totals == {
        "Ferrari": 61.0,
        "Red Bull Racing": 40.0,
    }


def test_result_points_frame_normalizes_fastf1_result_columns():
    results = pd.DataFrame(
        {
            "Abbreviation": ["LEC", "HAM"],
            "TeamName": ["Ferrari", "Ferrari"],
            "Points": [25, 8],
        }
    )

    frame = _result_points_frame(
        results,
        round_number=1,
        event_name="Australian Grand Prix",
    )

    assert frame.to_dict("records") == [
        {
            "RoundNumber": 1,
            "EventName": "Australian Grand Prix",
            "Driver": "LEC",
            "Team": "Ferrari",
            "Points": 25,
        },
        {
            "RoundNumber": 1,
            "EventName": "Australian Grand Prix",
            "Driver": "HAM",
            "Team": "Ferrari",
            "Points": 8,
        },
    ]


def test_calculate_points_progression_requires_event_point_columns():
    with pytest.raises(ValueError, match="Team"):
        calculate_points_progression(pd.DataFrame({"Driver": ["LEC"]}))


def _final_totals(points: pd.DataFrame, entity_column: str) -> dict[str, float]:
    final_round = points["RoundNumber"].max()
    final_points = points.loc[points["RoundNumber"] == final_round]
    return dict(zip(final_points[entity_column], final_points["CumulativePoints"]))


def _driver_round_points(points: pd.DataFrame, driver: str, round_number: int) -> float:
    return float(
        points.loc[
            (points["Driver"] == driver) & (points["RoundNumber"] == round_number),
            "CumulativePoints",
        ].iloc[0]
    )
