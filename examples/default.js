// CAD Example: Assembly with three colored parts
// Edit this code to see live preview on the right!

// Red cube with hole and chamfered edges
const cube = new Workplane("XY")
    .box(20, 20, 20)
    .hole(8)
    .chamfer(2)
    .color("#e74c3c");

// Green cylinder offset to the right
const cylinder = new Workplane("XY")
    .cylinder(8, 25)
    .translate(30, 0, 0)
    .color("#2ecc71");

// Blue smaller cube offset to the left
const smallCube = new Workplane("XY")
    .box(12, 12, 15)
    .translate(-25, 0, 0)
    .color("#3498db");

// Create assembly with all parts
const result = new Assembly()
    .add(cube)
    .add(cylinder)
    .add(smallCube);

result;
