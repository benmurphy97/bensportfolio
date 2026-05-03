import requests
import numpy as np
import pandas as pd
import cache

# ── Data fetchers ──────────────────────────────────────────────────────────────

def get_league_data(league_id):
    data = cache.get(league_id)
    if data:
        return data
    response = requests.get(
        f"https://draft.premierleague.com/api/league/{league_id}/details",
        timeout=15
    )
    response.raise_for_status()
    data = response.json()
    cache.set(league_id, data)
    return data

# ── Current Standings ──────────────────────────────────────────────────────────

def get_current_standings(league_data):
    """
    Returns:
        standings: list of dicts for the standings table
        scatter: list of {x, y, label} for avg pts for vs against chart
    """
    id_name = {e["id"]: e["short_name"] for e in league_data["league_entries"]}

    df = pd.DataFrame(league_data["standings"])
    df["player"] = df["league_entry"].map(id_name)
    df["games_played"] = df["matches_won"] + df["matches_lost"] + df["matches_drawn"]
    df["avg_pts_for"] = (df["points_for"] / df["games_played"]).round(1)
    df["avg_pts_against"] = (df["points_against"] / df["games_played"]).round(1)

    standings = df[[
        "rank", "player", "matches_won", "matches_drawn", "matches_lost",
        "points_for", "points_against", "total"
    ]].rename(columns={
        "rank": "Pos", "player": "Player",
        "matches_won": "W", "matches_drawn": "D", "matches_lost": "L",
        "points_for": "PF", "points_against": "PA", "total": "Pts"
    }).sort_values("Pos").to_dict("records")

    scatter = [
        {"x": row["avg_pts_for"], "y": row["avg_pts_against"], "label": row["player"]}
        for _, row in df.iterrows()
    ]

    return standings, scatter


# ── Expected Standings ─────────────────────────────────────────────────────────

def get_expected_standings(league_data):
    """
    Calculates expected points based on how each player's weekly score
    ranks against all other players that week.
    Returns list of dicts for the expected standings table.
    """
    id_name = {e["id"]: e["short_name"] for e in league_data["league_entries"]}
    n = len(league_data["league_entries"])

    matches = pd.DataFrame(league_data["matches"])
    finished = matches[matches["finished"]].copy()

    if finished.empty:
        return []

    # Build one row per player per match (both perspectives)
    m1 = finished.rename(columns={
        "event": "week",
        "league_entry_1": "player", "league_entry_1_points": "pts_for",
        "league_entry_2": "opponent", "league_entry_2_points": "pts_against"
    })[["week", "player", "pts_for", "pts_against"]]

    m2 = finished.rename(columns={
        "event": "week",
        "league_entry_2": "player", "league_entry_2_points": "pts_for",
        "league_entry_1": "opponent", "league_entry_1_points": "pts_against"
    })[["week", "player", "pts_for", "pts_against"]]

    df = pd.concat([m1, m2]).reset_index(drop=True)
    df["player"] = df["player"].map(id_name)

    # Expected points: beat X out of N-1 opponents → (X / N-1) * 3
    df["week_rank"] = df.groupby("week")["pts_for"].rank(ascending=False, method="max")
    df["opponents_beaten"] = n - df["week_rank"]
    df["expected_pts"] = (df["opponents_beaten"] / (n - 1) * 3).round(3)

    expected = df.groupby("player")["expected_pts"].sum().round(2).reset_index()

    # Merge with actual standings
    actual = pd.DataFrame(league_data["standings"])
    actual["player"] = actual["league_entry"].map(id_name).str.strip()
    actual = actual[["player", "rank", "total"]].rename(columns={
        "rank": "actual_pos", "total": "actual_pts"
    })

    result = actual.merge(expected, on="player")
    result["over_under"] = (result["actual_pts"] - result["expected_pts"]).round(2)
    result["expected_pos"] = result["expected_pts"].rank(ascending=False).astype(int)
    result = result.sort_values("expected_pts", ascending=False)

    return result[[
        "player", "expected_pos", "expected_pts",
        "actual_pts", "actual_pos", "over_under"
    ]].rename(columns={
        "player": "Player", "expected_pos": "xPos", "expected_pts": "xPts",
        "actual_pts": "Actual Pts", "actual_pos": "Actual Pos",
        "over_under": "+/-"
    }).to_dict("records")


# ── Monte Carlo Predicted Standings ───────────────────────────────────────────

GAMMA_MIN_SAMPLES = 5

def get_predicted_standings(league_data, n_simulations=1000):
    id_name = {e["id"]: e["short_name"] for e in league_data["league_entries"]}
    n_teams = len(league_data["league_entries"])

    matches = pd.DataFrame(league_data["matches"])
    finished = matches[matches["finished"]].copy()
    upcoming = matches[~matches["finished"]].copy()

    m1 = finished[["event", "league_entry_1", "league_entry_1_points"]].rename(
        columns={"event": "week", "league_entry_1": "team", "league_entry_1_points": "pts"})
    m2 = finished[["event", "league_entry_2", "league_entry_2_points"]].rename(
        columns={"event": "week", "league_entry_2": "team", "league_entry_2_points": "pts"})
    weekly = pd.concat([m1, m2]).groupby(["team", "week"])["pts"].sum().reset_index()

    # Fit Gamma (method-of-moments = MLE for 2-param Gamma with loc=0) or fall back to bootstrap
    team_samplers = {}
    for team_id, group in weekly.groupby("team"):
        scores = group["pts"].values.astype(float)
        var = scores.var()
        if len(scores) >= GAMMA_MIN_SAMPLES and var > 0:
            mean = scores.mean()
            team_samplers[team_id] = ("gamma", (mean ** 2 / var, var / mean))
        else:
            team_samplers[team_id] = ("bootstrap", scores)

    def bulk_sample(team_id, n):
        method, params = team_samplers[team_id]
        if method == "gamma":
            shape, scale = params
            return np.random.gamma(shape, scale, size=n)
        return np.random.choice(params, size=n).astype(float)

    # Pre-generate all scores upfront — one vectorised call per team per match
    match_samples = []
    for _, match in upcoming.iterrows():
        t1, t2 = match["league_entry_1"], match["league_entry_2"]
        match_samples.append((t1, t2, bulk_sample(t1, n_simulations), bulk_sample(t2, n_simulations)))

    standings = pd.DataFrame(league_data["standings"]).set_index("league_entry")
    current_totals = standings["total"].to_dict()
    rank_counts = {team: np.zeros(n_teams, dtype=int) for team in current_totals}

    for sim in range(n_simulations):
        sim_totals = current_totals.copy()
        for t1, t2, s1_all, s2_all in match_samples:
            s1, s2 = s1_all[sim], s2_all[sim]
            if s1 > s2:
                sim_totals[t1] += 3
            elif s2 > s1:
                sim_totals[t2] += 3
            else:
                sim_totals[t1] += 1
                sim_totals[t2] += 1

        sorted_teams = sorted(sim_totals, key=lambda t: sim_totals[t], reverse=True)
        for rank, team in enumerate(sorted_teams):
            rank_counts[team][rank] += 1

    position_cols = [f"P{i+1}" for i in range(n_teams)]
    rows = []
    for team_id, counts in rank_counts.items():
        probs = (counts / n_simulations * 100).round(1)
        rows.append({"Team": id_name[team_id], **dict(zip(position_cols, probs))})

    df = pd.DataFrame(rows).sort_values("P1", ascending=False).reset_index(drop=True)
    return df.to_dict("records"), position_cols