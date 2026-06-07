from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class PointsProgressionResult:
    event_points: pd.DataFrame
    driver_points: pd.DataFrame
    team_points: pd.DataFrame


REQUIRED_EVENT_POINT_COLUMNS = {
    "RoundNumber",
    "EventName",
    "Driver",
    "Team",
    "Points",
}


def calculate_points_progression(event_points: pd.DataFrame) -> PointsProgressionResult:
    """Calculate per-round and cumulative points for drivers and teams."""
    _validate_event_points(event_points)
    cleaned = _clean_event_points(event_points)

    driver_points = _cumulative_points(
        cleaned,
        entity_column="Driver",
        output_entity_column="Driver",
    )
    team_points = _cumulative_points(
        cleaned,
        entity_column="Team",
        output_entity_column="Team",
    )

    return PointsProgressionResult(
        event_points=cleaned,
        driver_points=driver_points,
        team_points=team_points,
    )


def _validate_event_points(event_points: pd.DataFrame) -> None:
    missing = REQUIRED_EVENT_POINT_COLUMNS.difference(event_points.columns)
    if missing:
        missing_columns = ", ".join(sorted(missing))
        raise ValueError(f"Event points missing required columns: {missing_columns}")


def _clean_event_points(event_points: pd.DataFrame) -> pd.DataFrame:
    cleaned = event_points.loc[:, sorted(REQUIRED_EVENT_POINT_COLUMNS)].copy()
    cleaned = cleaned.dropna(subset=["Driver", "Team"])
    cleaned["RoundNumber"] = pd.to_numeric(cleaned["RoundNumber"], errors="raise").astype(int)
    cleaned["Points"] = pd.to_numeric(cleaned["Points"], errors="coerce").fillna(0.0)
    cleaned["EventName"] = cleaned["EventName"].astype(str)
    cleaned["Driver"] = cleaned["Driver"].astype(str)
    cleaned["Team"] = cleaned["Team"].astype(str)
    return cleaned.sort_values(["RoundNumber", "Team", "Driver"]).reset_index(drop=True)


def _cumulative_points(
    event_points: pd.DataFrame,
    *,
    entity_column: str,
    output_entity_column: str,
) -> pd.DataFrame:
    rounds = (
        event_points.loc[:, ["RoundNumber", "EventName"]]
        .drop_duplicates()
        .sort_values("RoundNumber")
        .reset_index(drop=True)
    )
    entities = sorted(event_points[entity_column].dropna().unique())
    if not entities:
        return pd.DataFrame(
            columns=[
                output_entity_column,
                "RoundNumber",
                "EventName",
                "Points",
                "CumulativePoints",
            ]
        )

    index = pd.MultiIndex.from_product(
        [entities, rounds["RoundNumber"].tolist()],
        names=[output_entity_column, "RoundNumber"],
    )
    points_by_round = (
        event_points.groupby([entity_column, "RoundNumber"], as_index=True)["Points"]
        .sum()
        .reindex(index, fill_value=0.0)
        .reset_index()
    )
    points_by_round = points_by_round.merge(rounds, on="RoundNumber", how="left")
    points_by_round["CumulativePoints"] = points_by_round.groupby(output_entity_column)[
        "Points"
    ].cumsum()
    return points_by_round.sort_values(
        ["RoundNumber", "CumulativePoints", output_entity_column],
        ascending=[True, False, True],
    ).reset_index(drop=True)


__all__ = [
    "PointsProgressionResult",
    "calculate_points_progression",
]
