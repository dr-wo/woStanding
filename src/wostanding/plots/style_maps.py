from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd

F1_TEAM_COLORS = {
    "Ferrari": "#dc0000",
    "McLaren": "#ff8700",
    "Red Bull Racing": "#3029ed",
    "Red Bull": "#3029ed",
    "Mercedes": "#00fbe2",
    "Aston Martin": "#006f62",
    "Alpine": "#ff87bc",
    "Williams": "#1f6af4ff",
    "Haas F1 Team": "#6e6e6e",
    "Haas": "#6e6e6e",
    "Cadillac": "#82d8f4",
    "Kick Sauber": "#00e701",
    "Sauber": "#00e701",
    "Audi": "#000000",
    "Racing Bulls": "#5e59ee",
    "RB": "#5e59ee",
}


def build_team_color_map(teams: pd.Series) -> dict[str, object]:
    team_names = sorted(teams.dropna().unique())
    fallback_cmap = plt.get_cmap("tab20")
    fallback_team_colors = {
        team: fallback_cmap(idx % fallback_cmap.N)
        for idx, team in enumerate(team_names)
    }
    return {
        team: F1_TEAM_COLORS.get(team, fallback_team_colors[team])
        for team in team_names
    }


__all__ = [
    "F1_TEAM_COLORS",
    "build_team_color_map",
]
