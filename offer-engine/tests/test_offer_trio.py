from decimal import Decimal

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from offer_engine import Bundle, Offers, build_offers

scenarios("offer_trio.feature")


@given("these bundles:", target_fixture="bundles")
def _bundles(datatable: list[list[str]]) -> list[Bundle]:
    header, *rows = datatable
    segments = header[3:-1]
    return [
        Bundle(
            name=row[0],
            price=Decimal(row[1]),
            ancillaries=int(row[2]),
            likelihood={s: Decimal(v) for s, v in zip(segments, row[3:-1], strict=True)},
            overall=Decimal(row[-1]),
        )
        for row in rows
    ]


@when(parsers.parse("offers are built for the {segment} segment"), target_fixture="offers")
def _offers(bundles: list[Bundle], segment: str) -> Offers:
    return build_offers(bundles, segment)


@then(parsers.parse("the best offer is {name}"))
def _best(offers: Offers, name: str) -> None:
    assert offers.best.name == name


@then(parsers.parse("the decoy offer is {name}"))
def _decoy(offers: Offers, name: str) -> None:
    assert offers.decoy is not None
    assert offers.decoy.name == name


@then("there is no decoy offer")
def _no_decoy(offers: Offers) -> None:
    assert offers.decoy is None


@then(parsers.parse("the popular offer is {name}"))
def _popular(offers: Offers, name: str) -> None:
    assert offers.popular is not None
    assert offers.popular.name == name


def _bundle(name: str) -> Bundle:
    return Bundle(name, Decimal(100), 1, {"leisure": Decimal("0.5")}, Decimal("0.5"))


def test_offers_need_at_least_one_bundle() -> None:
    with pytest.raises(ValueError):
        build_offers([], "leisure")


def test_bundle_names_must_be_unique() -> None:
    with pytest.raises(ValueError):
        build_offers([_bundle("Basic"), _bundle("Basic")], "leisure")
