// Tab & Slot Demo - Snap-fit connectors on panel faces
// Shows addTab() (male) and addSlot() (female) side by side

const THICKNESS = 6.6;  // Panel thickness -> cylinder diameter = 4mm
const WIDTH = 20;
const HEIGHT = 30;
const NECK = 1.3;

// Male panel: tab extends from +X face
const male = new Workplane("XY")
    .box(THICKNESS, WIDTH, HEIGHT)
    .faces(">X")
    .addTab({ neckThickness: NECK });

// Female panel: slot cut into -X face (which faces the male)
const female = new Workplane("XY")
    .box(THICKNESS, WIDTH, HEIGHT)
    .faces("<X")
    .addSlot({ neckThickness: NECK, tolerance: 0.1 });

const assembly = new Assembly();
assembly.add(male.translate(-10, 0, 0).color("#3498db"));
assembly.add(female.translate(10, 0, 0).color("#e74c3c"));

const result = assembly;
result;
