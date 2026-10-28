import json

import pytest
import requests
import responses

from jobmarket.extract import FranceTravailClient, _parse_total

AUTH_URL = "https://auth.test/token"
SEARCH_URL = "https://api.test/offres/search"


def make_client(page_size: int = 2) -> FranceTravailClient:
    return FranceTravailClient(
        client_id="id",
        client_secret="secret",
        auth_url=AUTH_URL,
        search_url=SEARCH_URL,
        scope="api_offresdemploiv2",
        page_size=page_size,
        request_delay_s=0,
        session=requests.Session(),  # pas de retry automatique dans les tests
    )


def offers(*ids: str) -> dict:
    return {"resultats": [{"id": i} for i in ids]}


@pytest.fixture
def api():
    with responses.RequestsMock() as rsps:
        rsps.post(AUTH_URL, json={"access_token": "tok", "expires_in": 1499})
        yield rsps


def test_paginates_until_last_page(api):
    api.get(SEARCH_URL, json=offers("a", "b"), status=206, headers={"Content-Range": "offres 0-1/3"})
    api.get(SEARCH_URL, json=offers("c"), status=200, headers={"Content-Range": "offres 2-2/3"})

    result = list(make_client().iter_offers("data"))

    assert [o["id"] for o in result] == ["a", "b", "c"]
    search_calls = [c for c in api.calls if c.request.url.startswith(SEARCH_URL)]
    assert "range=0-1" in search_calls[0].request.url
    assert "range=2-3" in search_calls[1].request.url
    assert search_calls[0].request.headers["Authorization"] == "Bearer tok"


def test_no_content_returns_nothing(api):
    api.get(SEARCH_URL, status=204)
    assert list(make_client().iter_offers("rien")) == []


def test_token_is_reused_between_calls(api):
    api.get(SEARCH_URL, json=offers("a"), status=200)
    api.get(SEARCH_URL, json=offers("b"), status=200)

    make_client().search(["data", "ia"])

    auth_calls = [c for c in api.calls if c.request.url == AUTH_URL]
    assert len(auth_calls) == 1


def test_search_tags_each_offer_with_its_keyword(api):
    api.get(SEARCH_URL, json=offers("a"), status=200)
    api.get(SEARCH_URL, json=offers("a", "b"), status=200)

    records = make_client(page_size=150).search(["data engineer", "big data"])

    assert [(r["id"], r["_mot_cle"]) for r in records] == [
        ("a", "data engineer"),
        ("a", "big data"),
        ("b", "big data"),
    ]


def test_stops_at_api_range_limit(api):
    # L'API refuse un début > 1000 et une fin > 1149 : 1150 offres maximum par recherche.
    def page(request):
        start, end = map(int, request.params["range"].split("-"))
        body = json.dumps(offers(*[str(i) for i in range(start, end + 1)]))
        return 206, {"Content-Range": f"offres {start}-{end}/5000"}, body

    api.add_callback(responses.GET, SEARCH_URL, callback=page)

    result = list(make_client(page_size=150).iter_offers("data"))

    assert [o["id"] for o in result] == [str(i) for i in range(1150)]
    ranges = [c.request.params["range"] for c in api.calls if c.request.url.startswith(SEARCH_URL)]
    assert ranges[-2:] == ["900-1049", "1000-1149"]


def test_http_error_is_raised(api):
    api.get(SEARCH_URL, status=400, json={"message": "range invalide"})
    with pytest.raises(requests.HTTPError):
        list(make_client().iter_offers("data"))


@pytest.mark.parametrize(
    ("header", "expected"),
    [("offres 0-149/2345", 2345), ("0-9/10", 10), (None, None), ("n'importe quoi", None)],
)
def test_parse_total(header, expected):
    assert _parse_total(header) == expected
