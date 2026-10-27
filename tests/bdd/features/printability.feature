Feature: FDM printability optimization
  A maker applies conservative printability rules to editable CAD source while protecting mating edges.

  Scenario: Reach printability controls from the application root
    Given the CAD application is running
    When I browse to "/"
    Then the CAD editor is visible
    And the editor toolbar contains "Print for FDM"

  Scenario: Open the printability panel
    Given the CAD editor is visible
    When I click "Print for FDM" in the toolbar
    Then the Printability panel is visible
    And the panel shows vertical fillet and base chamfer controls
    And the panel explains mating-edge preservation

  Scenario: Apply deterministic printability transforms
    Given the Printability panel is visible
    When I click "Apply Printability"
    Then the editor script contains "optimizeForPrinting"
    And the editor script contains comments describing fillets and chamfers
    And the 3D preview shows the optimized solid
    And the Worker Console reports the printability changes

  Scenario: Preserve explicitly identified mating edges
    Given the Printability panel is visible
    When I preserve mating edges "<X and <Y"
    And I click "Apply Printability"
    Then the generated settings contain the mating-edge selector
    And the source model expression remains in the editor script

  Scenario: Undo printability in one editor step
    Given the 3D preview shows the optimized solid
    When I undo the Printability source edit once
    Then the exact original model source is restored
    When I redo the Printability source edit
    Then the editor script contains one Printability generated source block

  Scenario: Reapply printability without nesting generated wrappers
    Given the Printability panel is visible
    When I click "Apply Printability"
    And I open Print for FDM again
    And I click "Apply Printability"
    Then the editor script contains one Printability generated source block

  Scenario: Preserve editable source after invalid settings
    Given the Printability panel is visible
    When I enter a vertical fillet radius of "-1"
    And I click "Apply Printability"
    Then the panel displays a printability validation error
    And the editor script remains unchanged

  Scenario: Optimize assembly parts and preserve incompatible geometry
    Given the 3D preview shows the optimized solid
    When I enter a multi-part Assembly model with an incompatible first part
    And I open Print for FDM again
    And I click "Apply Printability"
    Then every compatible assembly solid is optimized independently
    And the incompatible part remains unchanged with a numbered warning
    And the generated source retains the Assembly, colors, and print settings
    And the Worker Console identifies the transformed and unchanged part numbers
