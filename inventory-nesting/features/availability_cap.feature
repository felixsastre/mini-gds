# Assumption: a negative availability is shown as 0.
# Assumption: the distributor cap is never negative. A cap of 0 shows 0.

Feature: Availability sent to a distributor
  A distributor receives a capped number. A shown "9" means "9 or more".

  Scenario Outline: The number is capped
    Given the distributor cap is <cap>
    And a class has a computed availability of <computed>
    Then the availability shown to the distributor is <shown>

    Examples:
      | cap | computed | shown |
      | 9   | 12       | 9     |
      | 9   | 9        | 9     |
      | 9   | 5        | 5     |
      | 7   | 12       | 7     |
      | 4   | 12       | 4     |
      | 9   | 0        | 0     |
      | 9   | -20      | 0     |
      | 9   | 10       | 9     |
      | 0   | 5        | 0     |

  Scenario: A negative cap is invalid
    Given the distributor cap is -1
    And a class has a computed availability of 5
    When the availability is shown to the distributor
    Then the request is invalid
