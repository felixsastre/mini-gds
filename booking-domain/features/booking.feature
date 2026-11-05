# Assumption: a booking is created with a GDS locator, at least one passenger and at least one segment.
# Assumption: the airline locator arrives after the sell, so it starts empty.
# Assumption: a ticket can only be issued for an existing booking. The ticket check digit is not verified.
# Assumption: a ticket number is issued once per booking.
# Assumption: a ticket belongs to one passenger, and a passenger is ticketed once. Each passenger of the booking needs their own ticket.
# Assumption: only confirmed segments (HK) get a flight coupon; cancelled, waitlisted and unable-to-confirm segments do not. A booking with no confirmed segment cannot be ticketed.

Feature: Booking and ticket
  A booking reserves seats; a ticket is the paid document. A confirmed booking can exist
  without a ticket, and the same trip is known by different identifiers in different systems.

  Scenario: A booking can exist without a ticket
    Given a booking with 1 passenger and 1 segment
    Then the booking has a GDS locator
    And the booking has no tickets

  Scenario: The airline locator arrives after the sell
    Given a booking with 1 passenger and 1 segment
    When the airline returns its locator "QX7P2L"
    Then the booking has the airline locator "QX7P2L"

  Scenario: Issuing a ticket adds its number to the booking
    Given a booking with 1 passenger and 1 segment
    When a ticket is issued with number "125-1234567890"
    Then the booking has 1 ticket
    And the ticket number is "125-1234567890"

  Scenario Outline: A ticket number is 3 digits of airline code and 10 digits of document number
    Given a booking with 1 passenger and 1 segment
    When a ticket is issued with number "<number>"
    Then the ticket is <outcome>

    Examples:
      | number          | outcome  |
      | 125-1234567890  | accepted |
      | 125-123456789   | rejected |
      | 12-12345678901  | rejected |
      | ABC-1234567890  | rejected |

  Scenario: A ticket number cannot be issued twice
    Given a booking with 2 passengers and 1 segment
    When a ticket is issued for passenger 1 with number "125-1234567890"
    And a ticket is issued for passenger 2 with number "125-1234567890"
    Then the ticket is rejected
    And the booking has 1 ticket

  Scenario: A booking of 6 segments is ticketed with a conjunction
    Given a booking with 1 passenger and 6 segments
    When conjunction tickets are issued starting at number "125-1234567890"
    Then the booking has 2 tickets
    And the ticket numbers are 125-1234567890, 125-1234567891

  Scenario: Each passenger gets their own ticket
    Given a booking with 2 passengers and 1 segment
    When a ticket is issued for passenger 1 with number "125-1234567890"
    And a ticket is issued for passenger 2 with number "125-1234567891"
    Then the booking has 2 tickets

  Scenario: A passenger is ticketed once
    Given a booking with 2 passengers and 1 segment
    When a ticket is issued for passenger 1 with number "125-1234567890"
    And a ticket is issued for passenger 1 with number "125-1234567891"
    Then the ticket is rejected
    And the booking has 1 ticket

  Scenario: A cancelled segment gets no coupon
    Given a booking with 1 passenger and 5 segments, 1 of them cancelled
    When a ticket is issued with number "125-1234567890"
    Then the ticket has 4 coupons

  Scenario: A booking with no confirmed segment cannot be ticketed
    Given a booking with 1 passenger and 1 segment, 1 of them cancelled
    When a ticket is issued with number "125-1234567890"
    Then the ticket is rejected
