# availability-cache

A distributor, such as a travel agency system, does not ask the airline every time someone searches for a flight. It keeps a copy of how many seats are left in each class and trusts that copy for a short time. This library models that copy: how entries expire, how the airline updates them, and the checks that find where the copy disagrees with the airline.

Inspired by airline distribution. The data is invented, and this is not a real distribution system.

> [!IMPORTANT]
> This is a proof of concept, made for research and out of curiosity about how airline
> distribution works. It is not prepared for production use, and it should not be used
> with real bookings, fares or traffic.

## Words used here

- Distributor: a company that sells the airline's seats, such as a travel agency system.
- Host: the airline's own system. It always holds the true number of seats.
- Time to live: how long a stored answer is trusted before it has to be checked again.
- Open-wrong error: the copy shows a seat as available but the host can no longer sell it.
- Closed-wrong error: the copy hides a seat that the host could sell.

## An example

The copy has a time to live of 60 seconds and holds 4 seats for class M on flight AA100, stored 30 seconds ago. A search asks for it. The copy answers 4 without asking the host, even if the host now has 0.

If the entry was stored 60 seconds ago, it has expired. The copy asks the host, gets 0 and stores that. An update that the airline sends on its own replaces the entry and starts its time over.

Before showing the best results, the system can check them against the host. If the copy says a class is open on three flights and the host has it closed on one, that one is removed and counted as an open-wrong error.

## Status

All the scenarios in `features/` pass. The automated tests also try many random cases, and one test uses the cache from several threads at once.

## Run

```
go test -race ./...
```
