Feature: Instant Messaging
  As a logged-in user
  I want to message roommate posters and see my conversations
  So that I can coordinate about available rooms

  Background:
    Given a user "sahana" exists and is logged in

  Scenario: Authenticated user can view their inbox
    When I visit the chat inbox
    Then the inbox returns 200

  Scenario: Unauthenticated user is redirected from the inbox
    Given the user logs out
    When I visit the chat inbox
    Then I am redirected away from the page

  Scenario: User can open a chat room for a posting
    Given a roommate post exists for "sahana"
    When I open the chat room for the posting
    Then the chat room returns 200

  Scenario: A message saved to the database appears in the inbox count
    Given a roommate post exists for "sahana"
    And a message "Hi, is the room still available?" is sent on the posting
    When I visit the chat inbox
    Then the inbox shows 1 message for that post
