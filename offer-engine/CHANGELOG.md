# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/). Edits to a `.feature` go under **Changed**, with the reason.

## [Unreleased]

### Added
- Behavior specs: `features/trip_purpose.feature`, `features/offer_trio.feature`, `features/dynamic_discount.feature` and `features/bandits.feature`.
- `segment_trip`: one segment per trip (business, family, couple, leisure, one-way).
- `build_offers`: best bundle for the segment, a decoy dominated by it, and the most popular other bundle.
- `discount_percent` and `discounted_price`: Michaelis-Menten discount curve.
- `epsilon_greedy`, `ucb`, `thompson`, `update` and `cumulative_regret`: bandit choices, learning and regret.

### Changed
- `features/bandits.feature`: an assumption and scenarios for an impossible epsilon or draw, a reward other than 0 or 1, a missing Thompson sample and a missing true mean. Reason: a code review found these raised `KeyError`, or were accepted and gave a wrong mean.
- `features/dynamic_discount.feature`: the discount is rounded down, not half up, so it never reaches the maximum, and impossible inputs are invalid. Reason: a code review found a spend of 2000000 gave 10.00, the maximum.
- `features/trip_purpose.feature`, `features/offer_trio.feature` and `features/bandits.feature`: an assumption and scenarios for impossible trips, a segment with no data (falls back to overall sales), and choosing with no arms or an arm that does not exist. Reason: a code review found these raised the wrong error or silently gave a result.
- Build backend `uv_build` 0.13 and Python 3.15 (`.python-version`); dependencies re-resolved to the latest releases.

### Fixed
- `discount_percent` rounds down and raises `ValueError` for a negative spend, a maximum outside 0 to 100 or a constant of 0 or less. Before, it reached the maximum at a large spend, raised `InvalidOperation` for a zero constant, and a negative spend gave a surcharge. `discounted_price` rejects a negative price and a percent outside 0 to 100.
- `segment_trip` raises `ValueError` for fewer than 1 traveler or negative days, where it used to return leisure or business.
- `build_offers` no longer raises `KeyError` for a segment a bundle has no likelihood for (couple, one-way): it uses the overall share. It raises `ValueError` for no bundles or repeated names, and compares bundles by name.
- `epsilon_greedy`, `ucb` and `thompson` raise `ValueError` for no arms, and `epsilon_greedy` for an explore index outside the arms; a negative index used to pick from the end.
- `epsilon_greedy` raises `ValueError` for an epsilon or draw outside 0 to 1; `thompson` for an arm with no sample; `update` for a reward that is not 0 or 1; `cumulative_regret` for no arms or an unknown one; and `Arm` for negative pulls. Before, some raised `KeyError`, and a bad reward or negative pulls gave a wrong mean.
- `Arm` raises `ValueError` for a mean outside 0 to 1 (with a tolerance of 1e-9) or NaN, and `update` keeps the mean inside that range. Before, a NaN or out-of-range mean made `ucb`, `epsilon_greedy` and `thompson` choose an arbitrary arm.
