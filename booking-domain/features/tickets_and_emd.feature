# Assumption: a ticket has at most 4 flight coupons; longer itineraries use consecutive tickets issued together (a conjunction).
# Assumption: an itinerary has at most 12 flight coupons.
# Assumption: an EMD number format is not checked.
# Assumption: an EMD-A is associated with a ticket of the same booking, and an EMD-B has none.

Feature: Coupons, conjunction tickets and EMDs
  A ticket holds at most 4 flight coupons, a limit inherited from the paper ticket.
  Longer itineraries use conjunction tickets. Extras such as bags and seats are
  documented by an EMD, associated with a ticket or standalone.

  Scenario Outline: Coupons are split into conjunction tickets
    Given an itinerary with <coupons> flight coupons
    When tickets are issued starting at number "125-1234567890"
    Then <tickets> tickets are issued
    And the coupons per ticket are <split>
    And the ticket numbers are <numbers>

    Examples:
      | coupons | tickets | split   | numbers                                     |
      | 4       | 1       | 4       | 125-1234567890                              |
      | 6       | 2       | 4, 2    | 125-1234567890, 125-1234567891              |
      | 8       | 2       | 4, 4    | 125-1234567890, 125-1234567891              |
      | 9       | 3       | 4, 4, 1 | 125-1234567890, 125-1234567891, 125-1234567892 |

  Scenario: An itinerary over the limit is rejected
    Given an itinerary with 13 flight coupons
    When tickets are issued starting at number "125-1234567890"
    Then the issue is rejected

  Scenario: An EMD-A is associated with a ticket
    Given a booking with a ticket "125-1234567890"
    When an EMD of type A is issued for that ticket
    Then the EMD is associated with ticket "125-1234567890"

  Scenario: An EMD-A without a ticket is rejected
    Given a booking with no tickets
    When an EMD of type A is issued without a ticket
    Then the issue is rejected

  Scenario: An EMD-B is standalone
    Given a booking with no tickets
    When an EMD of type B is issued
    Then the EMD has no associated ticket

  Scenario: An EMD-A for a ticket that is not in the booking is rejected
    Given a booking with no tickets
    When an EMD of type A is issued for ticket "999-1234567890"
    Then the issue is rejected

  Scenario: An EMD-B with a ticket is rejected
    Given a booking with a ticket "125-1234567890"
    When an EMD of type B is issued for ticket "125-1234567890"
    Then the issue is rejected
