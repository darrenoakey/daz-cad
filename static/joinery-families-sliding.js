/**
 * Continuous, accessible sliding joinery families.
 *
 * All profiles are expressed in the split-plane frame supplied by joinery.js:
 * u is across the joint, v is the intentionally open insertion direction, and
 * n is the seam normal.  A family never makes a closed blind T-pocket: its
 * female cutter reaches the chosen negative-v access edge.
 */
import {
    localBox, localPrism, fuse, cut, combine,
} from './joinery-kernel.js';

const EPS = 1e-5;

function finite(value, name) {
    if (!Number.isFinite(value)) throw new Error(`splitAndJoin: ${name} must be finite`);
    return value;
}

/**
 * Resolve the one permitted access edge.  Core can pass projected local bounds
 * for arbitrary solids; the conservative fallback deliberately covers the
 * documented 60 x 40 x 24 default box from a centred connector.
 */
function slidePath(o, p, minimum) {
    const bounds = o.localBounds || o.frameBounds;
    let entry;
    if (Array.isArray(bounds) && Number.isFinite(bounds[1])) {
        // Kernel projection order: [uMin, vMin, nMin, uMax, vMax, nMax].
        entry = bounds[1] + 0.02;
    } else if (bounds && Number.isFinite(bounds.vMin)) {
        entry = bounds.vMin + 0.02;
    } else {
        const travel = finite(o.accessLength ?? o.slideLength ?? o.size * 4, 'accessLength');
        if (travel < minimum) {
            throw new Error('splitAndJoin: accessLength is too short to expose a continuous slide path');
        }
        entry = p[1] - travel;
    }
    // A rail needs real engagement length, not just its cross-section.  Keep
    // the hard stop inside available material, including centred default boxes.
    let engagement = Math.max(o.wall * 2, o.size * 2.5);
    if (Array.isArray(bounds) && Number.isFinite(bounds[4])) {
        engagement = Math.min(engagement, bounds[4] - p[1] - o.wall);
    }
    const stop = p[1] + engagement;
    if (stop - entry < minimum) {
        throw new Error('splitAndJoin: selected access edge leaves insufficient travel for this sliding joint');
    }
    return { entry, stop };
}

function expandProfile(profile, clearance) {
    // Offset each edge by the physical per-side clearance and intersect its
    // neighbours. Moving vertices away from the centre shrinks concave pockets
    // at retaining shoulders and causes assembled solids to intersect.
    const cross2 = (a, b) => a[0] * b[1] - a[1] * b[0];
    const area = profile.reduce((sum, point, i) => sum + cross2(point, profile[(i + 1) % profile.length]), 0);
    const edges = profile.map((point, i) => {
        const next = profile[(i + 1) % profile.length];
        const direction = [next[0] - point[0], next[1] - point[1]];
        const scale = Math.sign(area) * clearance / Math.hypot(...direction);
        const offset = [direction[1] * scale, -direction[0] * scale];
        return { point: [point[0] + offset[0], point[1] + offset[1]], direction, offset };
    });
    return edges.map((edge, i) => {
        const previous = edges[(i + edges.length - 1) % edges.length];
        const denominator = cross2(previous.direction, edge.direction);
        if (Math.abs(denominator) < EPS) return edge.point;
        const difference = [edge.point[0] - previous.point[0], edge.point[1] - previous.point[1]];
        const distance = cross2(difference, edge.direction) / denominator;
        return [previous.point[0] + distance * previous.direction[0], previous.point[1] + distance * previous.direction[1]];
    });
}

function railPair(oc, frame, p, o, profile, path) {
    const male = localPrism(oc, frame, profile, path.entry, path.stop, 'v');
    // Only the cutter crosses the access face; the integral rail begins inside it.
    const female = localPrism(oc, frame, expandProfile(profile, o.clearance, p[0]), path.entry - 0.08, path.stop + 0.05, 'v');
    return { lower: fuse(oc, o.base.lower, male), upper: cut(oc, o.base.upper, female) };
}

