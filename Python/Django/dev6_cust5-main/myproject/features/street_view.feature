Feature: Street View Deeplink
  As a visitor browsing properties on the map
  I want each marker to expose a Google Street View deeplink
  So that I can preview the actual street before reaching out

  Scenario: Map page renders the Street View deeplink template
    Given the Rentcast API returns a property at "100 Pearl St, Boulder, CO"
    When I search the map with city "Boulder" and state "CO"
    Then the map page returns 200
    And the map page contains the Street View deeplink template

  Scenario: Each property in the map context carries coords for Street View
    Given the Rentcast API returns a property at "200 Walnut St, Boulder, CO"
    When I search the map with city "Boulder" and state "CO"
    Then every property in the map context has coordinates
