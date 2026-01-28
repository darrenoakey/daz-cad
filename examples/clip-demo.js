// Clip Demo - Pattern cutting on irregular shaped faces
// Demonstrates the 'clip' option for cutPattern()

// Create an irregular-shaped thin plate
// Using a rounded star shape to show how clipping works

// Create base shape: a thin cylinder
const cyl = new Workplane("XY").cylinder(35, 4);

// Cut a star pattern to make it irregular
const cuts = [];
for (let i = 0; i < 6; i++) {
    const angle = (i * 60) * Math.PI / 180;
    const x = 25 * Math.cos(angle);
    const y = 25 * Math.sin(angle);
    cuts.push(
        new Workplane("XY")
            .cylinder(12, 10)
            .translate(x, y, 0)
    );
}

// Create the irregular shape by cutting notches
let irregular = cyl;
for (const cut of cuts) {
    irregular = irregular.cut(cut);
}

// Now apply hexagon pattern with partial clipping
// 'partial' mode clips hexagons at the irregular boundary
const result = irregular.faces(">Z").cutPattern({
    shape: 'hexagon',
    width: 6,
    wallThickness: 1.5,
    stagger: true,
    clip: 'partial',  // Try 'whole' to see only complete hexagons
    border: 2,
    depth: 2
}).color("#3498db");

result;
