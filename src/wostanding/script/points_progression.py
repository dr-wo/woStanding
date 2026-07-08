from __future__ import annotations

import argparse
from pathlib import Path

import fastf1
import matplotlib.pyplot as plt
import pandas as pd

from wostanding.analysis.points_progression import (
    PointsProgressionResult,
    calculate_points_progression,
)
from wostanding.plots.points_progression import (
    DEFAULT_PROJECTION_HISTORY_ROUNDS,
    plot_points_progression,
    save_points_progression_figures,
)
from wostanding.utils import parse_inclusive_race_range


SCRIPT_CONFIG = {
    "year": 2026,
    "race_range": [1, 9],
    "include_sprints": True,
    "include_projection": True,
    "projection_top": 4,
    "projection_history_rounds": DEFAULT_PROJECTION_HISTORY_ROUNDS,
    "output": None,
    "driver_csv_output": None,
    "team_csv_output": None,
    "event_csv_output": None,
    "show": False,
}


def run_points_progression(
    *,
    year: int,
    race_range: list[int] | tuple[int, int] | str = SCRIPT_CONFIG["race_range"],
    include_sprints: bool = SCRIPT_CONFIG["include_sprints"],
    include_projection: bool = SCRIPT_CONFIG["include_projection"],
    projection_top: int = SCRIPT_CONFIG["projection_top"],
    projection_history_rounds: int = SCRIPT_CONFIG["projection_history_rounds"],
    output_path: str | Path | None = SCRIPT_CONFIG["output"],
    driver_csv_output_path: str | Path | None = SCRIPT_CONFIG["driver_csv_output"],
    team_csv_output_path: str | Path | None = SCRIPT_CONFIG["team_csv_output"],
    event_csv_output_path: str | Path | None = SCRIPT_CONFIG["event_csv_output"],
    show: bool = SCRIPT_CONFIG["show"],
) -> tuple[PointsProgressionResult, dict[str, tuple[plt.Figure, plt.Axes, pd.DataFrame]]]:
    if projection_top < 0:
        raise ValueError("projection_top must be non-negative.")
    if projection_history_rounds <= 0:
        raise ValueError("projection_history_rounds must be positive.")

    race_start, race_end = parse_inclusive_race_range(
        race_range,
        argument_name="race range",
    )

    event_points = load_season_event_points(
        year=year,
        race_start=race_start,
        race_end=race_end,
        include_sprints=include_sprints,
    )
    if event_points.empty:
        raise ValueError(f"No event points loaded for {year}.")

    round_labels = load_season_round_labels(year)
    result = calculate_points_progression(event_points)
    figures = plot_points_progression(
        result,
        title=f"{year} Accumulated Points",
        include_projection=include_projection,
        projection_top=projection_top,
        projection_history_rounds=projection_history_rounds,
        round_labels=round_labels,
    )

    output_path = _resolve_output_path(output_path, year=year)
    saved_paths = save_points_progression_figures(figures, output_path)
    csv_paths = _save_points_csvs(
        result,
        output_path=output_path,
        driver_csv_output_path=driver_csv_output_path,
        team_csv_output_path=team_csv_output_path,
        event_csv_output_path=event_csv_output_path,
    )

    print(f"Loaded event point rows: {len(result.event_points)}")
    print(f"Saved driver plot: {saved_paths['drivers']}")
    print(f"Saved team plot: {saved_paths['teams']}")
    print(f"Saved event points: {csv_paths['events']}")
    print(f"Saved driver points: {csv_paths['drivers']}")
    print(f"Saved team points: {csv_paths['teams']}")

    if show:
        plt.show()
    else:
        for fig, _, _ in figures.values():
            plt.close(fig)

    return result, figures


