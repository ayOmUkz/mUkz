"""Tests for the Unusual Whales API client (all network mocked with respx)."""

import httpx
import pytest
import respx

from app.client.uw_client import UWAPIError, UWClient, UWRateLimitError

BASE = "https://api.unusualwhales.com"


def make_client(**kwargs) -> UWClient:
    client = UWClient("test-token", requests_per_minute=100_000, **kwargs)
    client._sleep = lambda seconds: None  # never actually sleep in tests
    return client


def test_empty_or_placeholder_token_is_rejected():
    with pytest.raises(ValueError):
        UWClient("")
    with pytest.raises(ValueError):
        UWClient("***")  # the .env.example placeholder


def test_repr_never_contains_token():
    with make_client() as client:
        assert "test-token" not in repr(client)


@respx.mock
def test_auth_header_and_data_unwrap():
    route = respx.get(f"{BASE}/api/darkpool/recent").mock(
        return_value=httpx.Response(200, json={"data": [{"ticker": "TSM"}]})
    )
    with make_client() as client:
        rows = client.recent_darkpool_trades(limit=1, min_premium=1_000_000)
    assert rows == [{"ticker": "TSM"}]
    request = route.calls.last.request
    assert request.headers["Authorization"] == "Bearer test-token"
    assert "min_premium=1000000" in str(request.url)


@respx.mock
def test_none_params_are_omitted():
    route = respx.get(f"{BASE}/api/darkpool/recent").mock(
        return_value=httpx.Response(200, json={"data": []})
    )
    with make_client() as client:
        client.recent_darkpool_trades()
    assert "min_premium" not in str(route.calls.last.request.url)


@respx.mock
def test_retries_on_429_then_succeeds():
    route = respx.get(f"{BASE}/api/darkpool/recent")
    route.side_effect = [
        httpx.Response(429, headers={"Retry-After": "1"}),
        httpx.Response(200, json={"data": []}),
    ]
    with make_client() as client:
        assert client.recent_darkpool_trades() == []
    assert route.call_count == 2


@respx.mock
def test_rate_limit_exhaustion_raises_specific_error():
    respx.get(f"{BASE}/api/darkpool/recent").mock(return_value=httpx.Response(429))
    with make_client(max_retries=2) as client:
        with pytest.raises(UWRateLimitError):
            client.recent_darkpool_trades()


@respx.mock
def test_http_error_raises_without_leaking_token():
    respx.get(f"{BASE}/api/darkpool/TSM").mock(return_value=httpx.Response(404, text="not found"))
    with make_client() as client:
        with pytest.raises(UWAPIError) as excinfo:
            client.ticker_darkpool_trades("TSM")
    assert excinfo.value.status_code == 404
    assert "test-token" not in str(excinfo.value)


@respx.mock
def test_network_error_retries_then_raises():
    route = respx.get(f"{BASE}/api/darkpool/recent")
    route.side_effect = httpx.ConnectError("boom")
    with make_client(max_retries=1) as client:
        with pytest.raises(UWAPIError):
            client.recent_darkpool_trades()
    assert route.call_count == 2  # first try + one retry


@respx.mock
def test_pagination_walks_older_than_and_dedupes():
    page1 = {
        "data": [
            {"tracking_id": 1, "executed_at": "2026-08-05T16:00:59Z"},
            {"tracking_id": 2, "executed_at": "2026-08-05T16:00:58Z"},
            {"tracking_id": 3, "executed_at": "2026-08-05T16:00:57Z"},
        ]
    }
    page2 = {
        "data": [
            {"tracking_id": 3, "executed_at": "2026-08-05T16:00:57Z"},  # boundary duplicate
            {"tracking_id": 4, "executed_at": "2026-08-05T15:00:00Z"},
        ]
    }
    route = respx.get(f"{BASE}/api/darkpool/TSM")
    route.side_effect = [
        httpx.Response(200, json=page1),
        httpx.Response(200, json=page2),
    ]
    with make_client() as client:
        rows = list(client.iter_ticker_darkpool_trades("TSM", page_limit=3))
    assert [row["tracking_id"] for row in rows] == [1, 2, 3, 4]
    second_request = route.calls[1].request
    assert "older_than=2026-08-05T16%3A00%3A57Z" in str(second_request.url)


@respx.mock
def test_price_levels_endpoint():
    respx.get(f"{BASE}/api/darkpool/NVDA/price-levels").mock(
        return_value=httpx.Response(200, json={"data": {"stock_price_vol": []}})
    )
    with make_client() as client:
        levels = client.darkpool_price_levels("NVDA", date="2026-08-05")
    assert levels == {"stock_price_vol": []}