function addSpringDetent(oc, frame, p, o, path, result, roof) {
    if (!o.detent) return result;
    const [u] = p, s = o.size, w = o.wall, c = o.clearance;
    const armLength = Math.max(s * 0.7, w * 4);
    const thickness = w * 0.35;
    const travel = Math.max(c + w * 0.25, w * 0.45);
    const armTop = roof + travel + thickness;
    const toothHeight = c + w * 0.22;
    const toothLength = Math.max(w * 1.2, toothHeight * 1.5);
    const armEnd = path.stop - w * 0.3;
    const armStart = armEnd - armLength;
    const arm = localBox(oc, frame, [u, (armStart + armEnd) / 2, armTop - thickness / 2],
        [s * 0.2, armLength, thickness]);
    const anchor = localBox(oc, frame, [u, armEnd - w * 0.2, (roof + armTop) / 2 - w * 0.05],
        [s * 0.2, w * 0.5, armTop - roof + w * 0.1]);
    // The higher-v tip leads insertion. Its shallow ramp depresses the leaf;
    // the vertical rear face catches only after reaching the terminal pocket.
    const tooth = localPrism(oc, frame,
        [[armStart, armTop - thickness / 2], [armStart, armTop + toothHeight],
         [armStart + toothLength, armTop - thickness / 2]],
        u - s * 0.1, u + s * 0.1, 'u');
    result.lower = fuse(oc, result.lower, combine(oc, [anchor, arm, tooth]));
    const channel = localBox(oc, frame,
        [u, (path.entry + path.stop) / 2, (roof + armTop + c) / 2],
        [s * 0.2 + 2 * c, path.stop - path.entry + 0.2, armTop + c - roof + 0.1]);
    const receiver = localBox(oc, frame,
        [u, armStart + toothLength / 2, armTop + toothHeight / 2],
        [s * 0.2 + 2 * c, toothLength + 2 * c, toothHeight + 2 * c]);
    result.upper = cut(oc, cut(oc, result.upper, channel), receiver);
    return result;
}

/**
 * Sliding dovetail rail with a faceted undercut roof.  Its lower root overlaps
 * the negative half, while the widened head can only leave through -v.
 */
export function makeDovetail(oc, frame, p, o) {
    const s = o.size, d = o.depth, w = o.wall;
    const [u] = p;
    const root = Math.max(s * 0.38, w * 1.6);
    const head = s * 0.78;
    const path = slidePath(o, p, s * 1.8);
    const profile = [
        [u - root / 2, -w * 0.45],
        [u + root / 2, -w * 0.45],
        [u + root / 2, d * 0.20],
        [u + head / 2, d * 0.58],
        [u + head / 2, d * 0.82],
        [u - head / 2, d * 0.82],
        [u - head / 2, d * 0.58],
        [u - root / 2, d * 0.20],
    ];
    const result = addSpringDetent(oc, frame, p, o, path, railPair(oc, frame, p, o, profile, path), d * 0.82);
    return {
        ...result,
        keys: [],
        note: 'Insert from the negative-v access edge and slide the faceted dovetail rail to the positive-v solid stop. The undercut retains seam-normal pull-out; detent:true adds an integral anchored spring leaf and upper receiver to resist reverse slide.',
        // The framework maps each named local axis to build +Z.
        print: { parts: [o.detent ? '-v' : 'v', o.detent ? '-v' : 'v'], keys: [] },
        printGuidance: 'Print both continuous v-sweeps upright; their faceted u/n profiles then have no hidden horizontal roof. Keep the negative-v entry unobstructed and slide only along +v to the solid stop.'
    };
}

/**
 * A jigsaw rail is one constant, lobed [u,n] profile swept along v, rather
 * than isolated cylinders.  The two faceted shoulders make a positive
 * interlock while every v cross-section remains an insertion cross-section.
 */
export function makeJigsaw(oc, frame, p, o) {
    const s = o.size, d = o.depth, w = o.wall;
    const [u] = p;
    const root = Math.max(s * 0.30, w * 1.45);
    const waist = s * 0.43;
    const lobe = s * 0.62;
    const path = slidePath(o, p, s * 1.9);
    const profile = [
        [u - root / 2, -w * 0.42],
        [u + root / 2, -w * 0.42],
        [u + root / 2, d * 0.16],
        [u + waist / 2, d * 0.28],
        [u + lobe / 2, d * 0.47],
        [u + lobe / 2, d * 0.66],
        [u + waist / 2, d * 0.78],
        [u + root / 2, d * 0.90],
        [u - root / 2, d * 0.90],
        [u - waist / 2, d * 0.78],
        [u - lobe / 2, d * 0.66],
        [u - lobe / 2, d * 0.47],
        [u - waist / 2, d * 0.28],
        [u - root / 2, d * 0.16],
    ];
    const result = addSpringDetent(oc, frame, p, o, path, railPair(oc, frame, p, o, profile, path), d * 0.90);
    return {
        ...result,
        keys: [],
        note: 'Start at the negative-v opening and translate along v. The rail is a single constant faceted lobed profile for the full path, so there are no discrete bulbs to trap during insertion; detent:true adds an integral spring leaf and receiver against reverse slide.',
        print: { parts: [o.detent ? '-v' : 'v', o.detent ? '-v' : 'v'], keys: [] },
        printGuidance: 'Print both continuous v-sweeps upright; the faceted lobed u/n profile avoids a hidden horizontal ceiling. Slide only along +v from the negative-v entry.'
    };
}

function scarfProfile(u, s, d, w) {
    const run = s * 0.86;
    const low = -w * 0.42;
    const toe = d * 0.20;
    const heel = d * 0.78;
    // Long sloped faces are a genuine scarf/lap, not a rectangular tongue.
    return [
        [u - run / 2, low],
        [u + run / 2, low],
        [u + run / 2, toe],
        [u - run / 2, heel],
    ];
}

