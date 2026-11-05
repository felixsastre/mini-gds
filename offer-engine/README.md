# offer-engine

When someone searches for a flight, the airline shows a few bundles, each one a fare with extras such as bags or a seat. This library chooses which ones to show. It guesses why the person is traveling, picks the best bundle for that kind of trip together with a decoy and a popular one, applies a discount that grows with what the customer spends, and learns over time which bundles sell.

Inspired by airline offer management. The data is invented, and so are the trip types and the bundles.

## About this project

This is an experiment, made for research and out of curiosity about how airline distribution works. It is not prepared for production use, and it should not be used with real bookings, fares or traffic.

## Words used here

- Bundle: a fare together with extras, shown to the traveler as an offer.
- Segment: the kind of trip, such as business, family, couple, leisure or one-way.
- Decoy: a bundle placed next to the best one so that the best one looks like better value. Here it costs the same or more than the best bundle and has the same or fewer extras.
- Bandit: a way to try several options at once and show more of the ones that sell, while still testing the others.

## An example

A traveler searches for a round trip booked 3 days ahead, alone, with a stay of 1 day. The library calls it a business trip. From a list of five bundles it shows three:

- the best for business travelers, Flex, at 260 with two extras;
- a decoy, Flex Max, at 300 with the same two extras;
- the popular one, Basic, at 200, which most people across all segments buy.

The discount follows a curve. With a maximum of 10 percent and a customer who spends 300, the discount is 7.50 percent, so a bundle priced at 300 is offered at 277.50.

## Status

All the scenarios in `features/` pass. The automated tests also try many random cases against the basic rules.

## Run

```
uv sync
uv run pytest
```
