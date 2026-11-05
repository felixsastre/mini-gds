from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Bundle:
    name: str
    price: Decimal
    ancillaries: int
    likelihood: Mapping[str, Decimal]  # chance of purchase by segment name
    overall: Decimal  # share of all sales


@dataclass(frozen=True)
class Offers:
    best: Bundle
    decoy: Bundle | None
    popular: Bundle | None


def build_offers(bundles: Sequence[Bundle], segment: str) -> Offers:
    """Best for the segment, a decoy dominated by it, and the most popular other bundle.

    A bundle with no likelihood for the segment counts with its overall share.
    Raise ValueError for no bundles or two bundles with the same name.
    """
    if not bundles:
        raise ValueError("at least one bundle is needed to build offers")
    if len({bundle.name for bundle in bundles}) != len(bundles):
        raise ValueError("bundle names must be unique")
    best = max(bundles, key=lambda bundle: bundle.likelihood.get(segment, bundle.overall))
    dominated = [
        bundle
        for bundle in bundles
        if bundle.name != best.name
        and bundle.price >= best.price
        and bundle.ancillaries <= best.ancillaries
    ]
    decoy = min(dominated, key=lambda bundle: bundle.price, default=None)
    shown = {best.name} | ({decoy.name} if decoy else set())
    others = sorted(bundles, key=lambda bundle: bundle.overall, reverse=True)
    popular = next((bundle for bundle in others if bundle.name not in shown), None)
    return Offers(best, decoy, popular)
