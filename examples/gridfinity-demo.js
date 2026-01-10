// Gridfinity Demo - Create bins with standardized base and cutouts
//
// Gridfinity.bin() creates a complete gridfinity-compatible unit:
// - Correct outer dimensions (41.5mm per grid unit)
// - Rounded corners (3.5mm radius)
// - Base chamfer for baseplate compatibility
// - Ready for cutouts

// Create a 3x2 gridfinity bin, 5 units tall (35mm)
// with 2 rectangular cutouts
const bin = Gridfinity.bin({ x: 3, y: 2, z: 5 })
    .cutRectGrid({
        width: 35,      // pocket width in mm
        height: 55,     // pocket height in mm
        count: 2,       // we want exactly 2 cutouts
        fillet: 5,      // corner radius
        minBorder: 3    // shell thickness
    })
    .color("#2ecc71");

const result = bin;
result;
