"""Tests for the /scoring/best_alt endpoint.

Run from the fpl-auto root directory so prediction TSVs and data/ CSVs resolve:
  /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 \
      -m pytest fpl_microservice/test_scoring.py -q
"""
import sys

# Ensure fpl_auto package is importable when tests are run from the fpl-auto root
sys.path.insert(0, '.')

import pytest
from fastapi.testclient import TestClient

from fpl_microservice.main import app


# ---------------------------------------------------------------------------
# Fixture: a TestClient that triggers the lifespan (loads season data)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def loaded_client():
    """TestClient used as context manager so the lifespan loads season data."""
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# /scoring/best_alt — happy path
# ---------------------------------------------------------------------------

def test_best_alt_returns_player_for_mid_position(loaded_client):
    """A generous budget with an empty squad should return the highest-xP MID."""
    response = loaded_client.post("/scoring/best_alt", json={
        "season": "2024-25",
        "gameweek": 4,
        "position": "MID",
        "budget": 13.0,
        "transferred_out_name": "Nonexistent Player",
        "squad_player_names": []
    })
    assert response.status_code == 200
    data = response.json()
    assert "best_alt_name" in data
    assert "best_alt_xp" in data
    # With a 13.0 budget and no squad constraints a player must be found
    assert data["best_alt_name"] is not None
    assert isinstance(data["best_alt_xp"], (int, float))
    assert data["best_alt_xp"] > 0


def test_best_alt_zero_budget_returns_none(loaded_client):
    """A budget of 0.0 cannot afford any player — should return nulls."""
    response = loaded_client.post("/scoring/best_alt", json={
        "season": "2024-25",
        "gameweek": 4,
        "position": "MID",
        "budget": 0.0,
        "transferred_out_name": "Nonexistent Player",
        "squad_player_names": []
    })
    assert response.status_code == 200
    data = response.json()
    assert data["best_alt_name"] is None
    assert data["best_alt_xp"] is None


# ---------------------------------------------------------------------------
# /scoring/best_alt — error handling
# ---------------------------------------------------------------------------

def test_best_alt_unknown_season_returns_400(loaded_client):
    """An unloaded season should return HTTP 400."""
    response = loaded_client.post("/scoring/best_alt", json={
        "season": "1999-00",
        "gameweek": 1,
        "position": "MID",
        "budget": 13.0,
        "transferred_out_name": "Someone",
        "squad_player_names": []
    })
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Existing endpoints remain untouched
# ---------------------------------------------------------------------------

def test_health_endpoint_still_works(loaded_client):
    response = loaded_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "2024-25" in data["seasons_loaded"]


def test_xp_single_gw_still_works(loaded_client):
    response = loaded_client.post("/xp/single_gw", json={
        "season": "2024-25",
        "gameweek": 4,
        "position": "MID"
    })
    assert response.status_code == 200
    assert "predictions" in response.json()
