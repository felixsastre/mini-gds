# Assumption: the best offer is the bundle the segment is most likely to buy.
# Assumption: a decoy is a bundle dominated by the best one: it costs the same or more and has the same or fewer ancillaries. Of those, the cheapest is the decoy; if none is dominated, no decoy is shown.
# Assumption: the popular offer is the bundle bought most across all segments; if it is already shown, the next most popular takes its place.
# Assumption: a bundle without a likelihood for a segment counts with its overall share. Bundle names are unique, and offers need at least one bundle.

Feature: Three offers per search
  For each search the airline shows up to three bundles: the best one for the segment,
  a decoy that makes the best one look better, and a popular one as a safety net in case
  the segment was inferred wrong.

  Background:
    Given these bundles:
      | bundle   | price | ancillaries | business | family | leisure | overall |
      | Basic    | 200   | 0           | 0.10     | 0.05   | 0.50    | 0.35    |
      | Flex     | 260   | 2           | 0.55     | 0.15   | 0.25    | 0.30    |
      | Flex Max | 300   | 2           | 0.05     | 0.10   | 0.05    | 0.10    |
      | Plus     | 310   | 3           | 0.25     | 0.60   | 0.15    | 0.20    |
      | Plus Max | 360   | 3           | 0.05     | 0.10   | 0.05    | 0.05    |

  Scenario: Business gets Flex, a dominated decoy and the popular bundle
    When offers are built for the business segment
    Then the best offer is Flex
    And the decoy offer is Flex Max
    And the popular offer is Basic

  Scenario: Family gets Plus
    When offers are built for the family segment
    Then the best offer is Plus
    And the decoy offer is Plus Max
    And the popular offer is Basic

  Scenario: Without a dominated bundle there is no decoy, and a repeated popular bundle is replaced
    When offers are built for the leisure segment
    Then the best offer is Basic
    And there is no decoy offer
    And the popular offer is Flex

  Scenario: A segment without data falls back to the overall sales
    When offers are built for the couple segment
    Then the best offer is Basic
    And there is no decoy offer
    And the popular offer is Flex
