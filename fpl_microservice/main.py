import sys
import json
from pathlib import Path
from contextlib import asynccontextmanager
sys.path.insert(0, '.')  # ensure fpl_auto package is importable

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fpl_auto.data import get_fpl_data

_SEASONS = ['2021-22', '2022-23', '2023-24', '2024-25']
_fpl_data_instances = {}

# Pre-computed top-100 weekly averages, keyed by season string.
# Populated at startup and refreshable via POST /top100/refresh.
_top100_weekly_avg: dict[str, dict[str, float]] = {}

_TOP100_DATA_PATHS: dict[str, Path] = {
    "2025-26": Path("data/season_winners_2025-26"),
}


def _compute_top100_weekly_avg(season: str) -> dict[str, float]:
    """Read per-GW points from local season_winners archive and average across managers."""
    data_dir = _TOP100_DATA_PATHS.get(season)
    if data_dir is None or not data_dir.is_dir():
        return {}

    gw_totals: dict[int, list[int]] = {}
    for mgr_dir in data_dir.iterdir():
        if not mgr_dir.is_dir() or not mgr_dir.name.isdigit():
            continue
        season_file = mgr_dir / "_complete_season.json"
        if not season_file.exists():
            continue
        with season_file.open() as f:
            season_data = json.load(f)
        for gw_str, gw_data in season_data.items():
            try:
                gw = int(gw_str)
                pts = gw_data["entry_history"]["points"]
                gw_totals.setdefault(gw, []).append(pts)
            except (KeyError, ValueError):
                continue

    return {
        str(gw): round(sum(pts) / len(pts), 1)
        for gw, pts in sorted(gw_totals.items())
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Eager model load at startup (D-01)
    for season in _SEASONS:
        _fpl_data_instances[season] = get_fpl_data('data', season)

    # Pre-compute top-100 weekly averages from local archive files
    for season in _TOP100_DATA_PATHS:
        _top100_weekly_avg[season] = _compute_top100_weekly_avg(season)

    yield


app = FastAPI(lifespan=lifespan)


class XpRequest(BaseModel):
    season: str
    gameweek: int
    position: str  # 'GK', 'DEF', 'MID', 'FWD'


@app.post("/xp/single_gw")
def xp_single_gw(req: XpRequest):
    """Returns single-GW predictions (_xp_dicts equivalent). Used for sub suggestions."""
    fpl_data = _fpl_data_instances.get(req.season)
    if not fpl_data:
        raise HTTPException(status_code=400, detail=f"Season {req.season} not loaded")
    df = fpl_data.get_predictions(req.gameweek, req.position)
    return {"predictions": df.set_index('Name')['xP'].to_dict()}


@app.post("/xp/lookahead")
def xp_lookahead(req: XpRequest):
    """Returns 5-GW discounted predictions (_all_xp_dicts equivalent). Used for transfers/captain."""
    fpl_data = _fpl_data_instances.get(req.season)
    if not fpl_data:
        raise HTTPException(status_code=400, detail=f"Season {req.season} not loaded")
    df = fpl_data.get_predictions(req.gameweek, req.position)
    discounted = fpl_data.discount_next_n_gws([df], req.gameweek, n=5, discount_factor=0.8)
    return {"predictions": discounted[0].set_index('Name')['xP'].to_dict()}


class BestAltRequest(BaseModel):
    season: str
    gameweek: int
    position: str            # 'GK' | 'DEF' | 'MID' | 'FWD'
    budget: float            # selling price of transferred-out player, in millions (e.g. 7.5)
    transferred_out_name: str
    squad_player_names: list[str]   # current squad names, for the 3-per-club rule


@app.post("/scoring/best_alt")
def best_alt(req: BestAltRequest):
    """Returns the best affordable, club-legal alternative player for a position at a GW.

    Uses single-GW xP predictions (historical decision -> single-GW source per CLAUDE.md).
    Mirrors suggest_transfer_in logic WITHOUT the xp_gain >= 2 threshold.
    Returns {"best_alt_name": <name or None>, "best_alt_xp": <float or None>}.
    """
    fpl_data = _fpl_data_instances.get(req.season)
    if not fpl_data:
        raise HTTPException(status_code=400, detail=f"Season {req.season} not loaded")

    # Single-GW xP predictions for this position
    preds = fpl_data.get_predictions(req.gameweek, req.position)
    # Sort candidates by xP descending
    candidates = preds.sort_values(by='xP', ascending=False)[['Name', 'xP']].values.tolist()

    # GW data for prices and team lookups
    gw_data = fpl_data.get_gw_data(req.season, req.gameweek)

    # Pre-compute club counts from squad_player_names using gw_data team column
    club_counts: dict = {}
    for name in req.squad_player_names:
        try:
            team = gw_data.loc[name]['team']
            if team is not None:
                club_counts[str(team)] = club_counts.get(str(team), 0) + 1
        except KeyError:
            pass  # player not in gw_data — skip (mirrors suggest_transfer_in robustness)

    for candidate in candidates:
        name, xp = candidate[0], float(candidate[1])

        # Skip the transferred-out player and anyone already in the squad
        if name == req.transferred_out_name or name in req.squad_player_names:
            continue

        # Price check — value column is in tenths
        try:
            p_cost = gw_data.loc[name]['value']
        except KeyError:
            continue  # player not in gw_data — skip
        if p_cost is None:
            continue
        p_cost = float(p_cost) / 10.0
        if p_cost > req.budget:
            continue

        # Club rule: max 3 players per club
        try:
            player_club = str(fpl_data.get_player_team(name, req.gameweek, gw_data))
        except Exception:
            continue
        if player_club == 'None':
            continue
        if club_counts.get(player_club, 0) + 1 > 3:
            continue

        # First candidate that passes all filters is the best alternative
        return {"best_alt_name": name, "best_alt_xp": xp}

    return {"best_alt_name": None, "best_alt_xp": None}


@app.get("/top100/weekly_avg")
def top100_weekly_avg(season: str = "2025-26"):
    """Returns pre-computed top-100 manager average GW points.

    Data is loaded from local season_winners archive at startup.
    Call POST /top100/refresh to reload after the archive files change.
    """
    data = _top100_weekly_avg.get(season)
    if data is None:
        raise HTTPException(status_code=404, detail=f"No top-100 data for season {season}")
    return {"weekly_avg": data}


@app.post("/top100/refresh")
def top100_refresh(season: str = "2025-26"):
    """Re-reads the local season_winners archive and refreshes the in-memory cache.

    Intended to be called by a daily Sidekiq cron job after the archive is updated.
    """
    if season not in _TOP100_DATA_PATHS:
        raise HTTPException(status_code=404, detail=f"No archive path configured for season {season}")
    _top100_weekly_avg[season] = _compute_top100_weekly_avg(season)
    return {"refreshed": season, "gameweeks": len(_top100_weekly_avg[season])}


@app.get("/health")
def health():
    return {"status": "ok", "seasons_loaded": list(_fpl_data_instances.keys())}
