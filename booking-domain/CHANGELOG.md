# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/). Edits to a `.feature` go under **Changed**, with the reason.

## [Unreleased]

### Added
- Behavior specs: `features/booking.feature`, `features/carriers.feature`, `features/segment_status.feature` and `features/tickets_and_emd.feature`.
- `Booking`: needs a GDS locator, a passenger and a segment; takes the airline locator later; issues tickets (one ticket covers at most 4 segments) and EMDs.
- `TicketNumber` (3 + 10 digits), `Ticket` and `issue_tickets`: conjunction tickets with consecutive numbers, up to 12 coupons.
- `Segment` and `Status` (HK, HL, UC, XX): confirm, wait, cancel; carrier codes validated as 2 characters.
- `Emd`: type A needs a ticket, type B is standalone.

### Changed
- `features/booking.feature`: an assumption and scenarios for a ticket per passenger, a passenger ticketed once, and coupons only for confirmed segments. Reason: a code review found the booking issued one ticket whatever the passengers, and counted cancelled and unconfirmed segments as coupons.
- `Booking.issue_ticket` and `Booking.issue_conjunction_tickets` take the passenger first, and `Ticket` has a `passenger`. A ticket has one coupon per confirmed segment (HK); a passenger is ticketed once and must be one of the booking's passengers; a booking with no confirmed segment cannot be ticketed.
- `features/booking.feature`, `features/tickets_and_emd.feature` and `features/carriers.feature`: an assumption and scenarios for a ticket number issued once, a conjunction on a booking of more than 4 segments, an EMD-A for a ticket of the same booking, an EMD-B with no ticket, and the validating carrier code. Reason: a code review found these rules were in the feature text but not enforced.
- `features/carriers.feature`: added a scenario for the carrier code format. The two original scenarios only read fields and passed without code, so they did not specify behavior.
- Build backend `uv_build` 0.13 and Python 3.15 (`.python-version`); dependencies re-resolved to the latest releases.

### Fixed
- `Booking.issue_conjunction_tickets` (new): a booking of 5 to 12 segments can now be ticketed, and `issue_tickets` takes a validating carrier. Before, `issue_ticket` rejected it and nothing stored conjunction tickets.
- `Booking.issue_ticket` rejects a ticket number already issued.
- `Booking.issue_emd` rejects an EMD-A for a ticket that is not in the booking, an EMD-B with a ticket, and an empty ticket number, which used to give an EMD-A with no ticket.
- `Ticket` validates the validating carrier as 2 capital letters or digits.
- `TicketNumber` accepts only ASCII digits; `next` raises `ValueError` after `9999999999`, and `issue_tickets` no longer computes a number past the last ticket.
- `Emd` and `Ticket` check their own invariants: an EMD has type A with a ticket or type B without one, and a ticket holds 1 to 4 coupons. Before, only `Booking.issue_emd` checked the EMD, and `Ticket(number, coupons=0)` or `5` could be built directly.
