"""Parametric vase with spiral pattern"""
# pylint: disable=invalid-name,undefined-variable

import math
import unittest
import cadquery as cq

# Vase parameters
base_radius = 20
top_radius = 30
height = 80
wall_thickness = 8
num_spirals = 3
spiral_depth = 1.5


def _create_vase_profile_points():
    """Create profile points for the vase shape."""
    profile_points = []
    num_points = 20

    for i in range(num_points + 1):
        t = i / num_points
        z = height * t  # Start at z=0 (build plate)
        # Smooth radius transition
        radius = base_radius + (top_radius - base_radius) * t
        profile_points.append((radius, z))

    return profile_points


def _create_outer_vase(profile_points):
    """Create the outer vase shape."""
    return cq.Workplane("XZ").polyline(profile_points) \
        .lineTo(0, height).lineTo(0, 0).close() \
        .revolve(360, (0, 0, 0), (0, 1, 0))


def _create_inner_cavity():
    """Create the inner cavity for hollowing the vase."""
    inner_points = []
    num_points = 20

    for i in range(1, num_points):  # Skip first and last points
        t = i / num_points
        z = height * t
        radius = base_radius + (top_radius - base_radius) * t - wall_thickness
        if radius > 0:  # Ensure positive radius
            inner_points.append((radius, z))

    if inner_points:
        return cq.Workplane("XZ").polyline(inner_points) \
            .lineTo(0, inner_points[-1][1]).lineTo(0, inner_points[0][1]).close() \
            .revolve(360, (0, 0, 0), (0, 1, 0))
    return None


def _add_spiral_texture(workpiece):
    """Add spiral texture to the vase using cuts."""
    result_vase = workpiece

    for i in range(num_spirals * 4):
        angle = (360 / (num_spirals * 4)) * i
        spiral_height = height * 0.8  # Don't go all the way to top

        # Create helix points
        helix_points = _create_helix_points(angle, spiral_height)

        # Create small cylindrical cuts for texture
        result_vase = _apply_texture_cuts(result_vase, helix_points)

    return result_vase


def _create_helix_points(angle, spiral_height):
    """Create points for the helical spiral pattern."""
    helix_points = []

    for j in range(10):
        t = j / 9
        z = spiral_height * t + height * 0.1  # Start slightly above base
        radius = base_radius + (top_radius - base_radius) * t + spiral_depth
        x = radius * math.cos(math.radians(angle + 360 * t))
        y = radius * math.sin(math.radians(angle + 360 * t))
        helix_points.append((x, y, z))

    return helix_points


def _apply_texture_cuts(workpiece, helix_points):
    """Apply texture cuts to the vase at the given points."""
    result_vase = workpiece

    for point in helix_points[::2]:  # Every other point
        try:
            cut_cyl = cq.Workplane("XY").workplane(offset=point[2]) \
                .moveTo(point[0], point[1]) \
                .circle(spiral_depth * 0.3).extrude(wall_thickness * 0.5)
            result_vase = result_vase.cut(cut_cyl)
        except Exception:  # pylint: disable=broad-exception-caught
            pass  # Skip if cut fails

    return result_vase


def create_vase():
    """Create a vase with spiral texture using a more robust approach."""
    # Create basic vase profile
    profile_points = _create_vase_profile_points()

    # Create outer vase shape
    outer_vase = _create_outer_vase(profile_points)

    # Create inner cavity and hollow out the vase
    inner_cavity = _create_inner_cavity()
    if inner_cavity:
        result_vase = outer_vase.cut(inner_cavity)
    else:
        result_vase = outer_vase

    # Add spiral texture
    result_vase = _add_spiral_texture(result_vase)

    return result_vase


# Create the vase
vase = create_vase()

show_object(vase, name="Spiral Vase", color="lightgreen")


class TestVase(unittest.TestCase):
    """Tests for vase model."""

    def test_vase_creation(self):
        """Test that vase can be created without errors."""
        test_vase = create_vase()
        self.assertIsNotNone(test_vase)

    def test_profile_points_generation(self):
        """Test that profile points can be generated."""
        test_points = _create_vase_profile_points()
        self.assertEqual(len(test_points), 21)
        self.assertGreaterEqual(test_points[0][1], 0)  # First point at z=0 or above

    def test_polyline_creation(self):
        """Test that polyline can be created."""
        test_points = [(20, 0), (25, 40), (30, 80)]
        test_line = cq.Workplane("XZ").polyline(test_points)
        self.assertIsNotNone(test_line)

    def test_revolve_operation(self):
        """Test that revolve operation works."""
        test_points = [(20, 0), (25, 40), (30, 80)]
        test_shape = cq.Workplane("XZ").polyline(test_points) \
            .lineTo(0, 80).lineTo(0, 0).close() \
            .revolve(360, (0, 0, 0), (0, 1, 0))
        self.assertIsNotNone(test_shape)

    def test_parameters_valid(self):
        """Test that vase parameters are valid."""
        self.assertGreater(base_radius, 0)
        self.assertGreater(top_radius, 0)
        self.assertGreater(height, 0)
        self.assertGreater(wall_thickness, 0)
        self.assertLess(wall_thickness, base_radius)

    def test_helix_points_creation(self):
        """Test that helix points can be created."""
        points = _create_helix_points(0, 60)
        self.assertEqual(len(points), 10)
        self.assertIsInstance(points[0], tuple)
        self.assertEqual(len(points[0]), 3)
