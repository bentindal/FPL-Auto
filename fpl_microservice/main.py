import sys
from contextlib import asynccontextmanager
sys.path.insert(0, '.')  # ensure fpl_auto package is importable

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fpl_auto.data import get_fpl_data

_SEASONS = ['2021-22', '2022-23', '2023-24', '2024-25']
_fpl_data_instances = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Eager model load at startup (D-01)
    # Loads all season data before accepting requests so first call isn't slow
    for season in _SEASONS:
        _fpl_data_instances[season] = get_fpl_data('data', season)
    yield
    # Shutdown: nothing to clean up


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


@app.get("/health")
def health():
    return {"status": "ok", "seasons_loaded": list(_fpl_data_instances.keys())}
