// Gridfinity Demo - Create inserts with optimized cutout grids
//
// This demonstrates the Gridfinity extension for creating
// gridfinity-compatible inserts with automatic grid optimization.

// Create a 2x2 gridfinity plug, 3 units tall
// with rectangular cutouts optimized for the space
const plug = Gridfinity.plug({ x: 2, y: 2, z: 3 })
    .cutRectGrid({
        width: 25,      // pocket width in mm
        height: 25,     // pocket height in mm
        fillet: 3,      // corner radius
        minBorder: 2    // shell thickness
    })
    .color("#3498db");

const result = plug;
result;
