// Gridfinity Baseplate Demo - Minimal open grid baseplate
//
// Gridfinity.baseplate() creates the thinnest possible baseplate:
// - Open grid structure (no solid floor)
// - Stepped rim profile (4.65mm tall) that bins clip into
// - No magnets or screw holes - just pure grid functionality

// Create a 3x2 baseplate (126mm x 84mm)
const result = Gridfinity.baseplate({ x: 3, y: 2 })
    .color("#95a5a6");

result;
