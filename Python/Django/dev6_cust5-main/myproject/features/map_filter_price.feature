Feature: Map Filter By Price
  As a visitor
  I want to apply a price range to my map search
  So that the property API only returns listings within my budget

  Scenario: Map search forwards the price range to the property API
    Given the Rentcast API returns a property at "100 Oak St, Denver, CO"
    When I submit a map search with price range "500-1500" for "Denver, CO"
    Then the map page returns 200
    And the property API was called with min_price 500 and max_price 1500
