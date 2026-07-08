from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from wostanding.analysis.points_progression import PointsProgressionResult
from wostanding.plots.style_maps import build_team_color_map

DRIVER_LINESTYLES = ("-", "--", ":", "-.")
DRIVER_MARKERS = ("o", "s", "^", "D")
FIGURE_SIZE = (16, 9)
DEFAULT_PROJECTION_TOP = 3
DEFAULT_PROJECTION_HISTORY_ROUNDS = 4


def plot_points_progression(
    result: PointsProgressionResult,
    *,
    title: str | None = None,
    include_projection: bool = False,
    projection_top: int = DEFAULT_PROJECTION_TOP,
    projection_history_rounds: int = DEFAULT_PROJECTION_HISTORY_ROUNDS,
    round_labels: pd.DataFrame | None = None,
) -> dict[str, tuple[plt.Figure, plt.Axes, pd.DataFrame]]:
    driver_fig, driver_ax = _plot_driver_points(
        result.driver_points,
        result.event_points,
        title=title,
        include_projection=include_projection,
        projection_top=projection_top,
        projection_history_rounds=projection_history_rounds,
        round_labels=round_labels,
    )
    team_fig, team_ax = _plot_team_points(
        result.team_points,
        title=title,
        include_projection=include_projection,
        projection_top=projection_top,
        projection_history_rounds=projection_history_rounds,
        round_labels=round_labels,
    )
    return {
        "drivers": (driver_fig, driver_ax, result.driver_points),
        "teams": (team_fig, team_ax, result.team_points),
    }


def save_points_progression_figures(
    figures: dict[str, tuple[plt.Figure, plt.Axes, pd.DataFrame]],
    output_path: str | Path,
) -> dict[str, Path]:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    suffix = output_path.suffix or ".png"
    stem_path = output_path.with_suffix("")

    saved_paths: dict[str, Path] = {}
    for key, (fig, _, _) in figures.items():
        figure_path = stem_path.with_name(f"{stem_path.name}_{key}").with_suffix(suffix)
        fig.savefig(figure_path, dpi=150, bbox_inches="tight")
        saved_paths[key] = figure_path
    return saved_paths


def _plot_driver_points(
    driver_points: pd.DataFrame,
    event_points: pd.DataFrame,
    *,
    title: str | None,
    include_projection: bool,
    projection_top: int,
    projection_history_rounds: int,
    round_labels: pd.DataFrame | None,
) -> tuple[plt.Figure, plt.Axes]:
    team_color_map = build_team_color_map(event_points["Team"])
    latest_team_by_driver = _latest_team_by_driver(event_points)
    driver_style_map = _build_driver_style_map(driver_points, latest_team_by_driver)
    projection_points = _projection_points(
        driver_points,
        entity_column="Driver",
        round_labels=round_labels,
        include_projection=include_projection,
        projection_top=projection_top,
        projection_history_rounds=projection_history_rounds,
    )

    fig, ax = plt.subplots(figsize=FIGURE_SIZE)
    ordered_drivers = _final_order(driver_points, "Driver")
    for driver in ordered_drivers:
        points = driver_points.loc[driver_points["Driver"] == driver].sort_values("RoundNumber")
        team = latest_team_by_driver.get(driver)
        linestyle, marker = driver_style_map.get(driver, ("-", "o"))
        ax.plot(
            points["RoundNumber"],
            points["CumulativePoints"],
            marker=marker,
            linewidth=2,
            markersize=4.5,
            color=team_color_map.get(team),
            linestyle=linestyle,
            label=f"{driver} ({team})" if team else driver,
        )
        _plot_projection_line(
            ax,
            projection_points,
            entity_column="Driver",
            entity=driver,
            color=team_color_map.get(team),
        )

    _format_points_axis(
        ax,
        driver_points,
        projection_points,
        round_labels=round_labels,
        title=title or "Driver Points Progression",
        ylabel="Driver points",
    )
    ax.legend(
        loc="center left",
        bbox_to_anchor=(1.01, 0.5),
        fontsize=8,
        handlelength=3,
    )
    fig.tight_layout()
    return fig, ax


def _plot_team_points(
    team_points: pd.DataFrame,
    *,
    title: str | None,
    include_projection: bool,
    projection_top: int,
    projection_history_rounds: int,
    round_labels: pd.DataFrame | None,
) -> tuple[plt.Figure, plt.Axes]:
    team_color_map = build_team_color_map(team_points["Team"])
    projection_points = _projection_points(
        team_points,
        entity_column="Team",
        round_labels=round_labels,
        include_projection=include_projection,
        projection_top=projection_top,
        projection_history_rounds=projection_history_rounds,
    )

    fig, ax = plt.subplots(figsize=FIGURE_SIZE)
    ordered_teams = _final_order(team_points, "Team")
    for team in ordered_teams:
        points = team_points.loc[team_points["Team"] == team].sort_values("RoundNumber")
        ax.plot(
            points["RoundNumber"],
            points["CumulativePoints"],
            marker="o",
            linewidth=2.4,
            markersize=4,
            color=team_color_map.get(team),
            label=team,
        )
        _plot_projection_line(
            ax,
            projection_points,
            entity_column="Team",
            entity=team,
            color=team_color_map.get(team),
        )

    _format_points_axis(
        ax,
        team_points,
        projection_points,
        round_labels=round_labels,
        title=title or "Team Points Progression",
        ylabel="Team points",
    )
    ax.legend(loc="center left", bbox_to_anchor=(1.01, 0.5), fontsize=9)
    fig.tight_layout()
    return fig, ax


