# inventory-nesting

An airline sells the seats of a flight cabin at several price levels, called booking classes. It cannot let every class sell every seat, so it gives each class a sales limit and ranks the classes from the highest fare down. This library works out how many seats each class can still sell, and which number to send to the distributors that sell on the airline's behalf.

Inspired by airline revenue management. The data is invented, and this is not a real reservation system.

> [!IMPORTANT]
> This is a proof of concept, made for research and out of curiosity about how airline
> distribution works. It is not prepared for production use, and it should not be used
> with real bookings, fares or traffic.

## Words used here

- Booking class: a letter such as Y, B or M that marks one price level of the same seat.
- Authorization: the most seats a class is allowed to sell. The authorizations of all classes can add up to more than the seats the cabin has.
- Nesting: the way the limits of the classes overlap. The library supports two ways of counting, called threshold and net.
- Distributor: a company that sells the airline's seats, such as a travel agency system.

## An example

A cabin has 300 seats. Class M has an authorization of 320, and 255 seats have been sold in the whole cabin. With threshold nesting, class M can still sell 320 minus 255, which is 65 seats.

The airline then decides the highest number it will show a distributor, say 9. If a class has 12 seats available, the distributor is told 9, and a shown 9 means "9 or more". If the number is negative, the distributor is told 0.

## Status

All the scenarios in `features/` pass. The automated tests also try many random cases against the basic rules.

## Run

```
uv sync
uv run pytest
```

For how to use it from code, see [`REFERENCE.md`](REFERENCE.md).
