// Demo: Cutting line patterns using the unified cutPattern() API
//
// .cutPattern({ shape: 'line', ... }) creates parallel grooves across a selected face.
// Great for grip patterns, ventilation, or aesthetics.
//
// Key options for lines:
//   shape: 'line' - specifies line pattern
//   width: groove width in mm (default: 1.0)
//   depth: groove depth in mm (default: 0.4)
//   spacing: distance between groove centers (default: 2.0)
//   border: margin from face edges (default: 2.0)
//   direction: 'x' (horizontal) or 'y' (vertical)
//   angle: rotate the lines by N degrees
//   roundEnds: true to round the ends of lines (stadium shape)

// Create a simple box
const box = new Workplane("XY")
    .box(60, 40, 15);

// Cut horizontal line grooves into the top face using new cutPattern API
const result = box
    .faces(">Z")
    .cutPattern({
        shape: 'line',   // line pattern
        width: 1.0,      // 1mm wide grooves
        depth: 0.4,      // 0.4mm deep
        spacing: 2.0,    // 2mm between centers
        border: 3.0      // 3mm margin from edges
    })
    .color("#3498db");

result;
