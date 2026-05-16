Feature: Property Map
  As a visitor
  I want to see rental properties displayed on an interactive map
  So that I can visually explore housing options by location

  Scenario: Map page loads with no search input
    Given I am on the homepage
    When I visit the map page
    Then the map page returns 200

  Scenario: Searching by city and state displays properties on the map
    Given the Rentcast API returns a property at "100 Elm St, Boulder, CO"
    When I search the map with city "Boulder" and state "CO"
    Then the map page returns 200
    And the map context has at least 1 property

  Scenario: Each property on the map has latitude and longitude
    Given the Rentcast API returns a property at "100 Elm St, Boulder, CO"
    When I search the map with city "Boulder" and state "CO"
    Then every property in the map context has coordinates

  Scenario: Searching without a state shows no API results
    When I search the map with city "Boulder" and no state
    Then the map page returns 200
    And the map context has 0 properties

  Scenario: A budget filter is forwarded to the API
    Given the Rentcast API returns a property at "200 Oak Ave, Denver, CO"
    When I search the map with city "Denver" state "CO" and budget "500-1500"
    Then the map page returns 200

  Scenario: A property type filter is forwarded to the API
    Given the Rentcast API returns a property at "300 Pine Rd, Denver, CO"
    When I search the map with city "Denver" state "CO" and type "apartment"
    Then the map page returns 200

  Scenario: Local DB properties with coordinates show on the map when no search is made
    Given a local property with coordinates exists
    When I visit the map page
    Then the map context has at least 1 property
