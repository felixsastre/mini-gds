# Technical reference

Services, ports and how to run the system. The [README](README.md) explains what it does.

## Services

| Service    | Port  | What it does                                                          |
| ---------- | ----- | --------------------------------------------------------------------- |
| `host`     | 18000 | The airline: seats per class, built on `inventory-nesting` and `od-availability`            |
| `cache`    | 18081 | The distributor's copy of availability, built on `availability-cache` |
| `api`      | 18080 | Search with offers from `offer-engine`, and reservations              |
| `worker`   | none  | Runs the reservation workflows (`booking-domain`)                     |
| `temporal` | 18233 | Temporal development server; the port is its web UI                   |

Ports are published on `127.0.0.1` only.

## Run

Needs `uv`, `go` and the Temporal CLI (`brew install temporal`):

```
HOLD_SECONDS=30 ./scripts/dev.sh                 # starts the five processes; Ctrl-C stops them
HOLD_SECONDS=30 uv run pytest tests/e2e          # in another terminal
```

`./scripts/e2e.sh` does both in one go, and from the root of the repository `task up` and `task e2e` run the two scripts (see the root README for a walkthrough with `curl`).

The hold is 15 minutes by default (`HOLD_SECONDS=900`). The end-to-end run uses 30 seconds, so one minute of the feature lasts two seconds. Payment and ticketing are simulated.

Unit tests need no running system: `uv run pytest` and `cd cache && go test -race ./...`.
