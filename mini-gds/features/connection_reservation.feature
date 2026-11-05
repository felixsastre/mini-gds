# Assumption: reserving a connection sells one seat on each leg and creates one booking with one segment per leg.
# Assumption: the legs are sold in order; if a later leg cannot be confirmed, the seats already sold are given back.
# Assumption: the hold, the payment and the ticket work as in reservation.feature.
# Assumption: an itinerary of more than 4 flights is ticketed with conjunction tickets of consecutive numbers, 4 coupons at most on each; the first ticket is the booking's main ticket.
# Assumption: the validating carrier is the carrier of the first flight.

Feature: Reservation on a connection
  A connection is sold on every leg or on none. A customer never ends up holding the first
  flight of a trip whose second flight is full.

  Scenario: Reserving a connection takes a seat on each leg
    Given classes K and M have 4 seats at the airline on flights AA100 and AA200
    When a customer reserves class M on the connection of flights AA100 and AA200
    Then the booking has 2 segments with status HK
    And class M on flight AA100 has 3 seats at the airline
    And class M on flight AA200 has 3 seats at the airline

  Scenario: A connection that cannot be confirmed on every leg is sold on none
    Given class M has 4 seats at the airline on flight AA100
    And class M has 0 seats at the airline on flight AA200
    When a customer reserves class M on the connection of flights AA100 and AA200
    Then the airline cannot confirm the seat
    And no booking is created
    And class M on flight AA100 has 4 seats at the airline

  Scenario: Paying for a connection issues one ticket
    Given classes K and M have 4 seats at the airline on flights AA100 and AA200
    And a customer reserved class M on the connection of flights AA100 and AA200
    When the customer pays
    Then the booking has a ticket of 13 digits
    And the booking has 2 segments with status HK

  Scenario: An unpaid connection gives back the seat on each leg
    Given classes K and M have 4 seats at the airline on flights AA100 and AA200
    And a customer reserved class M on the connection of flights AA100 and AA200
    When 15 minutes pass
    Then the booking has 2 segments with status XX
    And class M on flight AA100 has 4 seats at the airline
    And class M on flight AA200 has 4 seats at the airline

  Scenario: A connection of five flights is ticketed with two tickets
    Given class M has 4 seats at the airline on each of flights AA100, AA200, AA300, AA400 and AA500
    And a customer reserved class M on the connection of flights AA100, AA200, AA300, AA400 and AA500
    When the customer pays
    Then the booking has 2 tickets with consecutive numbers
    And the booking has 5 segments with status HK
