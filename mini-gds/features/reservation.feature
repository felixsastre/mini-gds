# Assumption: reserving sells one seat at the airline and holds the booking for 15 minutes; if it is not paid by then, the booking is cancelled.
# Assumption: payment is simulated and either succeeds or is declined.
# Assumption: when the airline cannot confirm the seat, no booking is created.
# Assumption: the host starts with synthetic seats: flight AA100, class M, 4 seats.

Feature: Reservation
  A customer reserves an offer, pays within the hold time and gets a ticket. If anything
  goes wrong along the way, the seat goes back to the airline and nothing is left half done.

  Scenario: Reserving holds a seat and creates a booking without a ticket
    When a customer reserves class M on flight AA100
    Then the booking has a GDS locator and no ticket
    And the segment status is HK
    And class M on flight AA100 has 3 seats at the airline

  Scenario: Paying within the hold issues the ticket
    Given a customer reserved class M on flight AA100
    When 10 minutes pass
    And the customer pays
    Then the booking has a ticket of 13 digits
    And class M on flight AA100 has 3 seats at the airline

  Scenario: A hold that is not paid expires and frees the seat
    Given a customer reserved class M on flight AA100
    When 15 minutes pass
    Then the segment status is XX
    And the booking has no ticket
    And class M on flight AA100 has 4 seats at the airline

  Scenario: A declined payment cancels the booking and frees the seat
    Given a customer reserved class M on flight AA100
    When the customer pays and the payment is declined
    Then the segment status is XX
    And the booking has no ticket
    And class M on flight AA100 has 4 seats at the airline

  Scenario: A class that closed after the search cannot be confirmed
    Given class M has 0 seats at the airline on flight AA100
    When a customer reserves class M on flight AA100
    Then the airline cannot confirm the seat
    And no booking is created

  Scenario: The last seat is sold only once
    Given class M has 1 seat at the airline on flight AA100
    When two customers reserve class M on flight AA100 at the same time
    Then exactly one booking is created
    And class M on flight AA100 has 0 seats at the airline

  Scenario: A hold survives a restart of the booking worker
    Given a customer reserved class M on flight AA100
    When 5 minutes pass
    And the booking worker restarts
    And 5 minutes pass
    And the customer pays
    Then the booking has a ticket of 13 digits
