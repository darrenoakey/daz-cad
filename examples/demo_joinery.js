// Ten cut-plane connector families. Change METHOD (0..9) and VIEW below.
// Use Cut & Join in the toolbar to place a plane on your own Workplane.
// Millimetres; clearance is per side. Print a small coupon before a large model.
const METHOD = 0;
const VIEW = 'print'; // 'assembled', 'exploded', or 'print'
const CLEARANCE = 0.2;

const methods = [
    'snap-key', 'butterfly-key', 'dovetail', 'jigsaw', 'cantilever-snap',
    'snap-dowel', 'cross-key', 'scarf-wedge', 'bayonet', 'bridge-clip'
];
const body = new Workplane('XY').box(60, 40, 24).color('#578fc7');
const joint = body.splitAndJoin({
    plane: { origin: [0, 0, 12], normal: [0, 0, 1], up: [0, 1, 0] },
    method: methods[METHOD], size: 8, depth: 6,
    clearance: CLEARANCE, wall: 1.2, count: 1
});
console.log(joint.instructions.join('\n'));
console.warn(joint.warnings.join('\n'));
const result = joint.toAssembly({ mode: VIEW, gap: 15 });
result;
