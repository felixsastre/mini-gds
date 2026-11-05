"""The gateway: catalog, search and, later, reservation."""

import os
from dataclasses import asdict, dataclass, field
from decimal import Decimal
from typing import Annotated

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from offer_engine import Bundle, segment_trip
from pydantic import BaseModel, Field
from temporalio.client import Client

from mini_gds.cache_client import AvailabilityCache, CacheUnavailableError, HttpCache
from mini_gds.reservations import (
    HoldClosedError,
    ReservationNotFoundError,
    Reservations,
    ReservationsUnavailableError,
    TemporalReservations,
)
from mini_gds.search import Listing, search
from mini_gds.workflows import TASK_QUEUE


class BundleIn(BaseModel):
    name: str
    booking_class: str
    price: Decimal
    ancillaries: int
    likelihood: dict[str, Decimal]  # chance of purchase by segment
    overall: Decimal


class CatalogIn(BaseModel):
    flight: str
    origin: str
    destination: str
    bundles: list[BundleIn]


class ReserveIn(BaseModel):
    # One flight number per leg, in travel order: 2 capital letters or digits, then the number.
    flights: list[Annotated[str, Field(pattern=r"^[A-Z0-9]{2}[0-9]{1,4}$")]] = Field(
        min_length=1, max_length=12
    )
    booking_class: str = Field(pattern=r"^[A-Z]$")  # one letter, as in K, M or Y
    passenger: str = Field("Passenger", min_length=1)


class PaymentIn(BaseModel):
    decline: bool = False  # simulates a declined payment


class SearchIn(BaseModel):
    origin: str
    destination: str
    travelers: int = Field(ge=1)
    days_ahead: int = Field(ge=0)
    stay_days: int | None = Field(None, ge=0)  # None for a one-way trip


@dataclass
class Catalog:
    route: tuple[str, str] | None = None
    listings: list[Listing] = field(default_factory=list)


def create_app(
    cache: AvailabilityCache, wash_top: int = 2, reservations: Reservations | None = None
) -> FastAPI:
    app = FastAPI(title="api")
    catalog = Catalog()

    @app.exception_handler(ReservationsUnavailableError)
    async def reservations_unavailable(_: Request, __: Exception) -> JSONResponse:
        return JSONResponse({"detail": "reservations are unavailable"}, status_code=503)

    @app.exception_handler(CacheUnavailableError)
    async def cache_unavailable(_: Request, __: Exception) -> JSONResponse:
        return JSONResponse({"detail": "availability is unavailable"}, status_code=503)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.put("/admin/catalog", status_code=204)
    def put_catalog(body: CatalogIn) -> Response:
        catalog.route = (body.origin, body.destination)
        catalog.listings = [
            Listing(
                body.flight,
                item.booking_class,
                Bundle(
                    item.name,
                    item.price,
                    item.ancillaries,
                    item.likelihood,
                    item.overall,
                ),
            )
            for item in body.bundles
        ]
        return Response(status_code=204)

    @app.post("/search")
    def post_search(body: SearchIn) -> dict:
        segment = segment_trip(body.days_ahead, body.stay_days, body.travelers)
        on_route = catalog.route == (body.origin, body.destination)
        result = search(catalog.listings if on_route else [], segment, cache, wash_top)
        return {
            "segment": segment.value,
            "offers": [asdict(offer) for offer in result.offers],
            "open_wrong_caught": result.open_wrong_caught,
            "host_unavailable": result.host_unavailable,
        }

    def reservations_or_503() -> Reservations:
        if reservations is None:
            raise HTTPException(status_code=503, detail="reservations are not configured")
        return reservations

    @app.post("/reservations")
    async def post_reservation(body: ReserveIn) -> JSONResponse:
        reservation_id, view = await reservations_or_503().reserve(
            body.flights, body.booking_class, body.passenger
        )
        if view.gds_locator is None:  # the airline could not confirm: no booking exists
            return JSONResponse(asdict(view), status_code=409)
        return JSONResponse({"id": reservation_id, **asdict(view)}, status_code=201)

    @app.post("/reservations/{reservation_id}/payment")
    async def post_payment(reservation_id: str, body: PaymentIn) -> dict:
        try:
            view = await reservations_or_503().pay(reservation_id, body.decline)
        except HoldClosedError:
            raise HTTPException(status_code=409, detail="the hold is not open") from None
        except ReservationNotFoundError:
            raise HTTPException(status_code=404, detail="unknown reservation") from None
        return asdict(view)

    @app.get("/reservations/{reservation_id}")
    async def get_reservation(reservation_id: str) -> dict:
        try:
            return asdict(await reservations_or_503().get(reservation_id))
        except ReservationNotFoundError:
            raise HTTPException(status_code=404, detail="unknown reservation") from None

    return app


def app_from_environment() -> FastAPI:
    address = os.environ["TEMPORAL_ADDRESS"]
    reservations = TemporalReservations(
        lambda: Client.connect(address),
        TASK_QUEUE,
        hold_seconds=int(os.environ.get("HOLD_SECONDS", "900")),
    )
    cache = HttpCache(os.environ["CACHE_URL"])
    return create_app(cache, int(os.environ.get("WASH_TOP", "2")), reservations)
