/**
 * Butterfly-key mountain desk sculpture — a small layered landscape with a
 * removable gold bow-tie spline. The split is vertical at the central peak;
 * slide the key in from the front (-Y) edge. VIEW: 0 assembled, 1 exploded,
 * 2 print. Calibrate the 0.2 mm clearance on a coupon before printing.
 */
const VIEW = 1;
const CLEARANCE = 0.2;

const plinth = new Workplane('XY').box(160, 24, 18);
const centralPeak = new Workplane('XY').isoPrism(100, 32, 24)
    .rotate(1, 0, 0, 90).translate(0, 12, 33);
const leftPeak = new Workplane('XY').isoPrism(60, 22, 24)
    .rotate(1, 0, 0, 90).translate(-43, 12, 28);
const rightPeak = new Workplane('XY').isoPrism(68, 24, 24)
    .rotate(1, 0, 0, 90).translate(46, 12, 29);
// Peaks overlap the plinth by 1 mm so this is one genuinely fused solid.
const body = plinth.union(centralPeak).union(leftPeak).union(rightPeak);

const joint = body.splitAndJoin({
    plane: { origin: [0, 0, 25], normal: [1, 0, 0], up: [0, 1, 0] },
    method: 'butterfly-key', size: 8, depth: 6, wall: 1.2,
    clearance: CLEARANCE, count: 1
});
joint.parts[0] = joint.parts[0].color('#3f907f');
joint.parts[1] = joint.parts[1].color('#9bd1b5');
joint.keys[0] = joint.keys[0].color('#d7a62b');
console.log('Mountain sculpture: insert the butterfly key from the front edge after butting the two landscape halves.');
console.log(joint.instructions.join('\n'));
console.warn('Prototype/display object only; print a fit coupon and inspect the key channel in your slicer.');
console.warn(joint.warnings.join('\n'));
const result = joint.toAssembly({ mode: ['assembled', 'exploded', 'print'][Math.max(0, Math.min(2, Math.round(VIEW)))], gap: 16 });
result;
