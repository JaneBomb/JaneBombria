Feature: Keyword Search
  As a visitor
  I want to search local property listings by keyword
  So that I can quickly find relevant housing options

  Background:
    Given the following properties exist:
      | title                    | price | type      | location    |
      | Cozy Studio near Campus  | 900   | studio    | Boulder, CO |
      | Downtown Loft with View  | 1800  | apartment | Denver, CO  |

  Scenario: Search endpoint returns 200 for any keyword
    When I search by keyword "studio"
    Then the search page returns 200

  Scenario: All local properties appear in the search results
    When I visit the search page with no keyword
    Then I see "Cozy Studio near Campus" in the results
    And I see "Downtown Loft with View" in the results

  Scenario: Unknown keyword does not crash the search page
    When I search by keyword "xyznonexistent"
    Then the search page returns 200
