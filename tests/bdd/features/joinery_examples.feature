Feature: Interesting connector demonstration projects
  Scenario: Reach the demonstration project picker
    Given the CAD application is running
    When I browse to "/"
    And I open the model selector
    Then the model selector lists the ten connector demonstration projects

  Scenario Outline: Open and export a connector demonstration
    Given the model selector lists the ten connector demonstration projects
    When I choose "<project>"
    Then the filename display shows "<project>"
    And the interesting sample object finishes rendering
    And the Properties panel shows VIEW set to "1"
    And the 3MF export control is enabled
    When I download the 3MF
    Then a 3MF download is offered for the displayed project

    Examples:
      | project                          |
      | joinery_01_robot_chest.js         |
      | joinery_02_mountain_sculpture.js   |
      | joinery_03_cable_comb.js           |
      | joinery_04_arch_bridge.js         |
      | joinery_05_hex_lantern.js          |
      | joinery_06_rocket_pencil_pot.js    |
      | joinery_07_toolbox_handle.js      |
      | joinery_08_bridge_girder.js        |
      | joinery_09_twist_canister.js      |
      | joinery_10_picture_frame.js       |
