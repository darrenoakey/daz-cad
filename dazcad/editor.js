        value: `import cadquery as cq

# Create an assembly for 3D printing - positioned to sit on build plate (z=0)
asm = cq.Assembly()

# Create boxes that sit on the build plate
b1 = cq.Workplane("XY").workplane(offset=2.5).box(5, 5, 5)
asm.add(b1, name="Red", color=cq.Color("red"))

b2 = cq.Workplane("XY").workplane(offset=2.5).box(5, 5, 5) 
asm.add(b2, name="Green", loc=cq.Location((10, 0, 0)), color=cq.Color("green"))

show_object(asm, "Test")`