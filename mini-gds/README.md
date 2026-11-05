# mini-gds

The other projects of this repository running together as one small system. A traveler searches for a flight. The answer comes from the airline's own system, through the distributor's copy of availability, with offers chosen by the offer engine. The traveler then reserves a seat, pays within a time limit and gets a ticket. Payment and ticketing are simulated, and the data is invented.

## About this project

This is an experiment, made for research and out of curiosity about how airline distribution works. It is not prepared for production use, and it should not be used with real bookings, fares or traffic.

## Words used here

- Host: the airline's own system. It holds the true number of seats.
- Distributor: a company that sells the airline's seats on its behalf.
- Hold: the time a reserved seat waits for payment. It lasts 15 minutes unless it is set otherwise.
- Workflow: a process that remembers where it is. Each reservation is one.

## What happens

1. The traveler searches for a flight between two cities.
2. The system asks the distributor's copy of availability and, when the copy is not enough, the airline host.
3. The offer engine chooses the bundles to show.
4. The traveler reserves one. The seat is held while the system waits for the payment.
5. If the traveler pays in time, a ticket is issued. If the hold runs out or the payment is declined, the seat goes back to the airline.

It works for single flights and for connections. On a connection, a class can be closed even with seats left, because the trip is not worth what those seats cost on its flights.

## Status

Search and reservation work from start to finish, on single flights and on connections. A hold survives a restart of the program that runs the reservations.

## Run

The services, their ports and the commands are in [`REFERENCE.md`](REFERENCE.md). From the root of the repository, `task up` starts the system.
