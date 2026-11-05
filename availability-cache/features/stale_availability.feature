# Assumption: only open versus closed counts as an error; different seat counts with the class open on both sides is not an error.
# Assumption: a host that cannot answer is no proof that an offer is closed, so the offer is shown unchecked and no error is counted.
# Assumption: the offers are validated in the order they are shown, and only the first N are checked.

Feature: Stale availability
  When the cache disagrees with the host, a search can show a class that cannot be sold,
  or hide one that can. Validating the top results against the host limits the first kind.

  Scenario Outline: A cached answer is compared with the host
    Given the cache says <cached> seats for class M on flight AA100
    And the host has <host> seats for class M on flight AA100
    Then the result is <error>

    Examples:
      | cached | host | error                  |
      | 4      | 0    | open-wrong (type 1)    |
      | 0      | 4    | closed-wrong (type 2)  |
      | 4      | 2    | no error               |
      | 0      | 0    | no error               |

  Scenario: Validating the top offers removes the ones the host cannot sell
    Given the cache says class M is open on flights AA100, AA200 and AA300
    And the host has class M closed on flight AA200
    When the top 3 offers are validated against the host
    Then the offers shown are on flights AA100 and AA300
    And 1 open-wrong error was caught

  Scenario: Offers beyond the validated top are shown unchecked
    Given the cache says class M is open on flights AA100, AA200 and AA300
    And the host has class M closed on flight AA300
    When the top 2 offers are validated against the host
    Then the offers shown are on flights AA100, AA200 and AA300
    And 0 open-wrong errors were caught

  Scenario: An offer is kept when the host cannot answer about it
    Given the cache says class M is open on flights AA100, AA200 and AA300
    And the host cannot answer for class M on flight AA200
    And the host has class M closed on flight AA300
    When the top 3 offers are validated against the host
    Then the offers shown are on flights AA100 and AA200
    And 1 open-wrong error was caught
