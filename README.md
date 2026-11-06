# travel-projects

A miniature airline distribution system, built from small pieces as a portfolio. Airline distribution is the business of putting an airline's seats in front of travel agencies and travelers: someone searches for a flight, sees offers with prices, books a seat and pays. This repository models the main parts of that chain. Each part is a small project that can be understood and tested on its own, and one more project runs them all together.

Everything uses invented data. It is not a real reservation system and it does not connect to real airline systems.

## About this project

Every project in this repository is an experiment, made for research and out of curiosity about how airline distribution works. None of them is prepared for production use, and none should be used with real bookings, fares or traffic.

## How each project is built

Each project starts from a description of its behavior written in plain English, in the files of its `features/` folder. A person reads and approves that description before any code is written, and the same description then runs as the automated tests. The projects are written in Python and in Go.

## Words used here

- GDS: Global Distribution System, a network that connects airlines with travel agencies.
- Distributor: a company that sells an airline's seats on its behalf, such as a travel agency system or a GDS.
- Booking class: a letter such as Y, B or M that marks one price level of the same seat.
- Bundle: a fare together with extras such as bags or a seat, shown to the traveler as an offer.

## The projects

| Project | Built with | What it covers |
| --- | --- | --- |
| [`inventory-nesting`](inventory-nesting/) | Python | How many seats each price level of a cabin can still sell, and which number the distributors are told |
| [`od-availability`](od-availability/) | Python | Whether to keep a price level open for a whole trip with connections, looking at all its flights together |
| [`availability-cache`](availability-cache/) | Go | The copy of seat availability that a distributor keeps, how it expires and how to find where it is wrong |
| [`offer-engine`](offer-engine/) | Python | Which bundles to show a traveler, how a discount grows with spending and how the system learns what sells |
| [`booking-domain`](booking-domain/) | Python | What a booking, a ticket and a receipt for extras are, and how the status of each flight is tracked |
| [`mini-gds`](mini-gds/) | Python, Go | All of the above running together: search, offers, reservation and payment |

## License

[MIT](LICENSE).

## Running it

Running the whole system needs a few tools installed. [`REFERENCE.md`](REFERENCE.md) lists them, gives the commands and has a walkthrough with example requests.
