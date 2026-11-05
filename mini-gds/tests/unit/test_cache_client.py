import json
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

import pytest

from mini_gds.cache_client import CacheUnavailableError, HostUnavailableError, HttpCache


class CacheService(BaseHTTPRequestHandler):
    """A stand-in for the cache service: it answers with the status the test chose."""

    status = 200
    body: dict = {}

    def _answer(self) -> None:
        payload = json.dumps(self.body).encode()
        self.send_response(self.status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    do_GET = do_POST = _answer

    def log_message(self, *args) -> None:  # keep the test output quiet
        pass


@pytest.fixture
def service() -> Iterator[type[CacheService]]:
    server = HTTPServer(("127.0.0.1", 0), CacheService)
    Thread(target=server.serve_forever, daemon=True).start()
    CacheService.base_url = f"http://127.0.0.1:{server.server_port}"
    yield CacheService
    server.shutdown()
    server.server_close()


def answer(service: type[CacheService], status: int, body: dict) -> HttpCache:
    service.status, service.body = status, body
    return HttpCache(service.base_url)


def test_a_cache_service_that_cannot_be_reached_is_unavailable_not_a_crash() -> None:
    cache = HttpCache("http://127.0.0.1:9")  # nothing listens on the discard port
    with pytest.raises(CacheUnavailableError):
        cache.seats("AA100", "M")
    with pytest.raises(CacheUnavailableError):
        cache.wash([("AA100", "M")], 1)


def test_seats_are_read_from_the_answer(service) -> None:
    assert answer(service, 200, {"seats": 4}).seats("AA100", "M") == 4


def test_a_503_means_the_airline_host_cannot_answer(service) -> None:
    with pytest.raises(HostUnavailableError):
        answer(service, 503, {}).seats("AA100", "M")


@pytest.mark.parametrize("status", [500, 502, 504])
def test_any_other_server_error_means_the_cache_service_failed(service, status: int) -> None:
    cache = answer(service, status, {})
    with pytest.raises(CacheUnavailableError):
        cache.seats("AA100", "M")
    with pytest.raises(CacheUnavailableError):
        cache.wash([("AA100", "M")], 1)


def test_a_wash_returns_the_offers_to_show_and_the_errors_caught(service) -> None:
    body = {"shown": [{"flight": "AA200", "class": "M"}], "open_wrong_caught": 1}
    shown, caught = answer(service, 200, body).wash([("AA100", "M"), ("AA200", "M")], 2)
    assert (shown, caught) == ([("AA200", "M")], 1)
