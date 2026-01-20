// Gridfinity Baseplate on Surface Demo
//
// addBaseplate() automatically:
// - Measures the top surface of your shape
// - Calculates the largest baseplate that fits
// - Creates and unions an open grid baseplate onto the top
//
// Great for adding Gridfinity storage to:
// - Custom enclosures
// - Desk organizers
// - Shelf inserts
// - Any flat surface!

// Create a base platform (150mm x 100mm x 10mm thick)
const platform = new Workplane("XY")
    .box(150, 100, 10)
    .edges("|Z")
    .fillet(3)
    .color("#34495e");

// Add a gridfinity baseplate on top
// This will automatically create a 3x2 baseplate (126mm x 84mm)
// since that's the largest grid that fits on 150x100mm
const result = platform.addBaseplate();

result;
