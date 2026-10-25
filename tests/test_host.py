"""Host side: login, saving game configs, and what the host screen and phones get."""
import pytest
from fastapi.testclient import TestClient

THEME = {"bg": "#0a0b14", "accent": "#fcee0a", "answer": "#00f0ff",
         "text": "#ffffff", "glow1": "#ff003c", "glow2": "#00b7ff"}


def make_config(**overrides):
    question = {
        "type": "image",
        "text": "Что общего у этих актёров?",
        "media_url": "/uploads/a.jpg",
        "question_images": [{"url": "/uploads/a.jpg", "caption": "Том Хэнкс"},
                            {"url": "/uploads/b.jpg"}],
        "answer": "SECRET-ANSWER",
        "answer_description": "Все они Томы",
        "answer_images": [{"url": "/uploads/c.jpg", "caption": "Том Круз"}],
        "rebus": True,
        "timer_seconds": 30,
    }
    config = {
        "name": "Тестовая игра",
        "tours": [{"type": "ordinary", "name": "Тур с фото", "questions_data": [question]}],
        "theme": THEME,
        "theme_choice": {"base": "Киберпанк", "custom": {"bg": "#0a0b14"}},
    }
    config.update(overrides)
    return config


@pytest.fixture(scope="module")
def host(app_module):
    """A client logged in as the host."""
    c = TestClient(app_module.app)
    res = c.post("/api/config-login", json={"username": app_module._ADMIN_USERNAME,
                                            "password": app_module._load_password()})
    assert res.status_code == 200
    return c


def test_host_pages_require_login(client):
    res = client.get("/config.html", follow_redirects=False)
    assert res.status_code == 302
    assert "config_login.html" in res.headers["location"]
    assert client.get("/configs").status_code == 401
    assert client.post("/configs", json=make_config()).status_code == 401


def test_wrong_password_is_rejected(client, app_module):
    res = client.post("/api/config-login", json={"username": app_module._ADMIN_USERNAME,
                                                 "password": "definitely-wrong"})
    assert res.status_code == 401


def test_config_keeps_images_rebus_and_theme(host):
    res = host.post("/configs", json=make_config())
    assert res.status_code == 200
    config = host.get(f"/configs/{res.json()['id']}").json()

    q = config["tours"][0]["questions_data"][0]
    assert q["question_images"] == [{"url": "/uploads/a.jpg", "caption": "Том Хэнкс"},
                                    {"url": "/uploads/b.jpg", "caption": ""}]
    assert q["answer_images"] == [{"url": "/uploads/c.jpg", "caption": "Том Круз"}]
    assert q["rebus"] is True
    assert config["theme"] == THEME
    assert config["theme_choice"] == {"base": "Киберпанк", "custom": {"bg": "#0a0b14"}}


def test_config_update_keeps_the_same_config(host):
    config_id = host.post("/configs", json=make_config()).json()["id"]
    res = host.put(f"/configs/{config_id}", json=make_config(name="Переименованная"))
    assert res.status_code == 200
    assert host.get(f"/configs/{config_id}").json()["name"] == "Переименованная"


@pytest.mark.parametrize("bad", [
    {"theme": {**THEME, "bg": "red"}},
    {"theme": {**THEME, "accent": "#fff"}},
    {"theme_choice": {"base": "Лайм", "custom": {"unknown": "#000000"}}},
])
def test_bad_theme_is_rejected(host, bad):
    assert host.post("/configs", json=make_config(**bad)).status_code == 422


def test_phones_get_theme_but_no_questions_or_answers(host, client):
    config_id = host.post("/configs", json=make_config()).json()["id"]
    assert host.post("/game/start", json={"config_id": config_id}).status_code == 200
    try:
        host_view = host.get("/game/status").json()
        assert host_view["started"] is True
        assert host_view["config"]["theme"] == THEME
        assert host_view["config"]["tours"][0]["questions_data"][0]["answer"] == "SECRET-ANSWER"

        player_view = client.get("/game/status")
        assert player_view.json()["config"]["theme"] == THEME
        assert player_view.json()["config"]["tours"][0]["questions_data"] == [{"timer_seconds": 30}]
        assert "SECRET-ANSWER" not in player_view.text
        assert "Что общего" not in player_view.text
    finally:
        # leave no running game behind for the other tests
        assert host.post("/game/quit").status_code == 200
    assert client.get("/game/status").json()["started"] is False
