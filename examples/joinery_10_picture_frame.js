// Two-part tabletop picture frame — twin external bridge clips.
// Both clips slide in through accessible thickness edges and stop rotation; VIEW: 0 assembled,
// 1 exploded, 2 print. Use a backing panel separately if the displayed art needs protection.
const VIEW = 1;
const CLEARANCE = 0.2;

const blank = new Workplane('XY').box(110, 150, 18);
const photographWindow = new Workplane('XY').box(74, 114, 22).translate(0, 0, -2);
// 18 mm borders remain around a 74 x 114 mm photograph window in one source solid.
const body = blank.cut(photographWindow).color('#71495e');

const joint = body.splitAndJoin({
    // n = Y, v = Z, u = -X. Clips at both side borders use their nearest X outer edge
    // and enter along Z, so each rail has real exposed material and access.
    plane: { origin: [46, 0, 9], normal: [0, 1, 0], up: [0, 0, 1] },
    method: 'bridge-clip',
    size: 8,
    depth: 6,
    clearance: CLEARANCE,
    wall: 1.2,
    count: 2,
    positions: [[0, 0], [92, 0]]
});

joint.parts[0] = joint.parts[0].color('#63394f');
joint.parts[1] = joint.parts[1].color('#bd7b9a');
joint.keys[0] = joint.keys[0].color('#d99a28');
joint.keys[1] = joint.keys[1].color('#d99a28');
console.log('Picture frame: butt the front/back U-shaped halves, then slide both gold bridge clips in from their open thickness edges.');
console.log(joint.instructions.join('\n'));
console.warn('Print a fit coupon and inspect the thin clip lips in the slicer before using the finished frame.');
console.warn(joint.warnings.join('\n'));

const result = joint.toAssembly({
    mode: ['assembled', 'exploded', 'print'][Math.max(0, Math.min(2, Math.round(VIEW)))],
    gap: 18
});
result;