function wedgeProfile(path, d, clearance, preload) {
    const entry = path.entry - 0.5;
    const seat = path.stop - 0.08;
    const thin = Math.max(d * 0.20, clearance * 3);
    const thick = d * 0.58;
    // The leading +v tip is thin and the accessible -v tail is thick.  It can
    // therefore enter first and develop preload only as the tail is seated.
    return [
        [entry, -thick / 2],
        [seat, -thin / 2],
        [seat, thin / 2 + preload],
        [entry, thick / 2],
    ];
}

function scarfRetainerProfile(u, s, d, w) {
    const waist = Math.max(w * 1.05, s * 0.18);
    const wing = Math.max(w * 1.75, s * 0.34);
    const low = d * 0.16;
    const high = d * 0.56;
    // Hourglass/dovetail shoulders sit behind material in both halves.
    return [
        [u - wing / 2, -high], [u + wing / 2, -high],
        [u + wing / 2, -low], [u + waist / 2, -low],
        [u + waist / 2, low], [u + wing / 2, low],
        [u + wing / 2, high], [u - wing / 2, high],
        [u - wing / 2, low], [u - waist / 2, low],
        [u - waist / 2, -low], [u - wing / 2, -low],
    ];
}

/**
 * Sloped scarf/lap with an independent, tapered transverse wedge.  The wedge
 * slot reaches the same negative-v access edge and crosses both halves, so a
 * seated key mechanically captures the scarf against seam-normal separation.
 */
export function makeScarfWedge(oc, frame, p, o) {
    const s = o.size, d = o.depth, w = o.wall;
    const [u] = p;
    const path = slidePath(o, p, s * 2.1);
    const lap = localPrism(oc, frame, scarfProfile(u, s, d, w), path.entry + s * 0.35, path.stop - s * 0.18, 'v');
    const lapPocket = localPrism(oc, frame,
        expandProfile(scarfProfile(u, s, d, w), o.clearance, u),
        path.entry + s * 0.35 - 0.04, path.stop - s * 0.18 + 0.04, 'v');
    let lower = fuse(oc, o.base.lower, lap);
    let upper = cut(oc, o.base.upper, lapPocket);

    const keyWidth = Math.max(s * 0.34, w * 1.65);
    const preload = o.wedgePreload === undefined ? Math.min(0.06, o.clearance * 0.3) : finite(o.wedgePreload, 'wedgePreload');
    if (preload < 0 || preload >= d * 0.12) {
        throw new Error('splitAndJoin: wedgePreload must be non-negative and smaller than the scarf key thickness');
    }
    const key = localPrism(oc, frame, wedgeProfile(path, d, o.clearance, preload), u - keyWidth / 2, u + keyWidth / 2, 'u');
    const slotProfile = wedgeProfile(path, d, o.clearance, 0)
        .map(([v, n]) => [v, n + (n < 0 ? -o.clearance : o.clearance)]);
    const slot = localPrism(oc, frame, slotProfile,
        u - keyWidth / 2 - o.clearance, u + keyWidth / 2 + o.clearance, 'u');
    // A dovetail-waisted keeper runs beside the taper.  Its upper and lower
    // wings sit behind roofs in the respective halves, so the key cannot let
    // the scarf separate along n until it is deliberately slid back out.
    const retainerProfile = scarfRetainerProfile(u, s, d, w);
    const retainer = localPrism(oc, frame, retainerProfile, path.entry, path.stop, 'v');
    const retainerPocket = localPrism(oc, frame, expandProfile(retainerProfile, o.clearance, u), path.entry - 0.08, path.stop + 0.05, 'v');
    const pockets = combine(oc, [slot, retainerPocket]);
    // Both pocket systems are open only at the selected -v material edge.
    lower = cut(oc, lower, pockets);
    upper = cut(oc, upper, pockets);

    // A broad external driving head stops at the access edge.  It is part of
    // the removable key, not a cosmetic block in either mating half.
    const headDepth = Math.max(w * 0.75, s * 0.12);
    const head = localBox(oc, frame,
        [u, path.entry - 0.04 - headDepth / 2, 0],
        [keyWidth * 1.32, headDepth, d * 0.34]);
    return {
        lower,
        upper,
        keys: [combine(oc, [key, retainer, head])],
        note: 'Mate the sloped scarf lap, then drive the separate tapered key from the negative-v side channel until its external head seats. Its thin leading tip enters first, the thick accessible tail preloads the lap, and the dovetail-waisted keeper captures both halves until deliberately slid back out; tune wedgePreload for the material.',
        print: { parts: ['n', '-n'], keys: ['n'] },
        printGuidance: 'Print the lower scarf slope upward, the upper pocket opening upward, and the removable key flat. Preserve the negative-v key entry; engage the scarf, then drive the key along +v until its head seats.'
    };
}

export const slidingFamilies = {
    dovetail: makeDovetail,
    jigsaw: makeJigsaw,
    'scarf-wedge': makeScarfWedge,
};
