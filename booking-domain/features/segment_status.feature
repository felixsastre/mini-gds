# Assumption: status codes vary by system. This project uses four: HK confirmed, HL waitlisted, UC unable to confirm, XX cancelled.
# Assumption: UC and XX are final; a waitlisted segment can be confirmed or cancelled; a confirmed one can be cancelled.

Feature: Segment status
  Each segment of a booking has a status that says whether the airline holds the seat.

  Scenario: A sold segment is confirmed when the airline has the seat
    When a segment is sold and the airline confirms it
    Then the segment status is HK

  Scenario: A sold segment is UC when the airline cannot confirm it
    When a segment is sold and the airline cannot confirm it
    Then the segment status is UC

  Scenario: A waitlisted segment is confirmed when a seat opens
    Given a segment with status HL
    When a seat opens
    Then the segment status is HK

  Scenario Outline: Cancelling
    Given a segment with status <before>
    When the segment is cancelled
    Then the result is <result>

    Examples:
      | before | result       |
      | HK     | status XX    |
      | HL     | status XX    |
      | XX     | rejected     |
      | UC     | rejected     |

  Scenario: A cancelled segment cannot be confirmed
    Given a segment with status XX
    When a seat opens
    Then the segment status is XX
