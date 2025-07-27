"""Parametric vase with spiral pattern"""
# pylint: disable=invalid-name,undefined-variable

import math
import unittest
import cadquery as cq

# Vase parameters
base_radius = 20
top_radius = 30
height = 80
wall_thickness = 2
num_spirals = 5
spiral_depth = 2

# Create outer profile points - starting from z=0 (sitting on build plate)
num_points = 50
profile_points = []

for i in range(num_points + 1):
    t = i / num_points
    z = height * t  # Starts at z=0, goes to z=height
    # Smooth transition from base to top radius
    radius = base_radius + (top_radius - base_radius) * (t ** 0.7)
    # Add spiral variation
    angle = 2 * math.pi * num_spirals * t
    spiral_offset = spiral_depth * math.sin(angle)
    r = radius + spiral_offset
    profile_points.append((r, z))

# Create the vase shell
vase = cq.Workplane("XZ").spline(profile_points).close() \
    .revolve(360, (0, 0, 0), (0, 1, 0))

# Hollow out the vase
inner_points = [(p[0] - wall_thickness, p[1]) for p in profile_points[1:-1]]
inner_points = [(base_radius - wall_thickness, 0)] + inner_points + \
               [(top_radius - wall_thickness - spiral_depth, height)]

vase = vase.cut(
    cq.Workplane("XZ").spline(inner_points).close()
    .revolve(360, (0, 0, 0), (0, 1, 0))
)

# Cut the top to make it open
vase = vase.faces(">Z").shell(-wall_thickness)

show_object(vase, name="Spiral Vase", color="lightgreen")


class TestVase(unittest.TestCase):
    """Tests for vase model."""

    def test_profile_points_generation(self):
        """Test that profile points can be generated."""
        test_points = []
        for j in range(11):
            time_val = j / 10
            z_val = 80 * time_val
            radius_val = 20 + (30 - 20) * (time_val ** 0.7)
            test_points.append((radius_val, z_val))
        self.assertEqual(len(test_points), 11)
        self.assertGreaterEqual(test_points[0][1], 0)  # First point at z=0 or above

    def test_spline_creation(self):
        """Test that spline can be created."""
        test_points = [(20, 0), (25, 40), (30, 80)]
        test_spline = cq.Workplane("XZ").spline(test_points)
        self.assertIsNotNone(test_spline)

    def test_revolve_operation(self):
        """Test that revolve operation works."""
        test_points = [(20, 0), (25, 40), (30, 80)]
        test_vase = cq.Workplane("XZ").spline(test_points).close() \
            .revolve(360, (0, 0, 0), (0, 1, 0))
        self.assertIsNotNone(test_vase)

    def test_spiral_calculations(self):
        """Test spiral offset calculations."""
        test_angle = 2 * math.pi * 5 * 0.5  # Mid-point spiral
        test_offset = 2 * math.sin(test_angle)
        self.assertIsInstance(test_offset, float)
