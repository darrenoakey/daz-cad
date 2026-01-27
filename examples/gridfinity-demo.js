// Gridfinity Demo - Bins with proper stepped base profile
//
// Gridfinity.bin() creates gridfinity-compatible units with:
// - Separate base feet for each grid cell (4 feet for 2x2)
// - Stepped z-shaped profile (0.8mm + 1.8mm + 2.15mm = 4.75mm)
// - Correct outer dimensions (41.5mm per grid unit)

// Create a 2x2 gridfinity bin, 3 units tall
// This will have 4 separate stepped base feet
const bin = Gridfinity.bin({ x: 2, y: 2, z: 3 })
    .cutRectGrid({
        width: 25,      // pocket width in mm
        height: 25,     // pocket height in mm
        fillet: 3,      // corner radius
        minBorder: 3    // shell thickness
    })
    .color("#2ecc71");

const result = bin;
result;