def _format_points_axis(
    ax: plt.Axes,
    points: pd.DataFrame,
    projection_points: pd.DataFrame,
    *,
    round_labels: pd.DataFrame | None,
    title: str,
    ylabel: str,
) -> None:
    if round_labels is None:
        round_labels = (
            points.loc[:, ["RoundNumber", "EventName"]]
            .drop_duplicates()
            .sort_values("RoundNumber")
        )
    else:
        round_labels = _clean_round_labels(round_labels)
    ax.set_xlabel("Round")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.set_xticks(round_labels["RoundNumber"])
    labels = [
        f"R{round_number}\n{_short_event_name(event_name)}"
        for round_number, event_name in round_labels.itertuples(index=False)
    ]
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_xlim(
        left=float(round_labels["RoundNumber"].min()) - 0.25,
        right=float(round_labels["RoundNumber"].max()) + 0.25,
    )
    ax.grid(True, which="major", axis="both", alpha=0.3, zorder=0)
    ax.set_axisbelow(True)
    ax.set_ylim(bottom=0, top=_points_axis_top(points, projection_points))


def _projection_points(
    points: pd.DataFrame,
    *,
    entity_column: str,
    round_labels: pd.DataFrame | None,
    include_projection: bool,
    projection_top: int,
    projection_history_rounds: int,
) -> pd.DataFrame:
    columns = [entity_column, "RoundNumber", "CumulativePoints"]
    if (
        not include_projection
        or projection_top <= 0
        or projection_history_rounds <= 0
        or round_labels is None
        or points.empty
    ):
        return pd.DataFrame(columns=columns)

    round_numbers = _clean_round_labels(round_labels)["RoundNumber"].tolist()
    if not round_numbers:
        return pd.DataFrame(columns=columns)

    latest_round = int(points["RoundNumber"].max())
    projection_rounds = [
        round_number for round_number in round_numbers if round_number >= latest_round
    ]
    if len(projection_rounds) < 2:
        return pd.DataFrame(columns=columns)

    rows: list[dict[str, float | int | str]] = []
    for entity in _final_order(points, entity_column)[:projection_top]:
        entity_points = points.loc[points[entity_column] == entity].sort_values("RoundNumber")
        recent_points = entity_points.tail(projection_history_rounds)
        start = recent_points.iloc[0]
        end = recent_points.iloc[-1]
        round_delta = int(end["RoundNumber"]) - int(start["RoundNumber"])
        if round_delta:
            slope = (
                float(end["CumulativePoints"]) - float(start["CumulativePoints"])
            ) / round_delta
        else:
            slope = 0.0
        latest_points = float(end["CumulativePoints"])

        for round_number in projection_rounds:
            rows.append(
                {
                    entity_column: entity,
                    "RoundNumber": round_number,
                    "CumulativePoints": latest_points + slope * (round_number - latest_round),
                }
            )

    return pd.DataFrame(rows, columns=columns)


def _plot_projection_line(
    ax: plt.Axes,
    projection_points: pd.DataFrame,
    *,
    entity_column: str,
    entity: str,
    color: object,
) -> None:
    points = projection_points.loc[projection_points[entity_column] == entity]
    if points.empty:
        return
    ax.plot(
        points["RoundNumber"],
        points["CumulativePoints"],
        linewidth=2,
        color=color,
        linestyle="-.",
        alpha=0.75,
        label=f"{entity} projection",
    )


def _points_axis_top(points: pd.DataFrame, projection_points: pd.DataFrame) -> float:
    highest = float(points["CumulativePoints"].max()) if not points.empty else 0.0
    if not projection_points.empty:
        highest = max(highest, float(projection_points["CumulativePoints"].max()))
    if highest <= 0:
        return 1.0
    return highest * 1.25


def _clean_round_labels(round_labels: pd.DataFrame) -> pd.DataFrame:
    labels = round_labels.loc[:, ["RoundNumber", "EventName"]].copy()
    labels["RoundNumber"] = pd.to_numeric(labels["RoundNumber"], errors="raise").astype(int)
    labels["EventName"] = labels["EventName"].astype(str)
    return labels.drop_duplicates().sort_values("RoundNumber").reset_index(drop=True)


def _final_order(points: pd.DataFrame, entity_column: str) -> list[str]:
    final_round = points["RoundNumber"].max()
    final_points = points.loc[points["RoundNumber"] == final_round].copy()
    final_points = final_points.sort_values(
        ["CumulativePoints", entity_column],
        ascending=[False, True],
    )
    return final_points[entity_column].tolist()


def _latest_team_by_driver(event_points: pd.DataFrame) -> dict[str, str]:
    latest = event_points.sort_values(["Driver", "RoundNumber"]).drop_duplicates(
        subset=["Driver"],
        keep="last",
    )
    return dict(zip(latest["Driver"], latest["Team"]))


def _build_driver_style_map(
    driver_points: pd.DataFrame,
    latest_team_by_driver: dict[str, str],
) -> dict[str, tuple[str, str]]:
    final_order = _final_order(driver_points, "Driver")
    style_map = {}
    team_driver_order: dict[str, list[str]] = {}
    for driver in final_order:
        team = latest_team_by_driver.get(driver, "")
        team_driver_order.setdefault(team, []).append(driver)

    for drivers in team_driver_order.values():
        for idx, driver in enumerate(drivers):
            style_map[driver] = (
                DRIVER_LINESTYLES[idx % len(DRIVER_LINESTYLES)],
                DRIVER_MARKERS[idx % len(DRIVER_MARKERS)],
            )
    return style_map


def _short_event_name(event_name: object) -> str:
    return str(event_name).replace("Grand Prix", "").strip()


__all__ = [
    "plot_points_progression",
    "save_points_progression_figures",
]
