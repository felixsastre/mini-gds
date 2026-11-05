import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

MEAN_TOLERANCE = 1e-9  # float rounding can leave a mean a hair outside 0 to 1


@dataclass(frozen=True)
class Arm:
    name: str
    pulls: int
    mean: float

    def __post_init__(self) -> None:
        if self.pulls < 0:
            raise ValueError(f"an arm cannot have {self.pulls} pulls")
        if not -MEAN_TOLERANCE <= self.mean <= 1 + MEAN_TOLERANCE:  # also false for NaN
            raise ValueError(f"the mean reward of an arm is between 0 and 1, not {self.mean}")


def _require_arms(arms: Sequence[Arm]) -> None:
    if not arms:
        raise ValueError("choosing needs at least one arm")


def _best_mean(arms: Sequence[Arm]) -> Arm:
    return max(arms, key=lambda arm: arm.mean)


def epsilon_greedy(arms: Sequence[Arm], epsilon: float, draw: float, explore_index: int) -> Arm:
    """Explore arms[explore_index] when draw < epsilon, otherwise the highest mean.

    Raise ValueError for no arms, an epsilon or draw outside 0 to 1, or an explore index
    outside the arms.
    """
    _require_arms(arms)
    if not (0 <= epsilon <= 1 and 0 <= draw <= 1):
        raise ValueError(f"epsilon and the draw are between 0 and 1, not {epsilon} and {draw}")
    if not 0 <= explore_index < len(arms):
        raise ValueError(f"explore index {explore_index} is outside the {len(arms)} arms")
    return arms[explore_index] if draw < epsilon else _best_mean(arms)


def ucb(arms: Sequence[Arm]) -> Arm:
    """UCB1: an untried arm first, then the highest mean + sqrt(2 ln(total) / pulls)."""
    _require_arms(arms)
    untried = next((arm for arm in arms if arm.pulls == 0), None)
    if untried is not None:
        return untried
    total = sum(arm.pulls for arm in arms)
    return max(arms, key=lambda arm: arm.mean + math.sqrt(2 * math.log(total) / arm.pulls))


def thompson(arms: Sequence[Arm], samples: Mapping[str, float]) -> Arm:
    """The arm with the highest sample; ValueError for no arms or an arm with no sample."""
    _require_arms(arms)
    missing = [arm.name for arm in arms if arm.name not in samples]
    if missing:
        raise ValueError(f"no sample for arm {', '.join(missing)}")
    return max(arms, key=lambda arm: samples[arm.name])


def update(arm: Arm, reward: float) -> Arm:
    """The arm after one more pull; raise ValueError unless the reward is 0 or 1."""
    if reward not in (0, 1):
        raise ValueError(f"a reward is 0 or 1, not {reward}")
    pulls = arm.pulls + 1
    mean = (arm.mean * arm.pulls + reward) / pulls
    return replace(arm, pulls=pulls, mean=min(1.0, max(0.0, mean)))


def cumulative_regret(true_means: Mapping[str, float], chosen: Sequence[str]) -> float:
    """What the choices gave up against the best arm; ValueError for no arms or an unknown one."""
    if not true_means:
        raise ValueError("regret needs the true mean of at least one arm")
    unknown = [name for name in chosen if name not in true_means]
    if unknown:
        raise ValueError(f"no true mean for arm {', '.join(unknown)}")
    best = max(true_means.values())
    return sum(best - true_means[name] for name in chosen)
