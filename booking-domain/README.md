# booking-domain

The model of a booking in airline distribution. It covers the difference between a reservation and a ticket, the codes that one trip has in different systems, the status of each flight, which airline sells, flies and issues each flight, tickets for long trips, and receipts for extras.

Inspired by airline distribution. The data is invented, this is not a real reservation system, and the set of flight statuses is simplified.

## About this project

This is an experiment, made for research and out of curiosity about how airline distribution works. It is not prepared for production use, and it should not be used with real bookings, fares or traffic.

## Words used here

- Reservation (or booking): seats held for a passenger. It can exist without a ticket.
- Ticket: the paid document. Its number has 3 digits for the airline and 10 for the document.
- Segment: one flight of the trip.
- Locator: the code of a booking in one system. The distribution system and the airline each have their own.
- Status: whether the airline holds the seat. HK is confirmed, HL is on the waiting list, UC is unable to confirm and XX is cancelled.
- Marketing, operating and validating carrier: the airline whose code is sold, the airline that flies the plane and the airline that issues the ticket. They can be three different companies.
- Conjunction ticket: several tickets issued together for a long trip, because one ticket holds at most 4 flights.
- EMD: Electronic Miscellaneous Document, a receipt for extras such as bags and seats.

## An example

A trip has 6 flights to ticket. One ticket holds at most 4, so two tickets are issued, with 4 and 2 flights, numbered 125-1234567890 and 125-1234567891.

A flight can be sold by AA and flown by IB, a codeshare. Then AA is the marketing carrier and IB is the operating carrier. If AA issues the ticket, AA is also the validating carrier.

## Status

All the scenarios in `features/` pass. The automated tests also try many random cases against the basic rules.

## Run

```
uv sync
uv run pytest
```
