"""Parametric assembly of interlocking parts"""
# pylint: disable=invalid-name,undefined-variable,no-value-for-parameter

import unittest
import cadquery as cq

# Parameters
cube_size = 20
slot_width = 4
slot_depth = 10
gap = 0.2  # Clearance for fit

# Create first part with slot - positioned on z=0 plane
part1 = cq.Workplane("XY").workplane(offset=cube_size/2).box(cube_size, cube_size, cube_size)
part1 = part1.faces(">Y").workplane() \
    .rect(slot_width + gap, cube_size) \
    .cutBlind(-slot_depth)

# Create second part with tab - positioned on z=0 plane
part2 = cq.Workplane("XY").workplane(offset=cube_size/2).box(cube_size, cube_size, cube_size)
tab = cq.Workplane("XY").workplane(offset=cube_size/2).center(0, cube_size/2) \
    .rect(slot_width, slot_depth).extrude(cube_size)
part2 = part2.union(tab)

# Position the parts
assembly = cq.Assembly()
assembly.add(part1, name="part1", color="lightblue")
assembly.add(part2, name="part2", color="lightyellow",
             loc=cq.Location((cube_size + 5, 0, 0)))

# Show the assembly
show_object(assembly, name="Interlocking Parts")

# Also show how they fit together
assembled = part1.union(
    part2.translate((0, cube_size - slot_depth + gap/2, 0))
)
show_object(assembled, name="Assembled",
            color="lightgreen")


class TestAssembly(unittest.TestCase):
    """Tests for assembly model."""

    def test_parts_creation(self):
        """Test that parts can be created."""
        test_part1 = cq.Workplane("XY").workplane(offset=10).box(20, 20, 20)
        test_part2 = cq.Workplane("XY").workplane(offset=10).box(20, 20, 20)
        self.assertIsNotNone(test_part1)
        self.assertIsNotNone(test_part2)

    def test_assembly_creation(self):
        """Test that assembly can be created."""
        test_assembly = cq.Assembly()
        test_part = cq.Workplane("XY").workplane(offset=5).box(10, 10, 10)
        test_assembly.add(test_part, name="test")
        self.assertIsNotNone(test_assembly)
        self.assertEqual(len(test_assembly.children), 1)
