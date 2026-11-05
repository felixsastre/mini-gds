"""The airline host: the source of truth for seats left in each class."""

from decimal import Decimal
from threading import Lock

from fastapi import FastAPI, HTTPException, Response
from inventory_nesting import Inventory, Nesting, SaleRejectedError, availability_shown
from od_availability import Leg, is_open
from pydantic import BaseModel, Field

CAP = 9  # the most the host ever shows: "9" means 9 or more


class SeatsIn(BaseModel):
    seats: int = Field(ge=0)


class SaleIn(BaseModel):
    sale_id: str


class ValueIn(BaseModel):
    value: Decimal = Field(ge=0)  # market class fare value


class BidPriceIn(BaseModel):
    bid_price: Decimal = Field(ge=0)


class Flight:
    """The seats of one flight, kept as threshold-nesting authorizations and bookings.

    A sale has an id, so repeating a sale or a release changes nothing the second time.
    """

    def __init__(self) -> None:
        self._authorizations: dict[str, int] = {}
        self._bookings: dict[str, int] = {}
        self._sales: dict[str, str] = {}  # sale id -> booking class

    def set_seats(self, booking_class: str, seats: int) -> None:
        """Make the class show `seats`, whatever has been sold so far."""
        sold = sum(self._bookings.values())
        self._authorizations[booking_class] = seats + sold
        self._bookings.setdefault(booking_class, 0)

    def knows(self, booking_class: str) -> bool:
        return booking_class in self._authorizations

    def seats(self, booking_class: str) -> int:
        return availability_shown(
            self._inventory().availability(booking_class, Nesting.THRESHOLD), CAP
        )

    def sell(self, booking_class: str, sale_id: str) -> bool | None:
        """True for a new sale, None for a repeated one, False when it cannot be confirmed,
        which includes a sale id already used for another class."""
        if sale_id in self._sales:
            return None if self._sales[sale_id] == booking_class else False
        if not self.knows(booking_class):
            return False
        try:
            self._inventory().sell(booking_class, 1, Nesting.THRESHOLD)
        except SaleRejectedError:
            return False
        self._sales[sale_id] = booking_class
        self._bookings[booking_class] += 1
        return True

    def release(self, sale_id: str) -> None:
        booking_class = self._sales.pop(sale_id, None)
        if booking_class is not None:
            self._bookings[booking_class] -= 1

    def _inventory(self) -> Inventory:
        inventory = Inventory(self._authorizations)
        inventory.load_bookings(self._bookings)
        return inventory


class Airline:
    """The flights, plus what revenue management knows about connections.

    A connection is addressed by its flights joined with "+", as in "AA100+AA200". A class
    on a connection with a market value is open when every leg has a seat and the value
    minus the leg bid prices is above zero. Without a value it is judged on seats alone.
    """

    def __init__(self) -> None:
        self.flights: dict[str, Flight] = {}
        self._bid_prices: dict[str, Decimal] = {}
        self._values: dict[tuple[str, str], Decimal] = {}
        self._outages: set[tuple[str, str]] = set()

    def clear(self) -> None:
        self.flights.clear()
        self._bid_prices.clear()
        self._values.clear()
        self._outages.clear()

    def start_outage(self, itinerary: str, booking_class: str) -> None:
        """From now on the host cannot answer about this class (test setup)."""
        self._outages.add((itinerary, booking_class))

    def cannot_answer(self, itinerary: str, booking_class: str) -> bool:
        return (itinerary, booking_class) in self._outages

    def set_bid_price(self, flight: str, bid_price: Decimal) -> None:
        self._bid_prices[flight] = bid_price

    def set_value(self, itinerary: str, booking_class: str, value: Decimal) -> None:
        self._values[(itinerary, booking_class)] = value

    def seats(self, itinerary: str, booking_class: str) -> int | None:
        """Seats shown for the class, or None when a flight or class is unknown."""
        legs = itinerary.split("+")
        found = [self.flights.get(leg) for leg in legs]
        if any(flight is None or not flight.knows(booking_class) for flight in found):
            return None
        seats = [flight.seats(booking_class) for flight in found]
        value = self._values.get((itinerary, booking_class))
        if value is not None:
            priced = [
                Leg(self._bid_prices.get(leg, Decimal(0)), n)
                for leg, n in zip(legs, seats, strict=True)
            ]
            if not is_open(value, priced):
                return 0
        return min(seats)


def create_app() -> FastAPI:
    app = FastAPI(title="host")
    airline = Airline()
    flights = airline.flights
    lock = Lock()  # the endpoints run in threads and a sale must never oversell

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/flights/{flight}/classes/{booking_class}/seats")
    def seats(flight: str, booking_class: str) -> dict[str, int]:
        with lock:
            if airline.cannot_answer(flight, booking_class):
                raise HTTPException(status_code=503, detail="the host cannot answer")
            shown = airline.seats(flight, booking_class)
        if shown is None:
            raise HTTPException(status_code=404, detail="unknown flight or class")
        return {"seats": shown}

    @app.post("/flights/{flight}/classes/{booking_class}/sales")
    def sell(flight: str, booking_class: str, body: SaleIn, response: Response) -> dict[str, str]:
        with lock:
            found = flights.get(flight)
            outcome = found.sell(booking_class, body.sale_id) if found else False
        if outcome is False:
            raise HTTPException(status_code=409, detail="unable to confirm")
        response.status_code = 201 if outcome else 200
        return {"sale_id": body.sale_id}

    @app.delete("/flights/{flight}/sales/{sale_id}", status_code=204)
    def release(flight: str, sale_id: str) -> Response:
        with lock:
            found = flights.get(flight)
            if found is not None:
                found.release(sale_id)
        return Response(status_code=204)

    @app.put("/admin/flights/{flight}/classes/{booking_class}/seats", status_code=204)
    def set_seats(flight: str, booking_class: str, body: SeatsIn) -> Response:
        with lock:
            flights.setdefault(flight, Flight()).set_seats(booking_class, body.seats)
        return Response(status_code=204)

    @app.put("/admin/flights/{flight}/classes/{booking_class}/outage", status_code=204)
    def start_outage(flight: str, booking_class: str) -> Response:
        with lock:
            airline.start_outage(flight, booking_class)
        return Response(status_code=204)

    @app.put("/admin/flights/{flight}/bid-price", status_code=204)
    def set_bid_price(flight: str, body: BidPriceIn) -> Response:
        with lock:
            airline.set_bid_price(flight, body.bid_price)
        return Response(status_code=204)

    @app.put("/admin/itineraries/{itinerary}/classes/{booking_class}/value", status_code=204)
    def set_value(itinerary: str, booking_class: str, body: ValueIn) -> Response:
        with lock:
            airline.set_value(itinerary, booking_class, body.value)
        return Response(status_code=204)

    @app.post("/admin/reset", status_code=204)
    def reset() -> Response:
        with lock:
            airline.clear()
        return Response(status_code=204)

    return app


app = create_app()
