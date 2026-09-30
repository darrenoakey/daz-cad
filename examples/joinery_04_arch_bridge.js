/**
 * Freestanding arch-bridge sculpture split at its keystone by a jigsaw rail.
 * It is a true half-annulus with flat feet, extruded through Y; insert one half
 * from the front (-Y) edge along the full rail. VIEW: 0 assembled, 1 exploded,
 * 2 print. This display prototype is not a load-rated bridge; calibrate first.
 */
const VIEW = 1;
const CLEARANCE = 0.2;

const outerArc = new Workplane('XY').cylinder(50, 24).rotate(1, 0, 0, 90).translate(0, 12, 0);
const innerArc = new Workplane('XY').cylinder(28, 25).rotate(1, 0, 0, 90).translate(0, 12.5, 0);
const annulus = outerArc.cut(innerArc);
// Intersecting z >= 0 creates the flat-soled architectural arch without pads.
const upperHalf = new Workplane('XY').box(110, 26, 55);
const body = annulus.intersect(upperHalf);

const joint = body.splitAndJoin({
    plane: { origin: [0, 0, 40], normal: [1, 0, 0], up: [0, 1, 0] },
    method: 'jigsaw', size: 8, depth: 6, wall: 1.2,
    clearance: CLEARANCE, count: 1, detent: true
});
joint.parts[0] = joint.parts[0].color('#9c5b39');
joint.parts[1] = joint.parts[1].color('#d79761');
console.log('Arch bridge: align the two flat-footed arch halves and slide the jigsaw rail from the front extrusion edge.');
console.log(joint.instructions.join('\n'));
console.warn('Sculptural prototype only, not structural engineering; inspect rail roofs and fit with a small coupon.');
console.warn(joint.warnings.join('\n'));
const result = joint.toAssembly({ mode: ['assembled', 'exploded', 'print'][Math.max(0, Math.min(2, Math.round(VIEW)))], gap: 18 });
result;
