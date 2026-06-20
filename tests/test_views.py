"""Tests for the server-rendered page routes (the HTML shell, not the JSON API).

These confirm each screen's route resolves and renders its base shell; the live
data is fetched client-side, so we assert on the static markup the template
produces, not on obligation rows.
"""


def test_index_renders(app):
    res = app.test_client().get("/")
    assert res.status_code == 200
    body = res.get_data(as_text=True)
    assert "DayQuest" in body
    # Home links through to the obligations sub-page (a real href, not just the
    # /api/obligations comment).
    assert 'href="/obligations"' in body


def test_obligations_page_renders(app):
    res = app.test_client().get("/obligations")
    assert res.status_code == 200
    body = res.get_data(as_text=True)
    # Sub-page title (canonical top bar is overridden, so no wordmark required).
    assert "Obligations Vault" in body
    # Inline capture field and its client wiring are present.
    assert 'id="capture-input"' in body
    assert "obligations.js" in body
    # Back arrow returns to home.
    assert 'href="/"' in body
