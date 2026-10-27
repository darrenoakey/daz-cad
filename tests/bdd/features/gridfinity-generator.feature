Feature: Build-area-aware Gridfinity baseplate generator
  A maker creates one complete, connected set of printable Gridfinity baseplate segments from one generator form.

  Scenario: Reach the generator menu from the CAD editor
    Given the CAD application is running
    When I browse to "/"
    Then the CAD editor is visible
    And the editor toolbar contains "Generators"

  Scenario: Open the Gridfinity baseplate generator
    Given the CAD editor is visible
    When I click "Generators" in the toolbar
    Then the Generators panel is visible
    And the generator menu offers "Segmented Gridfinity baseplate"
    And the panel shows X and Y grid-unit controls
    And the panel shows the printer build-area control
    And mouse ears and snap connectors are enabled by default

  Scenario: Plan balanced segments and reject invalid dimensions
    Given the Generators panel is visible
    When I set the Gridfinity width to "5" units
    And I set the Gridfinity depth to "6" units
    And I set the printer build area to "200" mm
    Then the panel reports four balanced segments with remainder units distributed evenly
    And the plan includes five seam connectors and three spare connectors
    When I set the Gridfinity width to "0" units
    Then the panel shows a positive-integer validation error

  Scenario: Generate balanced baseplate segments and export every part
    Given the Generators panel is visible
    When I set the Gridfinity width to "2" units
    And I set the Gridfinity depth to "1" unit
    And I set the printer build area to "100" mm
    Then the panel reports two balanced baseplate segments
    When I click "Generate baseplate"
    Then the editor script calls the segmented Gridfinity baseplate generator
    And the 3D preview shows all generated parts
    When I click the "3MF" export button
    Then one 3MF download contains both baseplate segments and their snap connectors
