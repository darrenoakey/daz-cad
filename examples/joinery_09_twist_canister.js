// Earbud / cable capsule with central winding post — bayonet twist-lock joint.
// Insert the two halves and turn a quarter turn; VIEW: 0 assembled, 1 exploded, 2 print.
// The shell and post are joined by endcaps, making one solid source before splitting.
const VIEW = 1;
const CLEARANCE = 0.2;

const outerShell = new Workplane('XY').cylinder(28, 64);
const annularStorageVoid = new Workplane('XY').cylinder(22, 52).translate(0, 0, 6)
    .cut(new Workplane('XY').cylinder(10, 54).translate(0, 0, 5));
const lowerGripBand = new Workplane('XY').cylinder(29.2, 2.5).translate(0, 0, 8);
const upperGripBand = new Workplane('XY').cylinder(29.2, 2.5).translate(0, 0, 53.5);
// Cutting an annulus leaves a protective outer shell and a useful central winding post.
const body = outerShell.cut(annularStorageVoid).union(lowerGripBand).union(upperGripBand).color('#355d78');

const joint = body.splitAndJoin({
    // The bayonet sits in the 20 mm-diameter central post, with room to rotate freely.
    plane: { origin: [0, 0, 32], normal: [0, 0, 1], up: [0, 1, 0] },
    method: 'bayonet',
    size: 8,
    depth: 6,
    clearance: CLEARANCE,
    wall: 1.2,
    count: 1,
    positions: [[0, 0]]
});

joint.parts[0] = joint.parts[0].color('#234d68');
joint.parts[1] = joint.parts[1].color('#75b4cf');
console.log('Twist canister: align the entry windows, press together, then turn one quarter turn to the hard stops.');
console.log(joint.instructions.join('\n'));
console.warn('This is a storage capsule, not a pressure vessel; verify fit and bayonet rotation with a printer-specific coupon.');
console.warn(joint.warnings.join('\n'));

const result = joint.toAssembly({
    mode: ['assembled', 'exploded', 'print'][Math.max(0, Math.min(2, Math.round(VIEW)))],
    gap: 18
});
result;
