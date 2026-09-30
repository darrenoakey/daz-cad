/**
 * Desk cable comb with a continuous dovetail service joint. Four front-open,
 * top-open U channels capture charging leads while the central spine remains
 * solid for the rail. Slide the upper half in from the front (-Y) edge. VIEW:
 * 0 assembled, 1 exploded, 2 print. Clearance needs printer-specific tuning.
 */
const VIEW = 1;
const CLEARANCE = 0.2;

let body = new Workplane('XY').box(100, 40, 24);
// These are real front-entry, top-open cable lanes; none approaches x=0 where
// the connector's padded envelope and full sliding corridor require material.
for (const x of [-36, -18, 18, 36]) {
    const cableLane = new Workplane('XY').box(8, 19, 18)
        .translate(x, -10.5, 16);
    body = body.cut(cableLane);
}

const joint = body.splitAndJoin({
    plane: { origin: [0, 0, 12], normal: [0, 0, 1], up: [0, 1, 0] },
    method: 'dovetail', size: 8, depth: 6, wall: 1.2,
    clearance: CLEARANCE, count: 1, detent: true
});
joint.parts[0] = joint.parts[0].color('#7452a0');
joint.parts[1] = joint.parts[1].color('#bea0df');
console.log('Cable comb: route leads through the four open U lanes, then slide the dovetail from the front edge to its solid stop.');
console.log(joint.instructions.join('\n'));
console.warn('Print a material-and-nozzle-specific dovetail coupon first; keep the front insertion corridor clear.');
console.warn(joint.warnings.join('\n'));
const result = joint.toAssembly({ mode: ['assembled', 'exploded', 'print'][Math.max(0, Math.min(2, Math.round(VIEW)))], gap: 16 });
result;
