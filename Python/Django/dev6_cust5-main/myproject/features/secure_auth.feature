Feature: Two-Factor Authentication Setup
  As a registered user
  I want to configure two-factor authentication
  So that my account is better protected

  Background:
    Given a logged-in user "secureuser" with email "sec@test.com"

  Scenario: 2FA setup page is accessible to authenticated users
    When I visit the 2FA setup page
    Then the setup page returns 200

  Scenario: Unauthenticated users are blocked from the 2FA setup page
    Given the user logs out
    When I visit the 2FA setup page
    Then I am redirected away from the page

  Scenario: Setup page provides a TOTP secret in its context
    When I visit the 2FA setup page
    Then the response context contains a non-empty "totp_secret"

  Scenario: Submitting a wrong TOTP code shows an error
    When I submit a wrong TOTP code on the setup page
    Then the setup page shows a TOTP error

  Scenario: Sending an email code succeeds when the user has an email address
    When I request an email verification code
    Then the setup page confirms the email was sent
