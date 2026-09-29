/**
 * Mechanically-compliant snap family geometry.
 *
 * Coordinates are always the split-plane frame: u/v lie on the seam and n is
 * its normal.  The key bodies deliberately remain separate from the coupon;
 * only the small latch-over-shoulder interference declared below is intended
 * to contact when assembled.
 */
import {
    localBox, localCylinder, localPrism,
    fuse, cut, combine, volume, valid, transformShape,
} from './joinery-kernel.js';

const EPS = 1e-5;

function requireRoom(o, family, minimumDepth = 1.35) {
    const { size: s, depth: d, clearance: c, wall: w } = o;
    if (![s, d, c, w].every(Number.isFinite) || s <= 0 || d <= 0 || c < 0 || w <= 0) {
        throw new Error(`${family}: finite positive size, depth, and wall with non-negative clearance are required`);
    }
    if (d < Math.max(w * minimumDepth, 2.4) || s < Math.max(w * 3.2, 5)) {
        throw new Error(`${family}: source is too thin for a compliant, printable snap feature`);
    }
}

function assertSolid(oc, shape, label) {
    if (!valid(oc, shape) || volume(oc, shape) <= EPS) throw new Error(`${label}: invalid solid`);
    return shape;
}

function requireSourceThickness(o, family, lowerNeeded, upperNeeded) {
    if (!Array.isArray(o.localBounds) || o.localBounds.length !== 6) return;
    const lower = -o.localBounds[2], upper = o.localBounds[5];
    if (lower < lowerNeeded || upper < upperNeeded) {
        throw new Error(`${family}: source is too thin either side of the cut plane for the requested capture depth`);
    }
}

function plus(oc, shapes, label) { return assertSolid(oc, combine(oc, shapes), label); }

/* A triangular ramp in the u/n section, extruded through v. */
function ramp(oc, frame, points, vStart, vEnd) {
    return localPrism(oc, frame, points, vStart, vEnd, 'v');
}

/**
 * Separate bridge key.  The centre bridge is a short, stiff n-web.  Its two
 * end beams are only attached at that bridge, leaving a real slit beside each
 * beam and therefore independent elastic motion at the two capture ends.
 */
