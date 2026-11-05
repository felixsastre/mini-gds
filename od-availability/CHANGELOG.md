# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/). Edits to a `.feature` go under **Changed**, with the reason.

## [Unreleased]

### Added
- Behavior spec: `features/od_availability.feature` (net contribution, open and closed classes, seats left on every leg).
- `net_contribution` and `is_open` over a list of `Leg` (bid price, seats left).

### Changed
- `features/od_availability.feature`: an assumption and two scenarios for a negative market fare value. Reason: a code review found `is_open` accepted a negative or non-Decimal fare value.
- `features/od_availability.feature`: two assumptions and two scenarios (an itinerary without legs is closed; a leg with a negative bid price or negative seats left is rejected), from a code review that found `is_open` true for no legs.
- Build backend `uv_build` 0.13 and Python 3.15 (`.python-version`); dependencies re-resolved to the latest releases.

### Fixed
- `is_open` returns closed for an itinerary with no legs; before, a positive fare value made it open.
- `Leg` raises `ValueError` for a negative bid price, negative seats left, or a bid price that is not a `Decimal`, instead of failing later inside the arithmetic or treating negative seats as none.
- `is_open` and `net_contribution` raise `ValueError` for a market fare value that is not a finite, non-negative `Decimal` (a float gave `TypeError`), even for an itinerary with no legs. `Leg` raises `ValueError` for seats left that are not an integer (a `bool` or a float was accepted) and for a bid price that is not finite.
