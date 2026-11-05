"""Search: offers for the classes that can be sold, checked against the airline."""

from dataclasses import dataclass, replace

from offer_engine import Bundle, Segment, build_offers

from mini_gds.cache_client import AvailabilityCache, HostUnavailableError


@dataclass(frozen=True)
class Listing:
    """A bundle on sale on a flight, in one booking class."""

    flight: str
    booking_class: str
    bundle: Bundle


@dataclass(frozen=True)
class Offer:
    role: str
    bundle: str
    booking_class: str
    price: str


@dataclass(frozen=True)
class SearchResult:
    offers: list[Offer]
    open_wrong_caught: int
    host_unavailable: int  # classes left out because the airline could not answer


def search(
    listings: list[Listing], segment: Segment, cache: AvailabilityCache, wash_top: int
) -> SearchResult:
    open_listings = []
    host_unavailable = 0
    for item in listings:
        try:
            if cache.seats(item.flight, item.booking_class) > 0:
                open_listings.append(item)
        except HostUnavailableError:  # neither open nor closed: left out, and counted
            host_unavailable += 1
    if not open_listings:
        return SearchResult([], 0, host_unavailable)

    # offer-engine needs unique names, but two listings can share a bundle name: it sees
    # the position of the listing instead, and the offer takes the name from the listing.
    listing_of = {str(position): item for position, item in enumerate(open_listings)}
    built = build_offers(
        [replace(item.bundle, name=key) for key, item in listing_of.items()], segment.value
    )
    roles = [("best", built.best), ("decoy", built.decoy), ("popular", built.popular)]
    ordered = [(role, listing_of[b.name]) for role, b in roles if b is not None]

    keys = [(item.flight, item.booking_class) for _, item in ordered]
    shown_keys, caught = cache.wash(keys, wash_top)
    offers = [
        Offer(role, item.bundle.name, item.booking_class, str(item.bundle.price))
        for role, item in ordered
        if (item.flight, item.booking_class) in shown_keys
    ]
    return SearchResult(offers, caught, host_unavailable)
