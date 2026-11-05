# Assumption: an itinerary needs at least one seat left on every leg to be sold.
# Assumption: an itinerary with no legs is not an itinerary, so its class is closed.
# Assumption: a bid price is never negative and a leg never has negative seats left.
# Assumption: a market fare value is never negative, and an itinerary with a negative one cannot be evaluated, even with no legs.

Feature: Origin-and-destination availability
  An airline decides whether a booking class is open for a whole itinerary, not leg by leg.
  A class is open when it has seats on every leg and its net contribution is positive.
  The net contribution is the market fare value minus the sum of the bid prices of the legs.

  Scenario Outline: Net contribution decides whether a class is open
    Given a market fare value of <fare_value>
    And legs with bid prices <bid_prices>
    And seats left on those legs: <seats_left>
    Then the net contribution is <net_contribution>
    And the class is <status>

    Examples: One leg
      | fare_value | bid_prices | seats_left | net_contribution | status |
      | 600        | 300        | 9          | 300              | open   |
      | 450        | 450        | 9          | 0                | closed |
      | 300        | 350        | 9          | -50              | closed |

    Examples: Two legs
      | fare_value | bid_prices | seats_left | net_contribution | status |
      | 1200       | 300, 700   | 9, 9       | 200              | open   |
      | 1050       | 300, 700   | 9, 9       | 50               | open   |
      | 600        | 300, 350   | 9, 9       | -50              | closed |
      | 540        | 300, 350   | 9, 9       | -110             | closed |

  Scenario: A leg without seats closes a class that is worth selling
    Given a market fare value of 1050
    And legs with bid prices 300, 700
    And seats left on those legs: 5, 0
    Then the net contribution is 50
    And the class is closed

  Scenario: Seats on every leg are not enough
    Given a market fare value of 450
    And legs with bid prices 450
    And seats left on those legs: 5
    Then the class is closed

  Scenario: An itinerary without legs is closed
    Given a market fare value of 600
    And no legs
    Then the class is closed

  Scenario Outline: A leg with impossible values is rejected
    When a leg has a bid price of <bid_price> and <seats_left> seats left
    Then the leg is rejected

    Examples:
      | bid_price | seats_left |
      | -1        | 5          |
      | 300       | -1         |

  Scenario: A negative market fare value cannot be evaluated
    Given a market fare value of -1
    And legs with bid prices 300
    And seats left on those legs: 5
    Then the class cannot be evaluated

  Scenario: A negative market fare value cannot be evaluated even without legs
    Given a market fare value of -1
    And no legs
    Then the class cannot be evaluated
