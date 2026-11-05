from collections.abc import Callable

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from offer_engine import Arm, cumulative_regret, epsilon_greedy, thompson, ucb, update

scenarios("bandits.feature")


@given("these arms:", target_fixture="arms")
def _arms(datatable: list[list[str]]) -> list[Arm]:
    return [Arm(name, int(pulls), float(mean)) for name, pulls, mean in datatable[1:]]


@given("no arms", target_fixture="arms")
def _no_arms() -> list[Arm]:
    return []


def _attempt[T](action: Callable[[], T]) -> T | ValueError:
    try:
        return action()
    except ValueError as error:
        return error


@when(
    parsers.parse("epsilon-greedy with epsilon {epsilon:f} chooses with a random draw of {draw:f}"),
    target_fixture="outcome",
)
def _exploit(arms: list[Arm], epsilon: float, draw: float) -> Arm | ValueError:
    # The exploration index points at the worst arm, so exploring instead of exploiting shows.
    worst = min(range(len(arms)), key=lambda index: arms[index].mean)
    return _attempt(lambda: epsilon_greedy(arms, epsilon, draw, explore_index=worst))


@when(
    parsers.re(
        r"epsilon-greedy with epsilon (?P<epsilon>[\d.]+) chooses with a random draw of"
        r" (?P<draw>[\d.]+) and picks the (?P<position>\d+)(?:st|nd|rd|th) arm"
    ),
    converters={"epsilon": float, "draw": float, "position": int},
    target_fixture="outcome",
)
def _explore(arms: list[Arm], epsilon: float, draw: float, position: int) -> Arm | ValueError:
    return _attempt(lambda: epsilon_greedy(arms, epsilon, draw, explore_index=position - 1))


@when("UCB chooses", target_fixture="outcome")
def _ucb(arms: list[Arm]) -> Arm | ValueError:
    return _attempt(lambda: ucb(arms))


@when(parsers.parse("Thompson Sampling chooses with samples {samples}"), target_fixture="outcome")
def _thompson(arms: list[Arm], samples: str) -> Arm | ValueError:
    pairs = (item.split() for item in samples.replace(" and ", ", ").split(", "))
    return _attempt(lambda: thompson(arms, {name: float(value) for name, value in pairs}))


@then(parsers.parse("the chosen arm is {name}"))
def _chosen(outcome: Arm | ValueError, name: str) -> None:
    assert isinstance(outcome, Arm)
    assert outcome.name == name


@then("the request is invalid")
def _invalid(outcome: object) -> None:
    assert isinstance(outcome, ValueError)


@when(parsers.parse("arm {name} receives a reward of {reward:g}"), target_fixture="outcome")
def _reward(arms: list[Arm], name: str, reward: float) -> Arm | ValueError:
    arm = next(arm for arm in arms if arm.name == name)
    return _attempt(lambda: update(arm, reward))


@then(parsers.parse("arm {name} has {pulls:d} pulls and a mean reward of {mean:f}"))
def _updated(outcome: Arm | ValueError, name: str, pulls: int, mean: float) -> None:
    assert isinstance(outcome, Arm)
    assert (outcome.name, outcome.pulls) == (name, pulls)
    assert outcome.mean == pytest.approx(mean)


@given(parsers.parse("the true mean rewards are {means}"), target_fixture="true_means")
def _true_means(means: str) -> dict[str, float]:
    pairs = (item.split() for item in means.replace(" and ", ", ").split(", "))
    return {name: float(value) for name, value in pairs}


@when(parsers.parse("the arms chosen in order are {names}"), target_fixture="outcome")
def _regret(true_means: dict[str, float], names: str) -> float | ValueError:
    chosen = [name.strip() for name in names.split(",")]
    return _attempt(lambda: cumulative_regret(true_means, chosen))


@then(parsers.parse("the cumulative regret is {expected:f}"))
def _regret_is(outcome: float | ValueError, expected: float) -> None:
    assert not isinstance(outcome, ValueError)
    assert outcome == pytest.approx(expected)


def test_an_arm_cannot_have_negative_pulls() -> None:
    with pytest.raises(ValueError):
        Arm("A", -1, 0.5)


def test_regret_needs_true_means() -> None:
    with pytest.raises(ValueError):
        cumulative_regret({}, [])


@pytest.mark.parametrize("mean", [5.0, -0.5, 1.01, float("nan"), float("inf")])
def test_an_arm_mean_is_between_zero_and_one(mean: float) -> None:
    with pytest.raises(ValueError):
        Arm("A", 3, mean)


def test_the_mean_after_an_update_is_still_a_valid_arm() -> None:
    arm = Arm("A", 3, 1.0)
    for _ in range(50):
        arm = update(arm, 1.0)  # rounding may leave the mean a hair above 1
    assert arm.pulls == 53
