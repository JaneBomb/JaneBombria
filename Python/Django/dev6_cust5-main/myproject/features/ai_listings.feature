Feature: AI Curated Listings
  As a signed-in user
  I want the AI agent to recommend listings based on my search
  So that I can surface the best matches for my filters quickly

  Scenario: The AI agent returns curated picks for a signed-in user's search
    Given a user "alice" exists and is logged in
    And the AI agent recommends a property at "100 Elm St, Boulder, CO"
    When I request AI recommendations for city "Boulder" and state "CO"
    Then the AI agent response is OK
    And the AI picks include an address containing "Elm St"
