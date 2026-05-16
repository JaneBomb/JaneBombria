Feature: User Registration
  As a new visitor
  I want to register an account
  So that I can post and manage roommate listings

  Scenario: Successful registration
    Given I am on the homepage
    When I submit the registration form with username "newuser" and password "StrongPassword@123"
    Then a user with username "newuser" exists in the database

  Scenario: Registration with mismatched passwords fails
    Given I am on the homepage
    When I submit the registration form with mismatched passwords
    Then no new user is created