function makeSnapKey(oc, frame, p, o) {
    requireRoom(o, 'snap-key', 1.55);
    const { size: s, depth: d, clearance: c, wall: w } = o;
    requireSourceThickness(o, 'snap-key', d * 0.86, d * 0.86);
    const [u, v] = p;
    const beamW = Math.max(w * 0.82, s * 0.105);
    const keyT = Math.max(w * 0.92, s * 0.16); // v thickness
    const bridgeN = Math.max(w * 1.45, d * 0.18);
    const armLength = d * 0.72;
    const hookW = Math.max(w * 1.45, s * 0.25);
    const hookN = Math.max(w * 0.90, d * 0.15);
    const interference = Math.min(0.08, Math.max(0.025, c * 0.35));
    // The throat is deliberately only interference narrower than the relaxed
    // hook.  The terminal pocket is larger than the hook: seated geometry has
    // clearance and the short throat contact exists only while inserting.
    const throatW = hookW - interference;
    const pocketW = hookW + 2 * c;

    // Central bridge occupies only the seam recess. Each beam overlaps this
    // bridge by bridgeN/2 and otherwise has an open flex slit around it.
    const bridge = localBox(oc, frame, [u, v, 0], [beamW, keyT, bridgeN]);
    const bridgeOverlap = Math.max(w * 0.25, 0.08);
    const lowerBeam = localBox(oc, frame,
        [u, v, -bridgeN / 2 - armLength / 2 + bridgeOverlap / 2], [beamW, keyT, armLength + bridgeOverlap]);
    const upperBeam = localBox(oc, frame,
        [u, v, bridgeN / 2 + armLength / 2 - bridgeOverlap / 2], [beamW, keyT, armLength + bridgeOverlap]);

    // The leading tips are narrow. The ramps widen toward the seam, leaving
    // the broad back face to catch the body shoulder after insertion.
    const lowerTip = -(bridgeN / 2 + armLength);
    const upperTip = bridgeN / 2 + armLength;
    const lowerHook = ramp(oc, frame, [
        [u - beamW / 2, lowerTip], [u + beamW / 2, lowerTip],
        [u + hookW / 2, lowerTip + hookN], [u - beamW / 2, lowerTip + hookN],
    ], v - keyT / 2, v + keyT / 2);
    const upperHook = ramp(oc, frame, [
        [u + beamW / 2, upperTip], [u - beamW / 2, upperTip],
        [u - hookW / 2, upperTip - hookN], [u + beamW / 2, upperTip - hookN],
    ], v - keyT / 2, v + keyT / 2);
    const key = plus(oc, [bridge, lowerBeam, upperBeam, lowerHook, upperHook], 'snap-key bridge');

    // Seam-open lead channels have a throat only interference-narrower than
    // the relaxed hook. Blind capture pockets add end travel and seated air.
    const lowerTransition = lowerTip + hookN;
    const upperTransition = upperTip - hookN;
    const lowerLead = localBox(oc, frame,
        [u, v, (lowerTransition - bridgeN / 2) / 2], [throatW, keyT + 2 * c, bridgeN / 2 - lowerTransition]);
    const upperLead = localBox(oc, frame,
        [u, v, (upperTransition + bridgeN / 2) / 2], [throatW, keyT + 2 * c, upperTransition - bridgeN / 2]);
    const endRelief = Math.max(d * 0.10, w * 0.40);
    const lowerPocket = localBox(oc, frame,
        [u + (pocketW - beamW) / 4, v, (lowerTip - endRelief + lowerTransition) / 2],
        [pocketW, keyT + 2 * c + s * 0.10, hookN + endRelief]);
    const upperPocket = localBox(oc, frame,
        [u - (pocketW - beamW) / 4, v, (upperTip + endRelief + upperTransition) / 2],
        [pocketW, keyT + 2 * c + s * 0.10, hookN + endRelief]);
    const seamRecess = localBox(oc, frame, [u, v, 0], [throatW, keyT + 2 * c, bridgeN + 2 * c]);
    // Cut separately: a union of cutter solids would erase the shoulder.
    const lower = assertSolid(oc, cut(oc, cut(oc, cut(oc, o.base.lower, seamRecess), lowerLead), lowerPocket), 'snap-key lower body');
    const upper = assertSolid(oc, cut(oc, cut(oc, cut(oc, o.base.upper, seamRecess), upperLead), upperPocket), 'snap-key upper body');

    return {
        lower, upper, keys: [key],
        print: { parts: ['n', '-n'], keys: ['v'] },
        note: `Insert the single bridge key while bringing the halves together. Each independent arm has a narrow leading ramp and expands behind its seam-open capture shoulder. The ${interference.toFixed(3)} mm throat interference occurs only during insertion; the seated pocket has ${c.toFixed(3)} mm radial clearance and end travel.`,
    };
}

