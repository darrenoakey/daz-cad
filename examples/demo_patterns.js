// Demo: Unified Pattern Cutting API - 4x4 Grid Showcase
//
// Shows 16 different pattern variations in a grid layout.
// Each box demonstrates a different shape/option combination.

const SIZE = 30;      // Box size
const HEIGHT = 6;     // Box height
const GAP = 35;       // Gap between boxes

// Helper function to create a box ready for pattern cutting
const makeBox = () => new Workplane("XY").box(SIZE, SIZE, HEIGHT).faces(">Z");

// Calculate offsets to center the 4x4 grid around origin
const offset = (GAP * 3) / 2;

// Row 1: Basic shapes
const box1 = makeBox()
    .cutPattern({ shape: 'line', width: 1, spacing: 3, depth: 1, border: 3 })
    .translate(-offset, -offset, 0).color("red");

const box2 = makeBox()
    .cutPattern({ shape: 'rect', width: 8, height: 3, spacing: 6, border: 4 })
    .translate(-offset + GAP, -offset, 0).color("blue");

const box3 = makeBox()
    .cutPattern({ shape: 'square', width: 5, spacing: 8, border: 4 })
    .translate(-offset + GAP*2, -offset, 0).color("green");

const box4 = makeBox()
    .cutPattern({ shape: 'circle', width: 5, wallThickness: 2, border: 4 })
    .translate(-offset + GAP*3, -offset, 0).color("purple");

// Row 2: Polygons
const box5 = makeBox()
    .cutPattern({ shape: 'hexagon', width: 8, wallThickness: 1.2, border: 3 })
    .translate(-offset, -offset + GAP, 0).color("gold");

const box6 = makeBox()
    .cutPattern({ shape: 'octagon', width: 8, wallThickness: 1.5, border: 4 })
    .translate(-offset + GAP, -offset + GAP, 0).color("teal");

const box7 = makeBox()
    .cutPattern({ shape: 'triangle', width: 10, wallThickness: 2, border: 4 })
    .translate(-offset + GAP*2, -offset + GAP, 0).color("orange");

const box8 = makeBox()
    .cutPattern({ shape: 5, width: 10, wallThickness: 2, border: 4 })  // Pentagon
    .translate(-offset + GAP*3, -offset + GAP, 0).color("slategray");

// Row 3: Rounded rectangles and rotations
const box9 = makeBox()
    .cutPattern({ shape: 'rect', width: 12, height: 4, fillet: 2, spacing: 7, border: 4 })  // Rounded slots
    .translate(-offset, -offset + GAP*2, 0).color("hotpink");

const box10 = makeBox()
    .cutPattern({ shape: 'square', width: 6, fillet: 1.5, wallThickness: 2, border: 4 })  // Rounded squares
    .translate(-offset + GAP, -offset + GAP*2, 0).color("cyan");

const box11 = makeBox()
    .cutPattern({ shape: 'square', width: 5, rotation: 45, spacing: 8, border: 5 })  // Diamonds
    .translate(-offset + GAP*2, -offset + GAP*2, 0).color("lime");

const box12 = makeBox()
    .cutPattern({ shape: 'line', width: 1.5, spacing: 4, angle: 30, border: 4, depth: 1 })  // Angled lines
    .translate(-offset + GAP*3, -offset + GAP*2, 0).color("indigo");

// Row 4: Layout options (stagger, columns, direction)
const box13 = makeBox()
    .cutPattern({ shape: 'circle', width: 4, wallThickness: 1.5, stagger: true, border: 3 })
    .translate(-offset, -offset + GAP*3, 0).color("coral");

const box14 = makeBox()
    .cutPattern({ shape: 'hexagon', width: 6, wallThickness: 0.8, stagger: true, border: 2 })
    .translate(-offset + GAP, -offset + GAP*3, 0).color("steelblue");

const box15 = makeBox()
    .cutPattern({ shape: 'line', width: 1, spacing: 2.5, columns: 2, columnGap: 4, border: 3, depth: 1 })
    .translate(-offset + GAP*2, -offset + GAP*3, 0).color("brown");

const box16 = makeBox()
    .cutPattern({ shape: 'line', width: 1, spacing: 3, direction: 'y', border: 4, depth: 1 })
    .translate(-offset + GAP*3, -offset + GAP*3, 0).color("mediumseagreen");

// Create assembly with all boxes
const result = new Assembly()
    .add(box1).add(box2).add(box3).add(box4)
    .add(box5).add(box6).add(box7).add(box8)
    .add(box9).add(box10).add(box11).add(box12)
    .add(box13).add(box14).add(box15).add(box16);

result;
