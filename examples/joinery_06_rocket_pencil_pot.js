// ROCKET PENCIL POT — an open-top desktop cup with three low launch fins.
// Method: snap-dowel.  Stack the two horizontal sections, then press the
// single split retention dowel through the aligned boss bores until it seats.
// VIEW: 0 assembled, 1 exploded (default), 2 print layout.  The 64 mm body
// fits a desktop print bed; verify dowel flex and 0.20 mm clearance on a coupon.
// The top is intentionally flat/open: there is no pointed nose to destabilise
// the inverted upper print, and the pot stays accessible after separation.
const VIEW = 1;
const CLEARANCE = .2;

const fuselage = new Workplane('XY').cylinder(32, 72);
// Overlap the fuselage by 2 mm so the collar is fused into the one body solid.
const rim = new Workplane('XY').cylinder(25, 18).translate(0, 0, 70);
// A broad, solid internal sidewall boss surrounds the dowel placement envelope
// at x=27, y=0; it spans z=24..64 and remains outside the 19 mm-radius cavity.
const dowelBoss = new Workplane('XY').box(18, 18, 40).translate(27, 0, 24);
const finA = new Workplane('XY').wedge(10, 30, 22).translate(0, 35, 0);
const finB = new Workplane('XY').wedge(10, 30, 22).translate(0, 35, 0).rotate(0, 0, 1, 120);
const finC = new Workplane('XY').wedge(10, 30, 22).translate(0, 35, 0).rotate(0, 0, 1, 240);
const pencilCavity = new Workplane('XY').cylinder(19, 86).translate(0, 0, 4);
const body = fuselage.union(rim).union(dowelBoss).union(finA).union(finB).union(finC).cut(pencilCavity);

// The x=27 boss supplies full solid material around the 10.4 mm tangential
// and 14.4 mm normal connector envelope; the dowel never lies in the cup void.
const joint = body.splitAndJoin({
    plane: { origin: [0, 0, 44], normal: [0, 0, 1], up: [0, 1, 0] },
    method: 'snap-dowel', size: 8, depth: 6, wall: 1.2,
    clearance: CLEARANCE, positions: [[27, 0]]
});
joint.parts[0] = joint.parts[0].color('#d94b45');
joint.parts[1] = joint.parts[1].color('#f4f0df');
joint.keys[0] = joint.keys[0].color('#d7a72a');
console.log(joint.instructions.join('\n'));
console.warn(joint.warnings.join('\n'));
const result = joint.toAssembly({mode:['assembled','exploded','print'][Math.max(0,Math.min(2,Math.round(VIEW)))],gap:20});
result;