/** Integral lower-half cantilever with an independent shear locator. */
function makeCantilever(oc, frame, p, o) {
    requireRoom(o, 'cantilever-snap', 1.7);
    const { size: s, depth: d, clearance: c, wall: w } = o;
    requireSourceThickness(o, 'cantilever-snap', d * 0.70, d * 0.88);
    const [u, v] = p;
    const beamW = Math.max(w * 0.78, s * 0.10);
    const beamT = Math.max(w * 0.82, s * 0.13);
    const hookW = Math.max(w * 1.5, s * 0.27);
    const hookN = Math.max(w, d * 0.15);
    const reachN = d * 0.74;
    const interference = Math.min(0.08, Math.max(0.025, c * 0.35));

    // The locator is deliberately separate from the spring. It carries in-
    // plane shear and keys registration, leaving the thin beam to retain only.
    const locatorU = u - s * 0.26;
    const locator = localBox(oc, frame,
        [locatorU, v, d * 0.18], [s * 0.26, s * 0.54, d * 0.92]);
    const beamU = u + s * 0.25;
    // The root stays well down in the lower half. The beam overlaps it, then
    // runs through the seam into the upper receiving window.
    const root = localBox(oc, frame,
        [beamU, v, -d * 0.43], [beamW, beamT, d * 0.42]);
    const beam = localBox(oc, frame,
        [beamU, v, (reachN - d * 0.25) / 2], [beamW, beamT, reachN + d * 0.25]);
    // Narrow tip first; broad back face is the capture shoulder.
    const hook = ramp(oc, frame, [
        [beamU + beamW / 2, reachN], [beamU - beamW / 2, reachN],
        [beamU - hookW / 2, reachN - hookN], [beamU + beamW / 2, reachN - hookN],
    ], v - beamT / 2, v + beamT / 2);
    // This bridge is wholly in the lower half: it makes locator and spring a
    // single integral feature without turning the thin beam into a rigid web.
    const rootBridge = localBox(oc, frame,
        [(locatorU + beamU) / 2, v, -d * 0.25],
        [beamU - locatorU + s * 0.13 + beamW / 2, s * 0.54, d * 0.16]);
    const male = plus(oc, [locator, rootBridge, root, beam, hook], 'cantilever-snap male');

    const locatorPocket = localBox(oc, frame,
        [locatorU, v, d * 0.25], [s * 0.26 + 2 * c, s * 0.54 + 2 * c, d * 1.02]);
    // The lead throat flexes the hook by only the declared interference;
    // the blind terminal window is wider, so seated parts do not intersect.
    const throatW = hookW - interference;
    const transitionN = reachN - hookN;
    const beamChannel = localBox(oc, frame,
        [beamU, v, transitionN / 2], [throatW, beamT + 2 * c, transitionN]);
    const windowRelief = Math.max(d * 0.10, w * 0.40);
    const captureWindow = localBox(oc, frame,
        [beamU - (hookW - beamW) / 4, v, (reachN + windowRelief + transitionN) / 2],
        [hookW + 2 * c, beamT + 2 * c + s * 0.16, hookN + windowRelief]);

    // Carve the lower relief *before* adding the spring. This leaves open air
    // around the beam while its root still overlaps uncut lower material; a
    // post-union cut would sever the intended compliant member.
    const relief = localBox(oc, frame,
        [beamU, v, -d * 0.05],
        [hookW + 2 * c + s * 0.10, beamT + 2 * c + s * 0.18, d * 0.28]);
    const relievedLower = assertSolid(oc, cut(oc, o.base.lower, relief), 'cantilever lower relief');
    const lower = assertSolid(oc, fuse(oc, relievedLower, male), 'cantilever lower union');
    const upper = assertSolid(oc, cut(oc, cut(oc, cut(oc, o.base.upper, locatorPocket), beamChannel), captureWindow), 'cantilever upper body');

    return {
        lower, upper, keys: [],
        print: { parts: ['n', '-n'], keys: ['v'] },
        note: `Press the locator tongue home first, then continue until the integral beam rides its narrow lead ramp into the terminal window. The rigid locator carries shear; the relief gap is reserved for hook deflection. The ${interference.toFixed(3)} mm throat interference is insertion-only; the seated window clears the hook.`,
    };
}

