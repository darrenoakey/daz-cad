/**
 * Model bridge girder with an underside-access scarf-and-wedge lock. Broad
 * flanges and a full-height central web make a recognizable I-beam; the wedge
 * enters upward from Z=0 through material in the web. VIEW: 0 assembled,
 * 1 exploded, 2 print. Prototype only: not load-rated, and fit must be tested.
 */
const VIEW = 1;
const CLEARANCE = 0.2;

const lowerFlange = new Workplane('XY').box(160, 50, 8);
const upperFlange = new Workplane('XY').box(160, 50, 8).translate(0, 0, 24);
const web = new Workplane('XY').box(160, 20, 32);
// Each web/flange overlap is substantial, yielding one solid girder rather
// than a visual assembly of disconnected plates.
const body = lowerFlange.union(web).union(upperFlange);

const joint = body.splitAndJoin({
    plane: { origin: [0, 0, 16], normal: [1, 0, 0], up: [0, 0, 1] },
    method: 'scarf-wedge', size: 8, depth: 6, wall: 1.2,
    clearance: CLEARANCE, count: 1, wedgePreload: 0
});
joint.parts[0] = joint.parts[0].color('#3a5873');
joint.parts[1] = joint.parts[1].color('#7298b7');
joint.keys[0] = joint.keys[0].color('#d29a27');
console.log('Bridge girder: engage the scarf overlap, then drive the gold wedge upward from the underside until its head seats.');
console.log(joint.instructions.join('\n'));
console.warn('Model/prototype only, not load-rated; print a scarf and wedge fit coupon before a full girder.');
console.warn(joint.warnings.join('\n'));
const result = joint.toAssembly({ mode: ['assembled', 'exploded', 'print'][Math.max(0, Math.min(2, Math.round(VIEW)))], gap: 20 });
result;
