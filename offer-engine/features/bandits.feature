# Assumption: rewards are 0 or 1 (bought or not) and each arm is a bundle.
# Assumption: randomness is injected, so each scenario states the random values it uses.
# Assumption: choosing needs at least one arm, and the arm to explore must be one of them.
# Assumption: epsilon and the random draw are between 0 and 1, a reward is 0 or 1, Thompson Sampling needs a sample for every arm, and regret needs the true mean of every arm chosen; anything else is invalid.
# Assumption: UCB is UCB1: mean + sqrt(2 * ln(total pulls) / arm pulls).

Feature: Test and learn with bandits
  With many possible bundles, classic A/B tests are too slow. A bandit tries several
  bundles at once, sends more traffic to the ones that sell, and keeps learning.

  Scenario: Epsilon-greedy exploits the best arm
    Given these arms:
      | arm | pulls | mean reward |
      | A   | 10    | 0.5         |
      | B   | 10    | 0.2         |
    When epsilon-greedy with epsilon 0.1 chooses with a random draw of 0.5
    Then the chosen arm is A

  Scenario: Epsilon-greedy explores when the draw is below epsilon
    Given these arms:
      | arm | pulls | mean reward |
      | A   | 10    | 0.5         |
      | B   | 10    | 0.2         |
    When epsilon-greedy with epsilon 0.1 chooses with a random draw of 0.05 and picks the 2nd arm
    Then the chosen arm is B

  Scenario: UCB tries every arm before comparing
    Given these arms:
      | arm | pulls | mean reward |
      | A   | 10    | 0.9         |
      | B   | 0     | 0.0         |
    When UCB chooses
    Then the chosen arm is B

  Scenario: UCB favors an arm with few pulls
    Given these arms:
      | arm | pulls | mean reward |
      | A   | 10    | 0.5         |
      | B   | 2     | 0.4         |
    When UCB chooses
    Then the chosen arm is B

  Scenario: Thompson Sampling chooses the arm with the highest sample
    Given these arms:
      | arm | pulls | mean reward |
      | A   | 10    | 0.5         |
      | B   | 10    | 0.2         |
    When Thompson Sampling chooses with samples A 0.31 and B 0.74
    Then the chosen arm is B

  Scenario: A reward updates the mean of the chosen arm
    Given these arms:
      | arm | pulls | mean reward |
      | A   | 4     | 0.5         |
    When arm A receives a reward of 1
    Then arm A has 5 pulls and a mean reward of 0.6

  Scenario: Regret adds what each choice gave up
    Given the true mean rewards are A 0.6 and B 0.4
    When the arms chosen in order are A, B, B, A
    Then the cumulative regret is 0.4

  Scenario: Choosing among no arms is invalid
    Given no arms
    When UCB chooses
    Then the request is invalid

  Scenario: Exploring an arm that does not exist is invalid
    Given these arms:
      | arm | pulls | mean reward |
      | A   | 10    | 0.5         |
      | B   | 10    | 0.2         |
    When epsilon-greedy with epsilon 0.1 chooses with a random draw of 0.05 and picks the 3rd arm
    Then the request is invalid

  Scenario Outline: An impossible epsilon or draw is invalid
    Given these arms:
      | arm | pulls | mean reward |
      | A   | 10    | 0.5         |
      | B   | 10    | 0.2         |
    When epsilon-greedy with epsilon <epsilon> chooses with a random draw of <draw>
    Then the request is invalid

    Examples:
      | epsilon | draw |
      | 1.5     | 0.5  |
      | -0.1    | 0.5  |
      | 0.1     | 1.5  |

  Scenario: A reward other than 0 or 1 is invalid
    Given these arms:
      | arm | pulls | mean reward |
      | A   | 4     | 0.5         |
    When arm A receives a reward of 2
    Then the request is invalid

  Scenario: Thompson Sampling needs a sample for every arm
    Given these arms:
      | arm | pulls | mean reward |
      | A   | 10    | 0.5         |
      | B   | 10    | 0.2         |
    When Thompson Sampling chooses with samples A 0.31
    Then the request is invalid

  Scenario: Regret needs the true mean of every arm chosen
    Given the true mean rewards are A 0.6 and B 0.4
    When the arms chosen in order are A, C
    Then the request is invalid
