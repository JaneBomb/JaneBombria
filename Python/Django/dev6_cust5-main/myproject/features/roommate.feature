Feature: Roommate Postings
  As a logged-in user
  I want to create, view, close, and delete roommate posts
  So that I can find or offer housing

  Background:
    Given a user "poster" exists and is logged in

  Scenario: Create a roommate post
    When I submit a roommate post with message "Need roommate near campus"
    Then the post "Need roommate near campus" appears on the listings page

  Scenario: Close a roommate post
    Given a roommate post exists for "poster"
    When I close the post
    Then the post status is "closed"

  Scenario: Delete a roommate post
    Given a roommate post exists for "poster"
    When I delete the post
    Then the post no longer exists in the database

  Scenario: Non-owner cannot delete a post
    Given a roommate post exists for "poster"
    And user "other" is logged in
    When "other" tries to delete the post
    Then the post still exists in the database