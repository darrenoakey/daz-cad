// ROBOT TREASURE CHEST — a desktop keepsake box with a friendly recessed robot face.
// Method: snap-key. Seat one end of the gold key in the chest socket, then
// align the robot-face panel and press it onto the free end until both catches engage.
// VIEW: 0 assembled, 1 exploded (default), 2 print layout.  The 100 x 70 mm
// footprint suits a typical desktop printer, but make a material/printer coupon:
// 0.20 mm clearance and the spring-key insertion force are not calibrated here.
const VIEW = 1;
const CLEARANCE = .2;

// The cavity opens through the top, so the chest remains useful after the
// rear-wall split.  Its 68 x 38 mm plan leaves a 16 mm rear wall around the
// connector's 10.4 mm tangential by 14.4 mm normal placement envelope.
const outer = new Workplane('XY').box(100, 70, 44).fillet(4);
const storageCavity = new Workplane('XY').box(68, 38, 40).translate(0, 0, 12);
const leftEye = new Workplane('XY').cylinder(6, 3)
    .rotate(1, 0, 0, 90).translate(-21, -33, 29);
const rightEye = new Workplane('XY').cylinder(6, 3)
    .rotate(1, 0, 0, 90).translate(21, -33, 29);
const mouth = new Workplane('XY').box(32, 4, 5).translate(0, -34, 19);
const mouthDivider = new Workplane('XY').box(3, 5, 7).translate(0, -34, 18);
const body = outer.cut(storageCavity).cut(leftEye).cut(rightEye).cut(mouth).cut(mouthDivider);

// The vertical rear-wall plane keeps the snap-key fully buried in 16 mm of
// solid material, rather than in the open storage cavity.
const joint = body.splitAndJoin({
    plane: { origin: [0, -27, 34], normal: [0, 1, 0], up: [0, 0, 1] },
    method: 'snap-key', size: 8, depth: 6, wall: 1.2,
    clearance: CLEARANCE, positions: [[0, 0]]
});
joint.parts[0] = joint.parts[0].color('#f19162');
joint.parts[1] = joint.parts[1].color('#78b7e5');
joint.keys[0] = joint.keys[0].color('#d7a72a');
console.log(joint.instructions.join('\n'));
console.warn(joint.warnings.join('\n'));
const result = joint.toAssembly({mode:['assembled','exploded','print'][Math.max(0,Math.min(2,Math.round(VIEW)))],gap:18});
result;
