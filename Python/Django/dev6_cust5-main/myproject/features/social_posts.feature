Feature: Social Posts Feed
  As a user browsing the live listings feed
  I want open roommate posts to be serialized into the social feed shape
  So that they render correctly for every viewer in real time

  Scenario: An open roommate post is serialized for the social feed
    Given a user "alice" exists and is logged in
    And a roommate post exists for "alice"
    When I serialize the post for the social feed
    Then the serialized listing has status "open"
    And the serialized listing has rent 1000
    And the serialized listing name is "alice"
