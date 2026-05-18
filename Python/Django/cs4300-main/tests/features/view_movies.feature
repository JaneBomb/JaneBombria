Feature: view movies
  Scenario: view all current movies
     Given we have a home page
      When we click the "All Movies" button
      Then we get a list of all movies