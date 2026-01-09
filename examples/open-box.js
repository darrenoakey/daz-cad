// Open Box - A tray with walls on three sides
// Configurable dimensions and optional honeycomb pattern

// ===== CONFIGURATION =====
const LENGTH = 80;          // X dimension (mm)
const WIDTH = 40;           // Y dimension (mm)
const WALL_HEIGHT = 40;     // Height of walls (mm)
const WALL_THICKNESS = 2;   // Thickness of walls and base (mm)

// Pattern settings (set to false to disable)
const CUT_BASE_PATTERN = false;  // Cut honeycomb pattern in base
const CUT_WALL_PATTERN = false;  // Cut pattern in walls (not yet implemented)
const PATTERN_WALL_THICKNESS = 0.8;  // Wall thickness between hexagons
const PATTERN_BORDER = 3;            // Solid border around pattern

// Edge treatment
const CHAMFER_SIZE = 0.5;   // Bottom edge chamfer
const FILLET_SIZE = 0.4;    // Fillet radius for other edges

// ===== BUILD THE MODEL =====

// Build base plate separately (so pattern cuts only affect the base)
let base = new Workplane("XY").box(LENGTH, WIDTH, WALL_THICKNESS);

if (CUT_BASE_PATTERN) {
    base = base.cutPattern({
        sides: 6,
        wallThickness: PATTERN_WALL_THICKNESS,
        border: PATTERN_BORDER
    });
}

// Build walls separately, then union with base
// Left wall
const leftWall = new Workplane("XY")
    .box(WALL_THICKNESS, WIDTH, WALL_HEIGHT)
    .translate(-(LENGTH/2 - WALL_THICKNESS/2), 0, WALL_THICKNESS + WALL_HEIGHT/2);

// Right wall
const rightWall = new Workplane("XY")
    .box(WALL_THICKNESS, WIDTH, WALL_HEIGHT)
    .translate((LENGTH/2 - WALL_THICKNESS/2), 0, WALL_THICKNESS + WALL_HEIGHT/2);

// Back wall (connects left and right, minus the corners already covered)
const backWall = new Workplane("XY")
    .box(LENGTH - 2*WALL_THICKNESS, WALL_THICKNESS, WALL_HEIGHT)
    .translate(0, -(WIDTH/2 - WALL_THICKNESS/2), WALL_THICKNESS + WALL_HEIGHT/2);

// Combine all parts
let box = base
    .union(leftWall)
    .union(rightWall)
    .union(backWall);

// Chamfer the outside bottom edges
const chamfered = box.faces("<Z").edges().chamfer(CHAMFER_SIZE);

// Fillet all other edges
const result = chamfered.fillet(FILLET_SIZE).color("#3498db");

result;
