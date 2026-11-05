# od-availability

Many trips use more than one flight, and the same seat on one flight can be part of several different trips. An airline therefore decides whether to keep a price level open by looking at the whole trip, with all its flights together. This library makes that decision: a class is open when every flight of the trip has seats left and the trip is worth more than its seats cost the airline.

Inspired by airline revenue management. The data is invented, and this is not a real reservation system.

## About this project

This is an experiment, made for research and out of curiosity about how airline distribution works. It is not prepared for production use, and it should not be used with real bookings, fares or traffic.

## Words used here

- Origin and destination (O&D): the whole trip a passenger buys, from where it starts to where it ends.
- Leg: one flight of the trip.
- Fare value: what the passenger pays for the whole trip.
- Bid price: the least the airline wants to earn from one seat on one leg.
- Net contribution: the fare value minus the bid prices of all the legs. If it is above zero, the trip is worth selling.

## An example

A trip has two legs with bid prices of 300 and 700, and both legs have seats left.

- At a fare value of 1200, the net contribution is 1200 minus 1000, which is 200. The class is open.
- At a fare value of 600 and bid prices of 300 and 350, the net contribution is minus 50. The class is closed.
- At a fare value of 1050 the trip is worth selling, but if one of the legs has no seats left the class is closed anyway.

## Status

All the scenarios in `features/` pass. The automated tests also try many random cases against the basic rules.

## Run

```
uv sync
uv run pytest
```
