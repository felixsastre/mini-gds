# Assumption: each bundle is sold in exactly one booking class. A bundle is offered only while its class is open at the airline.
# Assumption: the three offers shown are the ones the offer rules build (best, decoy, popular), limited to bundles whose class is open.
# Assumption: before showing results, the top 2 offers are checked against the airline (wash).
# Assumption: a bundle with no likelihood for the kind of trip counts with its overall share.
# Assumption: when the airline cannot answer about a class the distributor has no fresh copy of, the class is left out of the offers, and the search report counts it separately from the closed classes.
# Assumption: the airline is the source of truth; the distributor keeps a copy that can be stale.

Feature: Search
  A customer searches for a flight and gets offers. The offers are built for the kind of trip,
  shown only for classes that can be sold, and checked against the airline before they are shown.

  Background:
    Given the airline sells these bundles on flight AA100 from JFK to LHR:
      | bundle | class | price | ancillaries | business | leisure | overall |
      | Basic  | K     | 200   | 0           | 0.30     | 0.80    | 0.60    |
      | Flex   | M     | 260   | 2           | 0.70     | 0.20    | 0.40    |

  Scenario: A business trip is offered Flex first
    Given class K has 9 seats and class M has 4 seats on flight AA100
    When a customer searches JFK to LHR, 1 traveler, booked 3 days ahead, staying 1 day
    Then the best offer is Flex at 260
    And the popular offer is Basic at 200

  Scenario: A closed class removes its bundle
    Given class K has 9 seats and class M has 0 seats on flight AA100
    When a customer searches JFK to LHR, 1 traveler, booked 3 days ahead, staying 1 day
    Then the offers are Basic only

  Scenario: A class that closed without the distributor knowing is not shown
    Given class K has 9 seats and class M has 0 seats at the airline on flight AA100
    And the distributor was never told that class M closed
    When a customer searches JFK to LHR, 1 traveler, booked 3 days ahead, staying 1 day
    Then the offers are Basic only
    And the search report shows 1 open-wrong error caught

  Scenario: A kind of trip the airline has no data for is offered by overall sales
    Given class K has 9 seats and class M has 4 seats on flight AA100
    When a customer searches JFK to LHR, 2 travelers, booked 30 days ahead, staying 7 days
    Then the best offer is Basic at 200
    And the popular offer is Flex at 260

  Scenario: A class the airline cannot answer about is left out and counted
    Given class K has 9 seats and class M has 4 seats on flight AA100
    And the distributor has no copy of class M
    And the airline cannot answer about class M
    When a customer searches JFK to LHR, 1 traveler, booked 3 days ahead, staying 1 day
    Then the offers are Basic only
    And the search report shows 1 class left out because the airline did not answer
