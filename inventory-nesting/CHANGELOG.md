# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/). Edits to a `.feature` go under **Changed**, with the reason.

## [Unreleased]

### Added
- Behavior specs: `features/nesting.feature` (threshold and net nesting, availability by class, sales, overbooking) and `features/availability_cap.feature` (distributor cap).
- `Inventory` with `Nesting.THRESHOLD` and `Nesting.NET` availability, `is_available`, and `sell` limited by availability.
- `availability_shown`: capped, never negative.

### Changed
- `features/nesting.feature` and `features/availability_cap.feature`: an assumption that authorizations, bookings, seats sold and the cap are never negative; scenarios for that, for selling under net nesting, and for the cap boundaries. Reason: a code review found `sell` accepted negative seats and created availability.
- Build backend `uv_build` 0.13 and Python 3.15 (`.python-version`); dependencies re-resolved to the latest releases.

### Fixed
- `sell`, `load_bookings`, the constructor and `availability_shown` raise `ValueError` for negative seats, bookings, authorizations or cap, where they used to accept them and corrupt the availability of every class. `load_bookings` checks every class before it changes any.