def load_season_event_points(
    *,
    year: int,
    race_start: int,
    race_end: int | None,
    include_sprints: bool,
) -> pd.DataFrame:
    schedule = fastf1.get_event_schedule(year, include_testing=False)
    schedule = schedule.loc[schedule["RoundNumber"] >= race_start].copy()
    if race_end is not None:
        schedule = schedule.loc[schedule["RoundNumber"] <= race_end].copy()

    event_frames: list[pd.DataFrame] = []
    for _, event in schedule.sort_values("RoundNumber").iterrows():
        round_number = int(event["RoundNumber"])
        event_name = str(event["EventName"])

        race_results = _load_session_results(year, round_number, "R")
        if race_results is None:
            print(f"Skipping {year} R{round_number} {event_name}: race results unavailable.")
            continue

        event_results = _result_points_frame(
            race_results,
            round_number=round_number,
            event_name=event_name,
        )
        if include_sprints and _event_has_sprint(event):
            sprint_results = _load_session_results(year, round_number, "S")
            if sprint_results is not None:
                event_results = pd.concat(
                    [
                        event_results,
                        _result_points_frame(
                            sprint_results,
                            round_number=round_number,
                            event_name=event_name,
                        ),
                    ],
                    ignore_index=True,
                )

        event_frames.append(
            event_results.groupby(
                ["RoundNumber", "EventName", "Driver", "Team"],
                as_index=False,
            )["Points"].sum()
        )

    if not event_frames:
        return pd.DataFrame(columns=["RoundNumber", "EventName", "Driver", "Team", "Points"])

    return pd.concat(event_frames, ignore_index=True)


