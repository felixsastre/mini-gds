# Assumption: an entry is fresh while its age is below the time to live; at exactly the time to live it is expired.
# Assumption: the host always holds the truth; the cache is a copy that may be stale.
# Assumption: an entry stored in the future, because the clock went back, is expired.
# Assumption: when the host cannot answer, the caller gets the failure, nothing is stored, and an expired entry is not served in its place.
# Assumption: availability is the number of seats left in a class, from 0 to 9; 0 means closed.

Feature: Availability cache
  A distributor does not ask the airline host on every search. It keeps a copy of the
  availability of each class, and every entry expires after a time to live.

  Background:
    Given a cache with a time to live of 60 seconds

  Scenario: A fresh entry is served without asking the host
    Given the cache holds 4 seats for class M on flight AA100, stored 30 seconds ago
    And the host has 0 seats for class M on flight AA100
    When availability for class M on flight AA100 is requested
    Then the answer is 4 seats
    And the host was asked 0 times

  Scenario: An expired entry is refreshed from the host
    Given the cache holds 4 seats for class M on flight AA100, stored 60 seconds ago
    And the host has 0 seats for class M on flight AA100
    When availability for class M on flight AA100 is requested
    Then the answer is 0 seats
    And the host was asked 1 time
    And the cache holds 0 seats for class M on flight AA100

  Scenario: A missing entry is fetched from the host
    Given the host has 7 seats for class M on flight AA100
    When availability for class M on flight AA100 is requested
    Then the answer is 7 seats
    And the host was asked 1 time
    And the cache holds 7 seats for class M on flight AA100

  Scenario: An update from the airline replaces the entry and restarts its expiry
    Given the cache holds 4 seats for class M on flight AA100, stored 50 seconds ago
    When the airline sends an update of 0 seats for class M on flight AA100
    And 20 seconds pass
    And availability for class M on flight AA100 is requested
    Then the answer is 0 seats
    And the host was asked 0 times

  Scenario: A market restricted flight always asks the host
    Given flight AA100 is market restricted
    And the cache holds 4 seats for class M on flight AA100, stored 5 seconds ago
    And the host has 0 seats for class M on flight AA100
    When availability for class M on flight AA100 is requested
    Then the answer is 0 seats
    And the host was asked 1 time

  Scenario: An entry stored in the future is expired
    Given the cache holds 4 seats for class M on flight AA100, stored 10 seconds ago
    And the host has 0 seats for class M on flight AA100
    When the clock goes back 30 seconds
    And availability for class M on flight AA100 is requested
    Then the answer is 0 seats
    And the host was asked 1 time

  Scenario: A host that cannot answer leaves nothing in the cache
    Given the host cannot answer for class M on flight AA100
    When availability for class M on flight AA100 is requested
    Then the request fails
    When the host has 6 seats for class M on flight AA100
    And availability for class M on flight AA100 is requested
    Then the answer is 6 seats

  Scenario: A host that cannot answer does not bring back an expired entry
    Given the cache holds 4 seats for class M on flight AA100, stored 60 seconds ago
    And the host cannot answer for class M on flight AA100
    When availability for class M on flight AA100 is requested
    Then the request fails
