Feature: File browser with thumbnails and sorting
  A maker opens a wide, scrollable file browser from the editor header to find a model by
  thumbnail, natural name order, recency, or search, without ever re-rendering models that
  are only being browsed.

  Scenario: Reach the CAD editor from the application root
    Given the CAD application is running
    When I browse to "/"
    Then the CAD editor is visible
    And the editor header contains a file selector button

  Scenario: Open the file browser panel
    Given the CAD editor is visible
    When I click the file selector button
    Then the file browser panel is visible
    And the file browser panel is wide and scrollable
    And the file browser offers sorting by "recent", "name", and "name-desc"
    And the file browser offers a filename search field
    And the file browser shows a file count

  Scenario: Example models without previews invite a render
    Given the file browser panel is visible
    Then example models without a cached preview show "Render to preview"
    And example model cards without a cached preview show no thumbnail image

  Scenario: Create a new model from the browser
    Given the file browser panel is visible
    When I create a new model "test-fb-{uuid}.js"
    Then the editor loads "test-fb-{uuid}.js"
    And the file browser panel closes

  Scenario: A successful render caches a transparent thumbnail
    Given the CAD editor is visible
    When I create a new model "test-fb-{uuid}.js"
    And I change the source from a box to a cylinder
    And the model finishes rendering
    And I open the file browser
    Then the "test-fb-{uuid}.js" card shows a loaded thumbnail image
    And the thumbnail is a real transparent PNG

  Scenario: Editing a model refreshes its cached thumbnail once
    Given a model "test-fb-{uuid}.js" has a cached thumbnail
    When I change the source from a box to a cylinder
    Then exactly one new thumbnail is cached for "test-fb-{uuid}.js"

  Scenario: A failed render keeps the last saved preview and source
    Given a model "test-fb-{uuid}.js" has a cached thumbnail
    When I enter an invalid source
    Then the editor reports a render error
    And the "test-fb-{uuid}.js" card still shows its cached thumbnail
    When I reload the page
    Then the editor shows the last saved source

  Scenario: Reopening an unchanged model reuses its cached preview
    Given models "test-fb-{uuid}-a.js" and "test-fb-{uuid}-b.js" have cached thumbnails
    When I open "test-fb-{uuid}-b.js" from its card
    And I reopen "test-fb-{uuid}-a.js" from its card
    Then no new render or thumbnail save is made for "test-fb-{uuid}-a.js"

  Scenario: Sort by name uses natural alphabetical order
    Given the file browser panel is visible
    When I create models "test-fb-{uuid}-1.js", "test-fb-{uuid}-2.js", and "test-fb-{uuid}-10.js"
    And I sort the file browser by "name"
    Then the file browser lists "test-fb-{uuid}-2.js" before "test-fb-{uuid}-10.js"

  Scenario: Reverse name sort lists Z to A
    Given the file browser panel is visible
    When I create models "test-fb-{uuid}-1.js", "test-fb-{uuid}-2.js", and "test-fb-{uuid}-10.js"
    And I sort the file browser by "name-desc"
    Then the file browser lists "test-fb-{uuid}-10.js" before "test-fb-{uuid}-1.js"

  Scenario: Sort by recent lists newest modified first
    Given the file browser panel is visible
    When I create models "test-fb-{uuid}-1.js", "test-fb-{uuid}-2.js", and "test-fb-{uuid}-10.js"
    And I edit and save "test-fb-{uuid}-1.js" so it is the newest
    And I sort the file browser by "recent"
    Then the file browser lists "test-fb-{uuid}-1.js" first

  Scenario: Sort preference persists across reload
    Given the file browser panel is visible
    When I sort the file browser by "name-desc"
    And I reload the page
    Then the file browser still sorts by "name-desc"

  Scenario: Search filters filenames and updates the count
    Given the file browser panel is visible
    When I create a model "test-fb-{uuid}.js"
    And I search the file browser for "test-fb-{uuid}"
    Then only cards matching "test-fb-{uuid}" are visible
    And the file count matches the visible cards
    When I clear the file browser search
    Then the full model list is visible again

  Scenario: Escape closes the panel and refocuses the selector
    Given the file browser panel is visible
    When I press Escape
    Then the file browser panel closes
    And the file selector button has focus

  Scenario: Clicking outside closes the panel
    Given the file browser panel is visible
    When I click the editor outside the panel
    Then the file browser panel closes

  Scenario: Selecting a card loads the model and persists across reload
    Given the file browser panel is visible
    When I create a model "test-fb-{uuid}.js"
    And I open the file browser
    And I click the "test-fb-{uuid}.js" card
    Then the editor loads "test-fb-{uuid}.js"
    And the file browser panel closes
    When I reload the page
    Then the editor loads "test-fb-{uuid}.js"

  Scenario: Browsing and sorting never re-render models
    Given the file browser panel is visible
    When I record network requests
    And I sort the file browser by "name"
    And I sort the file browser by "name-desc"
    And I sort the file browser by "recent"
    And I search the file browser for "test-fb"
    Then no render or thumbnail save requests were made
