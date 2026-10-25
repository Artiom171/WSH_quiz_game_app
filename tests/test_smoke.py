"""Smoke tests: the app starts, serves the player page and registers players."""


def test_player_page_is_served(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]


def test_game_is_not_started_after_server_start(client):
    res = client.get("/game/status")
    assert res.status_code == 200
    data = res.json()
    assert data["started"] is False
    assert "game_id" in data


def test_player_can_register_and_see_own_answers(client):
    res = client.post("/session", json={"name": "Anna"})
    assert res.status_code == 200
    session_id = res.json()["session_id"]

    res = client.get(f"/answers/by-session/{session_id}")
    assert res.status_code == 200
    assert res.json() == []


def test_player_name_is_validated(client):
    client.post("/session", json={"name": "Boris"})
    assert client.post("/session", json={"name": "boris"}).status_code == 400  # taken, any case
    assert client.post("/session", json={"name": "   "}).status_code == 400
    assert client.post("/session", json={"name": "bad name!"}).status_code == 400
    assert client.post("/session", json={"name": "x" * 41}).status_code == 400
    assert client.post("/session", json={"name": "Иван2"}).status_code == 200


def test_unknown_session_is_rejected(client):
    # the app turns a 404 into a redirect to its error page
    res = client.get("/answers/by-session/999999", follow_redirects=False)
    assert res.status_code in (307, 404)
    if res.status_code == 307:
        assert "error_page" in res.headers["location"]
