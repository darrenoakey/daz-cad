Feature: Cut-plane joinery
  A maker splits a solid on an arbitrary construction plane and applies a printable connector without losing the editable source model.

  Scenario: Reach the CAD editor from the application root
    Given the CAD application is running
    When I browse to "/"
    Then the CAD editor is visible
    And the editor toolbar contains "Cut & Join"

  Scenario: Open the cut-plane joinery panel
    Given the CAD editor is visible
    When I click "Cut & Join" in the toolbar
    Then the Cut & Join panel is visible
    And the panel shows a plane origin control
    And the panel shows a plane normal control
    And the panel shows a plane up-vector control

  Scenario Outline: Choose every connector mechanism
    Given the Cut & Join panel is visible
    When I choose the "<method>" connector method
    Then the selected method is "<method>"
    And the panel describes the "<method>" mechanism

    Examples:
      | method          |
      | snap-key        |
      | butterfly-key   |
      | dovetail        |
      | jigsaw          |
      | cantilever-snap |
      | snap-dowel      |
      | cross-key       |
      | scarf-wedge     |
      | bayonet         |
      | bridge-clip     |

  Scenario: Adjust connector dimensions and clearance
    Given the Cut & Join panel is visible
    When I set connector size to "8"
    And I set connector depth to "6"
    And I set connector wall thickness to "1.2"
    And I set connector clearance to "0.2"
    And I set connector count to "2"
    Then the panel displays size "8"
    And the panel displays depth "6"
    And the panel displays wall thickness "1.2"
    And the panel displays clearance "0.2"
    And the panel displays connector count "2"

  Scenario: Manipulate an oblique cut plane
    Given the Cut & Join panel is visible
    When I set the plane origin to "0, 0, 10"
    And I set the plane normal to "1, 1, 1"
    And I set the plane up-vector to "0, 0, 1"
    Then the joinery preview shows an oblique cut plane

  Scenario: Position the plane by dragging the preview
    Given the Cut & Join panel is visible
    When I Shift-drag the cyan cut plane in the 3D preview
    Then the plane origin controls show the dragged plane position
    And the panel reports the shifted plane preview

  Scenario: Apply joinery through the editor code wrapper
    Given the Cut & Join panel is visible
    When I choose the "dovetail" connector method
    And I click "Apply Cut & Join"
    Then the editor script contains "splitAndJoin"
    And the 3D preview shows separated joined parts
    And the source model expression remains in the editor script

  Scenario: Reapply joinery without nesting generated wrappers
    Given the Cut & Join panel is visible
    When I click "Apply Cut & Join"
    And I open Cut & Join again
    And I choose the "snap-key" connector method
    And I click "Apply Cut & Join"
    Then the editor script contains one Cut/Join generated source block
    And the 3D preview shows the re-applied connector

  Scenario: Preserve an editable script after invalid generation
    Given the Cut & Join panel is visible
    When I enter an invalid plane normal "0, 0, 0"
    And I click "Apply Cut & Join"
    Then the panel displays a joinery validation error
    And the editor script remains unchanged

  Scenario: Export the joined print layout
    Given the Cut & Join panel is visible
    When I click "Apply Cut & Join"
    And I click "Export 3MF"
    Then a 3MF download is offered
    And the print preview keeps parts separated
