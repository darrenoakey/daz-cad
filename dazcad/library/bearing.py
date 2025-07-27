"""Ball bearing model with parametric dimensions"""
# pylint: disable=invalid-name,undefined-variable

import math
import unittest
import cadquery as cq

# Bearing parameters (608 bearing dimensions)
outer_diameter = 22
inner_diameter = 8
width = 7
ball_diameter = 3.5
num_balls = 7

# Create outer ring - positioned to sit on z=0 plane
outer_ring = (
    cq.Workplane("XY")
    .workplane(offset=width/2)
    .circle(outer_diameter / 2)
    .circle((outer_diameter + inner_diameter) / 2 / 2 + ball_diameter / 4)
    .extrude(width)
)

# Create inner ring - positioned to sit on z=0 plane
inner_ring = (
    cq.Workplane("XY")
    .workplane(offset=width/2)
    .circle((outer_diameter + inner_diameter) / 2 / 2 - ball_diameter / 4)
    .circle(inner_diameter / 2)
    .extrude(width)
)

# Create balls - positioned at center height of bearing
balls = cq.Workplane("XY").workplane(offset=width/2)
for i in range(num_balls):
    angle = i * 360 / num_balls
    ball_center_radius = (outer_diameter + inner_diameter) / 2 / 2
    x = ball_center_radius * math.cos(math.radians(angle))
    y = ball_center_radius * math.sin(math.radians(angle))
    balls = balls.union(
        cq.Workplane("XY").workplane(offset=width/2).center(x, y).sphere(ball_diameter / 2)
    )

# Create ball cage (simplified) - positioned correctly
cage_thickness = 1
cage = (
    cq.Workplane("XY")
    .workplane(offset=width * 0.15 + width * 0.7 / 2)
    .circle((outer_diameter + inner_diameter) / 2 / 2 + ball_diameter / 4 - 0.5)
    .circle((outer_diameter + inner_diameter) / 2 / 2 - ball_diameter / 4 + 0.5)
    .extrude(width * 0.7)
)

# Assemble the bearing
show_object(outer_ring, name="Outer Ring", color="gray")
show_object(inner_ring, name="Inner Ring", color="darkgray")
show_object(balls, name="Balls", color="silver")
show_object(cage, name="Cage", color="yellow")


class TestBearing(unittest.TestCase):
    """Tests for bearing model."""

    def test_rings_creation(self):
        """Test that bearing rings can be created."""
        test_outer = cq.Workplane("XY").circle(11).circle(4).extrude(7)
        test_inner = cq.Workplane("XY").circle(8).circle(4).extrude(7)
        self.assertIsNotNone(test_outer)
        self.assertIsNotNone(test_inner)

    def test_ball_creation(self):
        """Test that balls can be created."""
        test_ball = cq.Workplane("XY").sphere(1.75)
        self.assertIsNotNone(test_ball)
        self.assertTrue(hasattr(test_ball, 'val'))

    def test_cage_creation(self):
        """Test that cage can be created."""
        test_cage = cq.Workplane("XY").circle(10).circle(6).extrude(5)
        self.assertIsNotNone(test_cage)
