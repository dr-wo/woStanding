from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd

from wodata.colours import F1_TEAM_COLORS


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
