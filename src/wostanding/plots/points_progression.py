from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from wostanding.analysis.points_progression import PointsProgressionResult
from wostanding.plots.style_maps import build_team_color_map

DRIVER_LINESTYLES = ("-", "--", ":", "-.")
DRIVER_MARKERS = ("o", "s", "^", "D")


def plot_points_progression(
    result: PointsProgressionResult,
    *,
    title: str | None = None,
) -> dict[str, tuple[plt.Figure, plt.Axes, pd.DataFrame]]:
    driver_fig, driver_ax = _plot_driver_points(
        result.driver_points,
        result.event_points,
        title=title,
    )
    team_fig, team_ax = _plot_team_points(result.team_points, title=title)
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
) -> tuple[plt.Figure, plt.Axes]:
    team_color_map = build_team_color_map(event_points["Team"])
    latest_team_by_driver = _latest_team_by_driver(event_points)
    driver_style_map = _build_driver_style_map(driver_points, latest_team_by_driver)

    fig, ax = plt.subplots(figsize=(14, 8))
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

    _format_points_axis(
        ax,
        driver_points,
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
) -> tuple[plt.Figure, plt.Axes]:
    team_color_map = build_team_color_map(team_points["Team"])

    fig, ax = plt.subplots(figsize=(14, 8))
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

    _format_points_axis(
        ax,
        team_points,
        title=title or "Team Points Progression",
        ylabel="Team points",
    )
    ax.legend(loc="center left", bbox_to_anchor=(1.01, 0.5), fontsize=9)
    fig.tight_layout()
    return fig, ax


def _format_points_axis(
    ax: plt.Axes,
    points: pd.DataFrame,
    *,
    title: str,
    ylabel: str,
) -> None:
    round_labels = (
        points.loc[:, ["RoundNumber", "EventName"]]
        .drop_duplicates()
        .sort_values("RoundNumber")
    )
    ax.set_xlabel("Round")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.set_xticks(round_labels["RoundNumber"])
    labels = [
        f"R{round_number}\n{_short_event_name(event_name)}"
        for round_number, event_name in round_labels.itertuples(index=False)
    ]
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.grid(True, which="major", alpha=0.3)
    ax.set_ylim(bottom=0)


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
