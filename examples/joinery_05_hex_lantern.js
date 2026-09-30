// HEX LED LANTERN — a ventilated, open-top shade for a battery LED module only.
// Method: cantilever-snap.  Align the two horizontal shell sections and push
// down until the integral locator seats and the compliant hook clicks home.
// VIEW: 0 assembled, 1 exploded (default), 2 print layout.  Use only a cool
// LED light: this thin-walled printed shade is not a candle or heat enclosure.
// Slice-check the hook roof and calibrate the nominal 0.20 mm fit on a coupon.
const VIEW = 1;
const CLEARANCE = .2;

// A 84 mm flat-to-flat hex with a 58 mm inner hex gives 13 mm side walls.
// The back-wall connector at y=-35.5 has its entire 10.4 x 10.4 mm seam
// envelope inside that wall, well away from the open central light chamber.
const outer = new Workplane('XY').polygonPrism(6, 84, 70);
const lightChamber = new Workplane('XY').polygonPrism(6, 58, 66).translate(0, 0, 5);
const frontVent1 = new Workplane('XY').box(38, 20, 5).translate(0, 36, 9);
const frontVent2 = new Workplane('XY').box(38, 20, 5).translate(0, 36, 18);
const frontVent3 = new Workplane('XY').box(38, 20, 5).translate(0, 36, 27);
const body = outer.cut(lightChamber).cut(frontVent1).cut(frontVent2).cut(frontVent3);

// Horizontal cut: the lower part remains a five-millimetre-bottom LED base,
// while the upper part is an open-ended ventilated shade.  The snap is placed
// in the deliberately solid rear hex wall, not in the hollow chamber.
const joint = body.splitAndJoin({
    plane: { origin: [0, 0, 35], normal: [0, 0, 1], up: [0, 1, 0] },
    method: 'cantilever-snap', size: 8, depth: 6, wall: 1.2,
    clearance: CLEARANCE, positions: [[0, -35.5]]
});
joint.parts[0] = joint.parts[0].color('#29445f');
joint.parts[1] = joint.parts[1].color('#f0b74b');
console.log(joint.instructions.join('\n'));
console.warn(joint.warnings.join('\n'));
const result = joint.toAssembly({mode:['assembled','exploded','print'][Math.max(0,Math.min(2,Math.round(VIEW)))],gap:20});
result;
