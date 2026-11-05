# Assumption: a carrier is a 2-character airline code of capital letters or digits. Codeshare block types (hard block, soft block, free sale) are out of scope.

Feature: Carriers on a segment
  A flight segment can involve three carriers that are not always the same company:
  the marketing carrier whose code is sold, the operating carrier that flies it, and the
  validating carrier that issues the ticket.

  Scenario: A codeshare flight has different marketing and operating carriers
    Given a segment sold under AA and operated by IB
    And the ticket is validated by AA
    Then the marketing carrier is AA
    And the operating carrier is IB
    And the validating carrier is AA

  Scenario: A flight on one airline has the same carrier in all three roles
    Given a segment sold under IB and operated by IB
    And the ticket is validated by IB
    Then the marketing carrier is IB
    And the operating carrier is IB
    And the validating carrier is IB

  Scenario Outline: A carrier is a two-character airline code
    When a segment is sold under <marketing> and operated by <operating>
    Then the segment is <outcome>

    Examples:
      | marketing | operating | outcome  |
      | AA        | IB        | accepted |
      | U2        | IB        | accepted |
      | A         | IB        | rejected |
      | AAA       | IB        | rejected |
      | AA        | ib        | rejected |

  Scenario Outline: A validating carrier is a two-character airline code
    When a ticket is validated by <carrier>
    Then the ticket is <outcome>

    Examples:
      | carrier | outcome  |
      | IB      | accepted |
      | U2      | accepted |
      | I       | rejected |
      | IBE     | rejected |
      | ib      | rejected |
