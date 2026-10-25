"""Tests run against a temporary copy of the app.

Importing app.main resets the game (players, answers, game state) and the app writes
its files next to the app folder, so the copy keeps the real database, game state and
saved configurations in the project folder untouched, even when tests run locally.
"""
import os
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def app_module(tmp_path_factory):
    work = tmp_path_factory.mktemp("quiz_app")
    shutil.copytree(ROOT / "app", work / "app", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(ROOT / "frontend", work / "frontend")
    os.chdir(work)  # the SQLite database path is relative to the working directory
    sys.path.insert(0, str(work))
    import app.main
    assert Path(app.main.__file__).resolve().is_relative_to(work), "imported the real app, not the copy"
    return app.main


@pytest.fixture(scope="session")
def client(app_module):
    from fastapi.testclient import TestClient
    return TestClient(app_module.app)
