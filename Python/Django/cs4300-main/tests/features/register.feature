Feature: register

  Scenario: register a new account
     Given we have a register page
      When we enter a <username> and <password> and click the "Sign Up" button
      Then we have a newly created account