/** Separate split dowel whose slits stop before the central web. */
function makeSnapDowel(oc, frame, p, o) {
    requireRoom(o, 'snap-dowel', 1.45);
    const { size: s, depth: d, clearance: c, wall: w } = o;
    requireSourceThickness(o, 'snap-dowel', d * 0.88, d * 0.88);
    const [u, v] = p;
    const shaftR = Math.max(w * 0.72, s * 0.145);
    const barbR = shaftR + Math.max(w * 0.32, s * 0.055);
    const webN = Math.max(w * 1.8, d * 0.26);
    const endN = d * 0.78;
    const collarN = Math.max(w * 0.95, d * 0.14);
    const leadR = shaftR + c;
    const requiredDeflection = barbR - leadR;
    // Each finger gets at least the radial closing travel it needs to pass the
    // lead bore, plus a small no-contact reserve between opposing fingers.
    const slitW = Math.max(c * 2 + 0.08, w * 0.26, 2 * requiredDeflection + 0.08);
    const availableFingerTravel = (slitW - 0.08) / 2;
    if (availableFingerTravel + EPS < requiredDeflection) throw new Error('snap-dowel: split travel cannot clear the lead bore');

    const shank = localCylinder(oc, frame, [u, v, 0], shaftR, endN * 2);
    // Tapered rather than blunt collars: the narrow outer tips lead each pair
    // of barbed fingers into the bore, and their broad inner faces retain.
    const conicalBarb = (bottom, top, start) => {
        const cone = new oc.BRepPrimAPI_MakeCone_1(bottom, top, collarN);
        const translation = new oc.gp_Trsf_1();
        const vector = new oc.gp_Vec_4(u, v, start);
        translation.SetTranslation_1(vector);
        const moved = new oc.BRepBuilderAPI_Transform_2(cone.Shape(), translation, true);
        const shape = transformShape(oc, moved.Shape(), frame);
        moved.delete(); vector.delete(); translation.delete(); cone.delete();
        return shape;
    };
    // Circular conical collars match the circular capture bore. Rectangular
    // ramps would leave corner interference even at the fully seated pose.
    const lowerBarb = conicalBarb(shaftR, barbR, -endN);
    const upperBarb = conicalBarb(barbR, shaftR, endN - collarN);
    let pin = plus(oc, [shank, lowerBarb, upperBarb], 'snap-dowel blank');

    // Two long end slits give genuinely flexible opposing fingers but stop
    // before the central web. Thus the pin remains one connected solid.
    const slitStop = webN / 2 + d * 0.04;
    const slitLength = endN - slitStop + d * 0.08;
    const lowerSlit = localBox(oc, frame,
        [u, v, -(slitStop + slitLength / 2)], [slitW, barbR * 2 + s * 0.12, slitLength]);
    const upperSlit = localBox(oc, frame,
        [u, v, slitStop + slitLength / 2], [slitW, barbR * 2 + s * 0.12, slitLength]);
    pin = assertSolid(oc, cut(oc, pin, lowerSlit), 'snap-dowel lower split');
    pin = assertSolid(oc, cut(oc, pin, upperSlit), 'snap-dowel upper split');

    // Bore lead is smaller than each relieved terminal capture cavity. The
    // radial step is the positive shoulder; end relief leaves axial travel
    // beyond the barbed collar rather than bottoming the fingers immediately.
    const captureR = barbR + c;
    const leadN = d * 0.52;
    const captureN = d * 0.27;
    const endReliefN = Math.max(w * 0.45, d * 0.10);
    const lowerLead = localCylinder(oc, frame, [u, v, -leadN / 2], leadR, leadN + d * 0.06);
    const upperLead = localCylinder(oc, frame, [u, v, leadN / 2], leadR, leadN + d * 0.06);
    const lowerCapture = localCylinder(oc, frame, [u, v, -(leadN + captureN / 2)], captureR, captureN + endReliefN);
    const upperCapture = localCylinder(oc, frame, [u, v, leadN + captureN / 2], captureR, captureN + endReliefN);
    const lowerBore = plus(oc, [lowerLead, lowerCapture], 'snap-dowel lower bore');
    const upperBore = plus(oc, [upperLead, upperCapture], 'snap-dowel upper bore');
    const lower = assertSolid(oc, cut(oc, o.base.lower, lowerBore), 'snap-dowel lower body');
    const upper = assertSolid(oc, cut(oc, o.base.upper, upperBore), 'snap-dowel upper body');

    return {
        lower, upper, keys: [pin],
        print: { parts: ['n', '-n'], keys: ['v'] },
        note: `Push the single connected split dowel through the aligned seam bores. The tapered split fingers each close ${requiredDeflection.toFixed(3)} mm through the lead bore (the ${slitW.toFixed(3)} mm slit provides ${availableFingerTravel.toFixed(3)} mm per finger), then expand in the relieved capture cavities. The central web remains unslit and seated barbs have ${c.toFixed(3)} mm clearance.`,
    };
}

export { makeSnapKey, makeCantilever, makeSnapDowel };
