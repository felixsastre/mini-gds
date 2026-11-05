# Assumption: the discount is a percentage of the price, rounded down to 2 decimals so that it never reaches the maximum.
# Assumption: the spend is never negative, the maximum is above 0 and at most 100, and the constant is above 0; anything else is invalid.

Feature: Dynamic discount
  The discount grows with what the customer spends but never reaches the maximum.
  It follows the curve: discount = max * spend / (constant + spend).

  Scenario Outline: The discount follows the spend
    Given a maximum discount of 10 percent and a constant of 100
    When the customer spends <spend>
    Then the discount is <discount> percent

    Examples:
      | spend   | discount |
      | 0       | 0.00     |
      | 50      | 3.33     |
      | 100     | 5.00     |
      | 300     | 7.50     |
      | 9900    | 9.90     |
      | 2000000 | 9.99     |

  Scenario: The discount is applied to the price
    Given a maximum discount of 10 percent and a constant of 100
    When the customer spends 300 on a bundle priced 300
    Then the price offered is 277.50

  Scenario Outline: An impossible curve or spend is invalid
    Given a maximum discount of <max> percent and a constant of <constant>
    When the customer spends <spend>
    Then the request is invalid

    Examples:
      | max | constant | spend |
      | 10  | 100      | -300  |
      | 10  | 0        | 0     |
      | 0   | 100      | 50    |
      | 101 | 100      | 50    |
