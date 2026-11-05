# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/). Edits to a `.feature` go under **Changed**, with the reason.

## [Unreleased]

### Added
- Behavior specs: `features/availability_cache.feature` (time to live, airline updates, market restricted flights) and `features/stale_availability.feature` (open-wrong and closed-wrong errors, wash of the top offers).
- `Cache` with `Availability`, `Update` and `Restrict`: entries expire at the time to live and are refreshed from the host. Safe for concurrent use.
- `Classify` and `Wash`: compare cached and host availability; drop closed offers within the validated top.
- Behavior spec: `features/airline_messages.feature` (status messages close or reopen a class; a class with no message is considered open).
- `StatusBoard` with `Apply` and `Open`.
- Dependency: `github.com/cucumber/godog`.

### Changed
- `Host.Seats` returns `(int, error)` and `Cache.Availability` returns `(int, error)`: a host that cannot answer is no longer the same as zero seats. Nothing is stored when it fails, and an expired entry is not served in its place. `Wash` keeps an offer the host could not answer about and counts no error. Reason: a failed call used to be stored as "closed" for the whole time to live.
- `features/availability_cache.feature` and `features/stale_availability.feature`: assumptions and scenarios for an entry stored in the future, a host that cannot answer, and an offer kept when the host cannot answer.
- Go 1.27.3; indirect dependencies (`gherkin`, `messages`, `go-uuid`, `golang-lru`) updated to the latest releases.

### Fixed
- `Cache.Availability` no longer holds its lock while the host answers, so a slow host delays only the callers that need it. Two callers that miss at once both ask the host.
- An entry stored in the future, because the clock went back, is expired; before, it counted as fresh until the clock caught up and the time to live passed on top.
- Expired entries are dropped as the cache grows, so keys nobody asks for again no longer pile up.
- `Cache.Availability` keeps an airline update that arrived while the host was still answering. Before, the late host answer overwrote it, and a class the airline had just closed showed as open for a whole time to live.
- The `godog` suite runs in strict mode, so an undefined or misspelled step fails it instead of leaving the scenario unchecked.
