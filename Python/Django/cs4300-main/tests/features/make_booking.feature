Feature: make booking
  Scenario: make a booking for a movie
     Given we have a booking page
      When we click an available seat on the seat grid
      Then we can confirm the booking for the seat
