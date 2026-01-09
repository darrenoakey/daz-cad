// Open Box - A tray with walls on three sides
// 80x40mm base, 2mm thick walls, 40mm wall height

// Create outer shell: full box with base + wall height
const outer = new Workplane("XY").box(80, 40, 42);

// Create inner void to hollow out
// - 76mm wide (2mm walls on left and right)
// - 38mm deep (2mm wall on back, open on front)
// - 40mm tall, starting 2mm up (leaving 2mm thick base)
// Translate: Y+1 shifts it toward front, Z+2 leaves the base
const inner = new Workplane("XY")
    .box(76, 38, 40)
    .translate(0, 1, 2);

// Cut out the interior to create the shell
const shell = outer.cut(inner);

// Apply fillet to all edges for a smooth look
// Using 0.4mm radius (small enough for complex shell geometry)
const result = shell.fillet(0.4).color("#3498db");

result;
