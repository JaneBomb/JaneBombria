Feature: Agent Advertising
  As a verified real estate agent
  I want to publish an agent advertisement
  So that buyers and renters can find and contact me from the listings flow

  Scenario: A non-verified user is blocked from creating an agent ad
    Given a user "wannabe" exists and is logged in
    When I open the agent ad create page
    Then the page returns 403

  Scenario: A complete active agent ad is publicly viewable on its profile page
    Given a verified agent "agent_amy" with a complete active ad in "Boulder, CO"
    When I open the agent profile page for that ad
    Then the profile page returns 200
    And the profile page shows the agent's headline