def main() -> None:
    args = _parse_args()
    run_points_progression(
        year=args.year,
        race_range=_resolve_race_range_args(
            race_range=args.race_range,
            race_start=args.race_start,
            race_end=args.race_end,
        ),
        include_sprints=not args.exclude_sprints,
        include_projection=args.include_projection,
        projection_top=args.projection_top,
        projection_history_rounds=args.projection_history_rounds,
        output_path=args.output,
        driver_csv_output_path=args.driver_csv_output,
        team_csv_output_path=args.team_csv_output,
        event_csv_output_path=args.event_csv_output,
        show=args.show,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plot accumulated Formula 1 points by driver and by team."
    )
    parser.add_argument("--year", type=int, default=SCRIPT_CONFIG["year"])
    parser.add_argument(
        "--race-range",
        default=SCRIPT_CONFIG["race_range"],
        help="Inclusive race range as [<start>, <end>], e.g. '[1, 9]'.",
    )
    parser.add_argument("--race-start", type=int, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--race-end", type=int, default=None, help=argparse.SUPPRESS)
    parser.add_argument(
        "--exclude-sprints",
        action="store_true",
        help="Do not include sprint points in the accumulated totals.",
    )
    parser.add_argument(
        "--include-projection",
        action="store_true",
        default=SCRIPT_CONFIG["include_projection"],
        help="Project top-N driver and team totals through the full season.",
    )
    parser.add_argument(
        "--projection-top",
        type=_nonnegative_int,
        default=SCRIPT_CONFIG["projection_top"],
        help="Number of top driver/team standings to project.",
    )
    parser.add_argument(
        "--projection-history-rounds",
        type=_positive_int,
        default=SCRIPT_CONFIG["projection_history_rounds"],
        help="Number of past rounds used to fit the projection slope.",
    )
    parser.add_argument("--output", type=Path, default=SCRIPT_CONFIG["output"])
    parser.add_argument(
        "--driver-csv-output",
        type=Path,
        default=SCRIPT_CONFIG["driver_csv_output"],
    )
    parser.add_argument(
        "--team-csv-output",
        type=Path,
        default=SCRIPT_CONFIG["team_csv_output"],
    )
    parser.add_argument(
        "--event-csv-output",
        type=Path,
        default=SCRIPT_CONFIG["event_csv_output"],
    )
    parser.add_argument("--show", action="store_true", default=SCRIPT_CONFIG["show"])
    return parser.parse_args()


def _nonnegative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be non-negative")
    return parsed


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return parsed


def _resolve_race_range_args(
    *,
    race_range: list[int] | tuple[int, int] | str,
    race_start: int | None,
    race_end: int | None,
) -> list[int] | tuple[int, int] | str:
    if race_start is None and race_end is None:
        return race_range
    if race_start is None or race_end is None:
        raise ValueError("Legacy --race-start and --race-end must be provided together.")
    return [race_start, race_end]


def load_season_round_labels(year: int) -> pd.DataFrame:
    schedule = fastf1.get_event_schedule(year, include_testing=False)
    return (
        schedule.loc[:, ["RoundNumber", "EventName"]]
        .drop_duplicates()
        .sort_values("RoundNumber")
        .reset_index(drop=True)
    )


def _load_session_results(year: int, round_number: int, session_name: str) -> pd.DataFrame | None:
    try:
        session = fastf1.get_session(year, round_number, session_name)
        session.load(laps=False, telemetry=False, weather=False, messages=False)
    except Exception as exc:
        print(f"Skipping {year} R{round_number} {session_name}: {exc}")
        return None

    results = getattr(session, "results", None)
    if results is None or results.empty:
        return None
    return results.copy()


def _result_points_frame(
    results: pd.DataFrame,
    *,
    round_number: int,
    event_name: str,
) -> pd.DataFrame:
    driver_column = _first_existing_column(results, ("Abbreviation", "Driver", "DriverCode"))
    team_column = _first_existing_column(results, ("TeamName", "Team", "ConstructorName"))
    points_column = _first_existing_column(results, ("Points", "points"))
    missing = [
        name
        for name, column in (
            ("driver", driver_column),
            ("team", team_column),
            ("points", points_column),
        )
        if column is None
    ]
    if missing:
        raise ValueError(f"Results missing required {', '.join(missing)} columns.")

    frame = results.loc[:, [driver_column, team_column, points_column]].copy()
    frame = frame.rename(
        columns={
            driver_column: "Driver",
            team_column: "Team",
            points_column: "Points",
        }
    )
    frame["RoundNumber"] = round_number
    frame["EventName"] = event_name
    frame["Points"] = pd.to_numeric(frame["Points"], errors="coerce").fillna(0.0)
    return frame.loc[:, ["RoundNumber", "EventName", "Driver", "Team", "Points"]]


def _event_has_sprint(event: pd.Series) -> bool:
    event_format = str(event.get("EventFormat", "")).lower()
    return "sprint" in event_format


def _save_points_csvs(
    result: PointsProgressionResult,
    *,
    output_path: Path,
    driver_csv_output_path: str | Path | None,
    team_csv_output_path: str | Path | None,
    event_csv_output_path: str | Path | None,
) -> dict[str, Path]:
    csv_paths = {
        "events": _resolve_csv_path(
            event_csv_output_path,
            output_path=output_path,
            suffix="_events.csv",
        ),
        "drivers": _resolve_csv_path(
            driver_csv_output_path,
            output_path=output_path,
            suffix="_drivers.csv",
        ),
        "teams": _resolve_csv_path(
            team_csv_output_path,
            output_path=output_path,
            suffix="_teams.csv",
        ),
    }
    result.event_points.to_csv(csv_paths["events"], index=False)
    result.driver_points.to_csv(csv_paths["drivers"], index=False)
    result.team_points.to_csv(csv_paths["teams"], index=False)
    return csv_paths


def _resolve_output_path(output_path: str | Path | None, *, year: int) -> Path:
    if output_path is not None:
        return Path(output_path)
    return Path("temp") / f"points_progression_{year}.png"


def _resolve_csv_path(
    csv_path: str | Path | None,
    *,
    output_path: Path,
    suffix: str,
) -> Path:
    if csv_path is not None:
        path = Path(csv_path)
    else:
        path = output_path.with_name(f"{output_path.stem}{suffix}")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _first_existing_column(data: pd.DataFrame, candidates: tuple[str, ...]) -> str | None:
    for candidate in candidates:
        if candidate in data.columns:
            return candidate
    return None


if __name__ == "__main__":
    main()
