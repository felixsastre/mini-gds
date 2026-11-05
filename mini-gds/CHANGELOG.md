# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/). Edits to a `.feature` go under **Changed**, with the reason.

## [Unreleased]

### Added
- Behavior specs: `features/search.feature` and `features/reservation.feature`.
- `host` service: seats per flight and class on top of `inventory-nesting`, capped at 9.
- `cache` service (Go): availability with time to live, updates from the airline and wash of the top offers, on top of `availability-cache`. A host that cannot answer is reported as unavailable (see Changed).
- `api` service: `PUT /admin/catalog` and `POST /search`, with offers from `offer-engine` for the classes that can be sold and a wash of the top 2 against the airline.
- Dependencies: `fastapi`, `uvicorn`, `httpx2`.
- Reservation: `POST /reservations`, `POST /reservations/{id}/payment` and `GET /reservations/{id}`. Each reservation is a Temporal workflow that sells a seat, holds it for `HOLD_SECONDS` (900 by default), and issues a ticket on payment. An expired hold or a declined payment cancels the segment and returns the seat. A seat the airline cannot confirm creates no booking.
- `host`: sales and releases by sale id, atomic and idempotent, so a retried step never sells twice.
- `worker` service: runs the reservation workflows on a Temporal server.
- Dependencies: `temporalio`, `booking-domain` (by path).
- Behavior specs: `features/connection_search.feature` and `features/connection_reservation.feature`.
- Connections: the host addresses them as flights joined with `+` and judges each class with `od-availability` (market value per class, bid price per leg); a class is open with a seat on every leg and a positive net contribution. New `/admin` endpoints set the values and bid prices. Dependency: `od-availability` (by path).
- Reserving a connection sells one seat per leg and creates one booking with a segment per leg. If a later leg cannot be confirmed, the earlier legs are given back.
- `host`: `PUT /admin/flights/{flight}/classes/{class}/outage` makes a class stop answering with 503 until `/admin/reset`, for test setup.

### Changed
- `features/connection_reservation.feature`: two assumptions (conjunction tickets with consecutive numbers for more than 4 flights; the validating carrier is the carrier of the first flight) and a scenario for five flights. Reason: a code review found the booking view showed only the first ticket of a long itinerary.
- The booking in `/reservations` responses has `tickets`, every ticket number in order; `ticket` stays as the first one.
- `features/search.feature`: an assumption and a scenario for a class the airline cannot answer about. Reason: a code review found a host outage showed every class as closed, so the search returned no offers and no signal.
- `cache`: `/availability` answers 503 when the host cannot answer, instead of 200 with 0 seats. `POST /search` leaves that class out and reports how many in `host_unavailable`, apart from the open-wrong errors caught.
- `features/search.feature`: an assumption and a scenario for a kind of trip the airline has no data for. Reason: a code review found the catalog filled it with 0, so the first bundle won.
- `POST /reservations` takes `flights` (a list, one per leg) instead of `flight`, and the booking reports `segment_statuses` (a list) instead of `segment_status`.

### Fixed
- `POST /reservations` rejects a booking class that is not one capital letter with 422; it went unchecked into the host's URL.
- `cache`: a host that answers 404 for a class it does not sell now means zero seats, instead of an error that `/search` counted as the airline not answering. Other failures stay errors.
- The end-to-end steps for paying fail on a bad answer and check that `ticket` is the first of `tickets`.
- `scripts/dev.sh` stops the worker loop first, then every process below each job, and kills what ignores the signal, so no worker is left running after Ctrl-C. A worker that could not reach Temporal used to survive.
- `host`: `PUT /admin/itineraries/.../value` rejects a negative market value with 422, which `od-availability` now refuses.
- Reservation: a flight number that is not 2 capital letters or digits followed by 1 to 4 digits, or an empty passenger name, is rejected with 422. Before, the airline sold the seat and the booking then refused the flight, so the workflow failed and retried forever with the seat sold. The workflow also gives the seats back if the booking or its tickets are refused after the sale.
- `POST /search` rejects fewer than 1 traveler or negative days with 422, where it answered 500.
- `api` answers 503 when the availability cache cannot be reached or fails, and `/reservations` answers 503 when Temporal cannot be reached, where both answered 500. A Temporal error while paying is no longer reported as a closed hold (409).
- Dependencies: `offer-engine`, `booking-domain`, `inventory-nesting` and `od-availability` are editable path dependencies. They were copied into the virtual environment, so the tests ran against old code.
- Search: a segment the catalog has no likelihood for (couple, one-way) is offered by overall sales, as `offer-engine` does, instead of every bundle counting as 0.
- Reservation: an itinerary of 5 to 12 legs is ticketed with conjunction tickets after the payment. Before, `issue_ticket` failed and Temporal retried it forever, with the card charged and the seats held. `POST /reservations` rejects more than 12 flights with 422.
- Reservation: a payment only starts while the hold is open, checked again in the update itself, and an expired hold is only cancelled if no payment has started. Two payments delivered together can no longer both pass.
- Reservation: a host that fails while selling a leg (not only one that refuses) now gives back every earlier leg, and the leg whose answer never arrived too, instead of leaving them sold.
- Reservation: a payment can no longer start while an expired hold is being cancelled, so a customer is not charged for a cancelled booking.
- Reservation: a ticket that cannot be issued after the payment cancels the booking and gives the seats back, instead of leaving the reservation stuck as paying.
- Reservation: the workflow ends only after its updates have answered, and `reserve` falls back to the workflow result, so a refused sale answers 409 instead of 500.
- `api`: `POST /reservations` rejects an empty `flights` list with 422; `/reservations` answers 503 when Temporal does not respond, and `GET /reservations/{id}` no longer answers 404 for that case.
- Search: listings that share a bundle name keep their own flight, class and price.
- `host`: a sale id reused for another class is refused (409) instead of reported as sold.
- `host`: `/admin` refuses negative seats and negative bid prices with 422, since `od-availability` now rejects such legs.
- `cache`: a host that cannot answer shows the class as closed only for that request; before, the answer was stored as closed for the whole time to live. `/wash` keeps an offer the host could not answer about instead of dropping it.
