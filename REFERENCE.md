# Technical reference

How to run the whole system. The [README](README.md) explains what the repository is.

## Run it

Needs [`uv`](https://docs.astral.sh/uv/), [`go`](https://go.dev/), the [Temporal CLI](https://docs.temporal.io/cli) (`brew install temporal`) and [`task`](https://taskfile.dev) (`brew install go-task`). From the root of the repository:

```
task up      # starts the whole mini GDS as local processes; Ctrl-C stops it
task test    # unit tests, lint and format check of every project
task e2e     # starts the system, runs the end-to-end tests (about two minutes) and stops it
task check   # test, then e2e
```

### Try it by hand

With `task up` running, in another terminal. The airline starts empty, so give it seats and the api a catalog first:

```
curl -X PUT localhost:18000/admin/flights/AA100/classes/K/seats -H 'content-type: application/json' -d '{"seats": 9}'
curl -X PUT localhost:18000/admin/flights/AA100/classes/M/seats -H 'content-type: application/json' -d '{"seats": 4}'

curl -X PUT localhost:18080/admin/catalog -H 'content-type: application/json' -d '{
  "flight": "AA100", "origin": "JFK", "destination": "LHR",
  "bundles": [
    {"name": "Basic", "booking_class": "K", "price": "200", "ancillaries": 0, "likelihood": {"business": "0.30", "leisure": "0.80"}, "overall": "0.60"},
    {"name": "Flex",  "booking_class": "M", "price": "260", "ancillaries": 2, "likelihood": {"business": "0.70", "leisure": "0.20"}, "overall": "0.40"}
  ]}'

# a business trip: Flex first, Basic as the popular offer
curl -X POST localhost:18080/search -H 'content-type: application/json' \
  -d '{"origin": "JFK", "destination": "LHR", "travelers": 1, "days_ahead": 3, "stay_days": 1}'

# reserve class M on AA100 (the answer has the reservation id), then pay within the hold
curl -X POST localhost:18080/reservations -H 'content-type: application/json' -d '{"flights": ["AA100"], "booking_class": "M"}'
curl -X POST localhost:18080/reservations/<id>/payment -H 'content-type: application/json' -d '{}'
```

The hold lasts 15 minutes unless `HOLD_SECONDS` says otherwise. See [`mini-gds`](mini-gds/) for the services, ports and endpoints.

## The `/admin` endpoints

The `host`, the `api` and the `cache` each have `/admin` endpoints. They set up the data (seats, the catalog, values and bid prices), make a class stop answering, and reset the state. The tests and the walkthrough above use them.

**They have no authentication.** They are served by the same app as the public endpoints, and anyone who can reach the port can change or erase the data. `task up` binds every service to `127.0.0.1`, which is the only protection: do not bind them to another address and do not expose them to a network.

## Known limits

- The `api` catalog is one route, replaced as a whole by each `PUT /admin/catalog`.
- Selling a connection does not check its market value again after the search.
- A Temporal unit test (`tests/unit/test_temporal_reservations.py`, `test_reservation_workflow.py`) failed in its setup in a few runs right after the lock file was rebuilt and could not be reproduced afterwards, so its cause is unknown. The end-to-end tests use real waits and take about two minutes.
