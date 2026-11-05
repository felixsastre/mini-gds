# Assumption: the airline's revenue management keeps two numbers, and both are set directly in these scenarios. One is the market value of each class on the connection (its market class fare value), the other is a bid price per leg.
# Assumption: a class is open on a connection when every leg has a seat and the market value minus the sum of the leg bid prices is above zero. A net contribution of zero is closed.
# Assumption: the market value is the airline's own forecast, so it is independent of the price a bundle is sold at.
# Assumption: a class with no market value (the single flights in search.feature) is judged on seats alone, as before.
# Assumption: offers on a connection are built, checked and shown the same way as on a single flight.

Feature: Search on a connection
  A connection is judged as a whole. Seats on every leg are not enough: the class must also be
  worth more than the seats it takes on the legs, so a class can be closed while seats remain.

  Background:
    Given the airline sells these bundles from JFK to MAD on flights AA100 and AA200:
      | bundle | class | price | ancillaries | business | leisure | overall |
      | Basic  | K     | 300   | 0           | 0.30     | 0.80    | 0.60    |
      | Flex   | M     | 420   | 2           | 0.70     | 0.20    | 0.40    |
    And the airline values class K at 300 and class M at 420 from JFK to MAD
    And the bid price is 100 on AA100
    And classes K and M have 4 seats at the airline on flights AA100 and AA200

  Scenario Outline: A class is open only while it is worth more than the legs cost
    Given the bid price is <bid_price> on AA200
    When a customer searches JFK to MAD, 1 traveler, booked 3 days ahead, staying 1 day
    Then Basic is <basic> and Flex is <flex>

    Examples:
      | bid_price | basic       | flex        |
      | 150       | offered     | offered     |
      | 199       | offered     | offered     |
      | 200       | not offered | offered     |
      | 220       | not offered | offered     |
      | 320       | not offered | not offered |

  Scenario: A leg without seats closes the class
    Given class M has 0 seats at the airline on flight AA200
    And the bid price is 150 on AA200
    When a customer searches JFK to MAD, 1 traveler, booked 3 days ahead, staying 1 day
    Then the offers are Basic only
