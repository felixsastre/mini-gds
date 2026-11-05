# Assumption: sales use threshold nesting in the scenarios that do not say otherwise.
# Assumption: authorizations, bookings and the seats of a sale are never negative; such values are invalid.

Feature: Nested inventory availability
  A cabin sells booking classes arranged in a hierarchy, highest class first. Each class has
  an authorization (a sales limit), not a share of the seats. Authorizations may add up to
  more than the physical capacity. Availability is derived from authorizations and bookings.

  Background:
    Given a cabin with 300 seats
    And the following authorizations, highest class first:
      | class | authorization |
      | Y     | 420           |
      | B     | 385           |
      | M     | 320           |
      | H     | 260           |
      | V     | 210           |
      | Z     | 180           |
      | Q     | 60            |
    And bookings of Y 5, B 10, M 20, H 35, V 50, Z 55, Q 80

  Scenario Outline: Threshold nesting subtracts the total sold in the cabin
    # Available = authorization - total sold (255)
    Given the airline uses threshold nesting
    Then availability of <class> is <available>

    Examples:
      | class | available |
      | Y     | 165       |
      | B     | 130       |
      | M     | 65        |
      | H     | 5         |
      | V     | -45       |
      | Z     | -75       |
      | Q     | -195      |

  Scenario Outline: Net nesting subtracts the sold in that class and lower classes
    # Available = authorization - sold in the class and lower ones,
    # and never more than the class above it. Z: 180 - 135 = 45, capped to 25 by V.
    Given the airline uses net nesting
    Then availability of <class> is <available>

    Examples:
      | class | available |
      | Y     | 165       |
      | B     | 135       |
      | M     | 80        |
      | H     | 40        |
      | V     | 25        |
      | Z     | 25        |
      | Q     | -20       |

  Scenario Outline: A class with no seats left to sell is unavailable
    Given the airline uses threshold nesting
    Then class <class> is <state>

    Examples:
      | class | state       |
      | H     | available   |
      | V     | unavailable |
      | Q     | unavailable |

  Scenario: A seat is sold in an open class
    Given the airline uses threshold nesting
    When a seat is requested in class M
    Then the sale is accepted
    And availability of M is 64

  Scenario: A seat is not sold in an unavailable class
    Given the airline uses threshold nesting
    When a seat is requested in class Q
    Then the sale is rejected

  Scenario: The highest class can be sold beyond the physical capacity
    # Y's authorization is the overbooking limit.
    Given the airline uses threshold nesting
    When 165 seats are sold in class Y
    Then more seats are sold than the cabin has
    And class Y is unavailable

  Scenario Outline: Net nesting limits a sale to the margin of the class and the classes above it
    Given the airline uses net nesting
    When <seats> seats are requested in class <class>
    Then the sale is <outcome>

    Examples:
      | class | seats | outcome  |
      | V     | 25    | accepted |
      | V     | 26    | rejected |
      | Z     | 25    | accepted |
      | Z     | 26    | rejected |

  Scenario: A negative number of seats cannot be sold
    Given the airline uses threshold nesting
    When -50 seats are requested in class Y
    Then the request is invalid
    And availability of Y is 165

  Scenario: Negative bookings cannot be loaded
    When bookings of Y -100 are loaded
    Then the request is invalid

  Scenario: A negative authorization cannot be set
    When a cabin is set up with an authorization of -5 for class Y
    Then the request is invalid
