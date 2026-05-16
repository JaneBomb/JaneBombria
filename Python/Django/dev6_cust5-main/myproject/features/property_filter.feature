Feature: Property Map Search
  As a visitor
  I want to search for rental properties by city and state on the map
  So that I can see available listings near me

  Scenario: Map page loads with no search parameters
    Given I am on the homepage
    When I visit the map page
    Then the map page returns 200

  Scenario: Searching with city and state calls the API and renders markers
    Given the Rentcast API returns a property at "100 Elm St, Boulder, CO"
    When I search the map with city "Boulder" and state "CO"
    Then the map page returns 200
    And the map context has at least 1 property

  Scenario: Searching without a state does not call the API
    When I search the map with city "Boulder" and no state
    Then the map page returns 200
    And the map context has 0 properties

  Scenario: Applying a budget filter passes price bounds to the API
    Given the Rentcast API returns a property at "200 Oak Ave, Denver, CO"
    When I search the map with city "Denver" state "CO" and budget "500-1500"
    Then the map page returns 200
