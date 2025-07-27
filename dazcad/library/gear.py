"""Parametric gear example for DazCAD"""
# pylint: disable=invalid-name,undefined-variable

import math
import unittest
import cadquery as cq

# Gear parameters
module = 2.0  # Gear module (tooth size)
num_teeth = 20
pressure_angle = 20  # degrees
thickness = 5

# Calculate dimensions
pitch_diameter = module * num_teeth
base_diameter = pitch_diameter * math.cos(math.radians(pressure_angle))
addendum = module
dedendum = 1.25 * module
outer_diameter = pitch_diameter + 2 * addendum
root_diameter = pitch_diameter - 2 * dedendum

# Create gear blank - positioned to sit on z=0 plane
gear = cq.Workplane("XY").circle(outer_diameter / 2).extrude(thickness)

# Add center hole
gear = gear.faces(">Z").workplane().circle(5).cutThruAll()

# Create tooth profile (simplified)
tooth_angle = 360 / num_teeth
for i in range(num_teeth):
    angle = i * tooth_angle
    gear = gear.rotate((0, 0, 0), (0, 0, 1), angle)

    # Simplified tooth shape
    gear = gear.faces(">Z").workplane() \
        .center(pitch_diameter / 2, 0) \
        .rect(module * 2, module * 3) \
        .cutThruAll()

    gear = gear.rotate((0, 0, 0), (0, 0, 1), -angle)

show_object(gear, name="Gear", color="orange")


class TestGear(unittest.TestCase):
    """Tests for gear model."""

    def test_gear_blank_creation(self):
        """Test that gear blank can be created."""
        test_gear = cq.Workplane("XY").circle(20).extrude(5)
        self.assertIsNotNone(test_gear)
        self.assertTrue(hasattr(test_gear, 'val'))

    def test_center_hole_creation(self):
        """Test that center hole can be created."""
        test_gear = cq.Workplane("XY").circle(20).extrude(5)
        test_gear = test_gear.faces(">Z").workplane().circle(5).cutThruAll()
        self.assertIsNotNone(test_gear)

    def test_gear_parameters(self):
        """Test gear parameter calculations."""
        test_module = 2.0
        test_teeth = 20
        test_pitch_diameter = test_module * test_teeth
        self.assertEqual(test_pitch_diameter, 40.0)

    def test_tooth_cutting(self):
        """Test that tooth cuts can be made."""
        test_gear = cq.Workplane("XY").circle(20).extrude(5)
        test_gear = test_gear.faces(">Z").workplane().center(15, 0).rect(4, 6).cutThruAll()
        self.assertIsNotNone(test_gear)
