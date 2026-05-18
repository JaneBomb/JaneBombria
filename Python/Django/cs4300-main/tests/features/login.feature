Feature: login
  Scenario Outline: login to an account
     Given we have a login page
      And we have an existing user
      When we enter the <username> and <password> and click the "Sign In" button
      Then the <username> will appear next to the login button
