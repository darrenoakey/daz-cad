// Toolbox carry-handle prototype — cross-keyed tongue joint.
// The handle splits left/right through the top grip; assemble the tongue, then
// slide the gold transverse key in from the open front/back edge. VIEW: 0 assembled,
// 1 exploded, 2 print. Prototype only: coupon-test it; it is not load-rated.
const VIEW = 1;
const CLEARANCE = 0.2;

const topGrip = new Workplane('XY').box(100, 24, 16).translate(0, 0, 40);
const leftFoot = new Workplane('XY').box(20, 24, 48).translate(-40, 0, 0);
const rightFoot = new Workplane('XY').box(20, 24, 48).translate(40, 0, 0);
// The 8 mm overlaps make this one continuous, printable U-shaped source solid.
const body = topGrip.union(leftFoot).union(rightFoot).color('#2867a8');

const joint = body.splitAndJoin({
    // n = X, v = Z, u = Y: the transverse key has a genuine Y-edge entry.
    plane: { origin: [0, 0, 48], normal: [1, 0, 0], up: [0, 0, 1] },
    method: 'cross-key',
    size: 9,
    depth: 6,
    clearance: CLEARANCE,
    wall: 1.2,
    count: 1,
    positions: [[0, 0]]
});

// Keep actual generated solids, while making the two handle halves and key legible.
joint.parts[0] = joint.parts[0].color('#1f5f9f');
joint.parts[1] = joint.parts[1].color('#58a6dc');
joint.keys[0] = joint.keys[0].color('#d99a28');
console.log('Toolbox-handle prototype: seat the tongue, then slide the key through the exposed Y edge.');
console.log(joint.instructions.join('\n'));
console.warn('Not load-rated: print and break-test a coupon in the intended material and orientation.');
console.warn(joint.warnings.join('\n'));

const result = joint.toAssembly({
    mode: ['assembled', 'exploded', 'print'][Math.max(0, Math.min(2, Math.round(VIEW)))],
    gap: 18
});
result;
