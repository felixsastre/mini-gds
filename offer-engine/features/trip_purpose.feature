# Assumption: segment names and boundaries are invented for this project, except business (booked 0 to 6 days ahead, stay of 0 to 1 days).
# Assumption: business is a single traveler.
# Assumption: a trip has at least 1 traveler, and days ahead and days of stay are never negative; anything else is invalid.
# Assumption: rules apply in this order: one-way, business, family, couple, leisure. Each trip gets exactly one segment.

Feature: Trip-purpose segmentation
  The context of a search says why the person travels. Each search belongs to one segment,
  so the airline can show the offers that segment tends to buy.

  Scenario Outline: A round trip gets one segment from its context
    Given a round trip booked <days_ahead> days ahead with a stay of <stay_days> days for <travelers> travelers
    Then the segment is <segment>

    Examples:
      | days_ahead | stay_days | travelers | segment  |
      | 3          | 1         | 1         | business |
      | 6          | 0         | 1         | business |
      | 7          | 1         | 1         | leisure  |
      | 3          | 2         | 1         | leisure  |
      | 3          | 1         | 3         | family   |
      | 30         | 7         | 4         | family   |
      | 30         | 7         | 2         | couple   |
      | 30         | 7         | 1         | leisure  |

  Scenario: A one-way trip is its own segment
    Given a one-way trip booked 3 days ahead for 1 travelers
    Then the segment is one-way

  Scenario Outline: An impossible trip is invalid
    Given a round trip booked <days_ahead> days ahead with a stay of <stay_days> days for <travelers> travelers
    Then the trip is invalid

    Examples:
      | days_ahead | stay_days | travelers |
      | 3          | 1         | 0         |
      | -5         | 0         | 1         |
      | 3          | -1        | 1         |
