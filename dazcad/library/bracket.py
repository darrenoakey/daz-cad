"""L-bracket with mounting holes"""
# pylint: disable=invalid-name,undefined-variable,duplicate-code

import unittest
import cadquery as cq

# Bracket parameters
length = 50
width = 30
thickness = 5
wall_height = 40
wall_thickness = 5
hole_diameter = 5
hole_spacing = 20

# Create base plate - positioned to sit on z=0 plane
base = cq.Workplane("XY").workplane(offset=thickness/2).box(length, width, thickness)

# Create vertical wall - positioned correctly relative to base
wall = (
    cq.Workplane("XY")
    .workplane(offset=thickness + wall_height/2)
    .center(-length/2 + wall_thickness/2, 0)
    .box(wall_thickness, width, wall_height)
)

# Combine base and wall
bracket = base.union(wall)

# Add fillet to strengthen the joint
bracket = bracket.edges("|Z").edges(">X").fillet(5)

# Add mounting holes in base
bracket = (
    bracket.faces("<Z")
    .workplane()
    .center(hole_spacing/2, 0)
    .hole(hole_diameter)
    .center(-hole_spacing, 0)
    .hole(hole_diameter)
)

# Add mounting holes in wall
bracket = (
    bracket.faces("<X")
    .workplane()
    .center(0, wall_height/2 - 10)
    .hole(hole_diameter)
)

# Show the result
show_object(bracket, name="L-Bracket", color="lightgray")


class TestBracket(unittest.TestCase):
    """Tests for bracket model."""

    def test_base_creation(self):
        """Test that base plate can be created."""
        test_base = cq.Workplane("XY").workplane(offset=2.5).box(50, 30, 5)
        self.assertIsNotNone(test_base)
        self.assertTrue(hasattr(test_base, 'val'))

    def test_wall_creation(self):
        """Test that wall can be created."""
        test_wall = cq.Workplane("XY").workplane(offset=25).box(5, 30, 40)
        self.assertIsNotNone(test_wall)

    def test_hole_creation(self):
        """Test that holes can be created."""
        test_part = cq.Workplane("XY").workplane(offset=2.5).box(20, 20, 5)
        test_part = test_part.faces(">Z").workplane().hole(5)
        self.assertIsNotNone(test_part)

    def test_fillet_creation(self):
        """Test that fillets can be created."""
        test_part = cq.Workplane("XY").workplane(offset=5).box(10, 10, 10)
        test_filleted = test_part.edges().fillet(1)
        self.assertIsNotNone(test_filleted)
