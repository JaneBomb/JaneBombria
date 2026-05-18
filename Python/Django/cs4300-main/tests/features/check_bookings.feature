Feature: check bookings
  Scenario: check all bookings made, including past bookings
     Given we have a user account
      When we click the account button
      Then we have a list of all bookings made