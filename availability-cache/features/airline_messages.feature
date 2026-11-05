# Assumption: a status message carries the seats left for one class on one flight; 0 seats is a close, more than 0 is open.
# Assumption: a class with no message at all is considered open, because the airline only sends a message when something changes.
# Assumption: a later message for the same class replaces the earlier one.

Feature: Airline status messages
  The airline does not send its inventory. It pushes short status messages when a class
  opens or closes. A distributor that only reads these messages assumes a class is open
  until it is told otherwise.

  Scenario: A close message closes the class
    When the airline sends a status message of 0 seats for class M on flight AA100
    Then class M on flight AA100 is closed

  Scenario: A later message reopens the class
    Given the airline sent a status message of 0 seats for class M on flight AA100
    When the airline sends a status message of 3 seats for class M on flight AA100
    Then class M on flight AA100 is open

  Scenario: A class without messages is considered open
    Given no status message was sent for class K on flight AA100
    Then class K on flight AA100 is open

  Scenario: A lost close message leaves a closed class shown as open
    Given the host has class M closed on flight AA100
    And the close message for class M on flight AA100 never arrived
    Then class M on flight AA100 is open
    And comparing it with the host gives an open-wrong error
