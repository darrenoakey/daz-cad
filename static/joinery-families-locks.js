/**
 * Locking split-plane joinery families.
 *
 * All dimensions are local to the frame supplied by joinery.js: u/v lie in the
 * cut plane and n is its oriented normal.  These factories deliberately create
 * clearance volumes and physical insertion paths; none is a metadata-only lock.
 */
import { EPS, localBox, localCylinder, localPrism, fuse, cut, combine } from './joinery-kernel.js';

const clamp = (value, low, high) => Math.max(low, Math.min(high, value));

function localBounds(o) {
    const b = o.localBounds;
    if (!Array.isArray(b) || b.length !== 6 || !b.every(Number.isFinite)) {
        throw new Error('splitAndJoin: locking families require localBounds from the split framework');
    }
    return b;
}

/** The nearest exposed edge is the deterministic access edge for a placement. */
function accessEdge(o, p, axis) {
    const b = localBounds(o);
    const index = axis === 'u' ? 0 : 1;
    const low = b[index], high = b[index + 3], value = p[index];
    if (value < low - EPS || value > high + EPS) {
        throw new Error('splitAndJoin: connector position is outside the split body');
    }
    // The core may choose a boundary during automatic placement.  Explicit
    // placements always choose the nearer boundary, with the negative side as
    // the stable tie-breaker for reproducible coupons and print instructions.
    const requested = o.autoPlacement?.access?.[axis] ?? o.autoPlacement?.[axis];
    const side = requested === 'max' || requested === 1 ? 1
        : requested === 'min' || requested === -1 ? -1
        : value - low <= high - value ? -1 : 1;
    return { side, bound: side < 0 ? low : high, low, high };
}

function insertionSpan(edge, target, inward, reach, clearance) {
    const outer = edge.bound + edge.side * (reach * .42 + clearance);
    const inner = clamp(target + inward * reach, edge.low + clearance, edge.high - clearance);
    if (Math.abs(inner - outer) < EPS) throw new Error('splitAndJoin: insufficient accessible edge length for connector');
    return { start: outer, end: inner, length: Math.abs(inner - outer) };
}

function bowTieProfile(size, depth, clearance = 0) {
    const wing = Math.max(size * .42 + clearance, EPS * 10);
    const neck = Math.max(size * .13 + clearance, EPS * 10);
    const high = Math.max(depth * .78 + clearance, EPS * 10);
    const waist = Math.max(depth * .16 + clearance, EPS * 10);
    return [
        [-wing, -high], [-neck, -waist], [-neck, waist], [-wing, high],
        [wing, high], [neck, waist], [neck, -waist], [wing, -high],
    ];
}

function rectangularProfile(halfA, lowB, highB) {
    return [[-halfA, lowB], [halfA, lowB], [halfA, highB], [-halfA, highB]];
}

function outsideHead(oc, frame, p, axis, edge, span, width, height, depth, nCenter = 0) {
    const center = [...p, nCenter];
    // Keep the shoulder entirely beyond the body edge while overlapping the
    // externally protruding section of the key; it is a positive stop, not an
    // accidental solid intersection with the joined workpieces.
    const outerCenter = edge.bound + edge.side * (depth / 2 + EPS * 20);
    if (axis === 'u') center[0] = outerCenter; else center[1] = outerCenter;
    return axis === 'u'
        ? localBox(oc, frame, [center[0], center[1], center[2]], [depth, width, height])
        : localBox(oc, frame, [center[0], center[1], center[2]], [width, depth, height]);
}

/**
 * A removable bow-tie spline.  The neck crosses n=0 while its wings sit in
 * opposite halves, so normal separation is blocked until the key is withdrawn
 * through its open v-edge channel.
 */
function makeButterfly(oc, frame, p, o) {
    const { size: s, depth: d, clearance: c } = o;
    const [u] = p;
    const edge = accessEdge(o, p, 'v');
    const span = insertionSpan(edge, p[1], -edge.side, s * .82, c);
    const atU = profile => profile.map(([x, n]) => [u + x, n]);
    const pocket = localPrism(oc, frame, atU(bowTieProfile(s, d, c)), span.start, span.end, 'v');
    const lower = cut(oc, o.base.lower, pocket);
    const upper = cut(oc, o.base.upper, pocket);
    const keyBody = localPrism(oc, frame, atU(bowTieProfile(s, d, -c)), span.start, span.end, 'v');
    const head = outsideHead(oc, frame, p, 'v', edge, span, s * 1.05, d * 1.85, s * .35);
    return {
        lower, upper, keys: [combine(oc, [keyBody, head])],
        note: 'Slide the necked bow-tie spline in from the open edge until its external shoulder stops; the opposed wings lock seam-normal pull-out.',
        print: { parts: ['n', '-n'], keys: ['v'] },
    };
}

/**
 * Lower carries a notched tongue; upper carries its mating mortise.  A key
 * enters from an exposed u-side and passes through both upper sidewalls and
 * the tongue at n>0, mechanically preventing tongue extraction along n.
 */
function makeCrossKey(oc, frame, p, o) {
    const { size: s, depth: d, clearance: c } = o;
    const [u, v] = p;
    const keyLow = d * .28, keyHigh = d * .60;
    const edge = accessEdge(o, p, 'u');
    const span = insertionSpan(edge, u, -edge.side, s * .92, c);
    const passageProfile = rectangularProfile(s * .14 + c, keyLow - c, keyHigh + c)
        .map(([vv, nn]) => [v + vv, nn]);
    const keyProfile = rectangularProfile(Math.max(s * .14 - c, EPS * 20), keyLow + c, keyHigh - c)
        .map(([vv, nn]) => [v + vv, nn]);
    const passage = localPrism(oc, frame, passageProfile, span.start, span.end, 'u');
    const tongueRaw = localBox(oc, frame, [u, v, d * .32], [s * .90, s * .58, d * 1.28]);
    const tongue = cut(oc, tongueRaw, passage);
    const mortise = localBox(oc, frame, [u, v, d * .38], [s * .90 + 2 * c, s * .58 + 2 * c, d * 1.42]);
    const lower = fuse(oc, o.base.lower, tongue);
    const upper = cut(oc, cut(oc, o.base.upper, mortise), passage);
    const keyBody = localPrism(oc, frame, keyProfile, span.start, span.end, 'u');
    const head = outsideHead(oc, frame, p, 'u', edge, span, s * .48, d * .30, s * .34, (keyLow + keyHigh) / 2);
    return {
        lower, upper, keys: [combine(oc, [keyBody, head])],
        note: 'Seat the integral tongue in its upper mortise, then insert the transverse key from the exposed side until its shoulder stops; it crosses the tongue and both upper sidewalls above the seam.',
        print: { parts: ['n', '-n'], keys: ['n'] },
    };
}

function annularSector(radiusInner, radiusOuter, start, end, steps = 16) {
    const outer = [], inner = [];
    // Circumscribe the required swept radius: inscribed polygon chords would
    // otherwise intrude into a rotating lug's corner clearance.
    const outerVertexRadius = radiusOuter / Math.cos((end - start) / (2 * steps));
    for (let i = 0; i <= steps; i += 1) {
        const angle = start + (end - start) * i / steps;
        outer.push([Math.cos(angle) * outerVertexRadius, Math.sin(angle) * outerVertexRadius]);
        inner.push([Math.cos(angle) * radiusInner, Math.sin(angle) * radiusInner]);
    }
    return [...outer, ...inner.reverse()];
}

/**
 * A two-lug bayonet in its final, rotated position.  The upper has radial entry
 * windows at +/-u and two quarter-annular tracks ending at +/-v.  The track
 * ends are hard angular stops below material shoulders, therefore the final
 * lugs cannot move seam-normal unless the lower half is first quarter-turned.
 */
function makeBayonet(oc, frame, p, o) {
    if ((o.count ?? o.positions?.length ?? 1) > 1) {
        throw new Error('splitAndJoin: bayonet supports one rotation axis only; multiple bayonets require coaxial placement and are rejected');
    }
    const { size: s, depth: d, clearance: c } = o;
    const [u, v] = p;
    const coreRadius = s * .19;
    const lugRadial = s * .24;
    const lugWidth = s * .18;
    const lugHeight = d * .25;
    const lugN = d * .40;
    // Overlap the spigot radially so the lugs are fused to it, not merely
    // tangent to it (tangent solids are not a mechanically connected lug).
    const radiusMid = coreRadius + lugRadial * .40;
    const spigot = localCylinder(oc, frame, [u, v, d * .36], coreRadius, d * .78);
    const upperLug = localBox(oc, frame, [u, v + radiusMid, lugN], [lugWidth, lugRadial, lugHeight]);
    const lowerLug = localBox(oc, frame, [u, v - radiusMid, lugN], [lugWidth, lugRadial, lugHeight]);
    const male = combine(oc, [spigot, upperLug, lowerLug]);

    const socket = localCylinder(oc, frame, [u, v, d * .43], coreRadius + c, d * .90);
    const trackStart = lugN - lugHeight / 2 - c;
    const trackEnd = lugN + lugHeight / 2 + c;
    const ringInner = coreRadius - lugRadial * .15 - c;
    const ringOuter = Math.hypot(radiusMid + lugRadial / 2, lugWidth / 2) + c;
    // The angular margin admits the rectangular lug corners at its final +/−v
    // pose, while the bounded sectors retain a hard stop just beyond that pose.
    const angularMargin = Math.asin((lugWidth / 2 + c) / (coreRadius + c));
    if (!Number.isFinite(angularMargin) || angularMargin >= Math.PI / 4) {
        throw new Error('splitAndJoin: bayonet clearance leaves no material for angular stops');
    }
    // Rotation is counter-clockwise from +u to +v, and simultaneously from -u
    // to -v; both final +/-v lugs share one n-axis rotation.
    const atConnector = polygon => polygon.map(([x, y]) => [u + x, v + y]);
    const firstTrack = localPrism(oc, frame,
        atConnector(annularSector(ringInner, ringOuter, -angularMargin, Math.PI / 2 + angularMargin)), trackStart, trackEnd, 'n');
    const secondTrack = localPrism(oc, frame,
        atConnector(annularSector(ringInner, ringOuter, Math.PI - angularMargin, Math.PI * 1.5 + angularMargin)), trackStart, trackEnd, 'n');
    const entryExtent = ringOuter + c;
    // Entry windows run from the seam through the lug-track height.  A window
    // confined to the lug band would make the advertised axial entry impossible.
    const entryHeight = trackEnd + d * .16;
    const entryN = (trackEnd - d * .16) / 2;
    const entryPlus = localBox(oc, frame, [u + entryExtent / 2, v, entryN], [entryExtent, lugWidth + 2 * c, entryHeight]);
    const entryMinus = localBox(oc, frame, [u - entryExtent / 2, v, entryN], [entryExtent, lugWidth + 2 * c, entryHeight]);
    const cavity = combine(oc, [socket, firstTrack, secondTrack, entryPlus, entryMinus]);
    const lower = fuse(oc, o.base.lower, male);
    const upper = cut(oc, o.base.upper, cavity);
    return {
        lower, upper, keys: [],
        note: 'With the lower half quarter-turned, pass both lugs through the +/-u entry windows; turn it counter-clockwise until the +/-v track ends stop under the retaining shoulders.',
        print: { parts: ['n', '-n'], keys: [] },
        assembly: { axis: 'n', finalRotationDegrees: 90, entryLugAxis: 'u', finalLugAxis: 'v' },
    };
}

/**
 * A removable exterior U clip.  Its bridge remains wholly beyond the nearest
 * u edge; only its slim lips enter open v-side rail recesses in each half.  It
 * never places a solid bridge through either part's interior.
 */
function makeBridgeClip(oc, frame, p, o) {
    const { size: s, depth: d, clearance: c, wall: w } = o;
    const [u, v] = p;
    const uEdge = accessEdge(o, p, 'u');
    const vEdge = accessEdge(o, p, 'v');
    const vSpan = insertionSpan(vEdge, v, -vEdge.side, s * 1.00, c);
    const railDepth = Math.max(w * 1.35, s * .22);
    const railHeight = Math.max(w * 1.15, d * .24);
    const railN = d * .42;
    const inwardU = -uEdge.side;
    const railU = uEdge.bound + inwardU * railDepth / 2;
    const railV = (vSpan.start + vSpan.end) / 2;
    const railLength = vSpan.length + 2 * c;
    const upperRail = localBox(oc, frame, [railU, railV, railN], [railDepth + 2 * c, railLength, railHeight + 2 * c]);
    const lowerRail = localBox(oc, frame, [railU, railV, -railN], [railDepth + 2 * c, railLength, railHeight + 2 * c]);
    const lower = cut(oc, o.base.lower, lowerRail);
    const upper = cut(oc, o.base.upper, upperRail);

    const exteriorU = uEdge.bound + uEdge.side * w / 2;
    const lipWidth = w + railDepth - 2 * c;
    const lipU = uEdge.bound + uEdge.side * w / 2 + inwardU * railDepth / 2;
    const bridge = localBox(oc, frame, [exteriorU, railV, 0], [w, vSpan.length - 2 * c, 2 * railN + railHeight]);
    const upperLip = localBox(oc, frame, [lipU, railV, railN], [lipWidth, vSpan.length - 2 * c, railHeight - 2 * c]);
    const lowerLip = localBox(oc, frame, [lipU, railV, -railN], [lipWidth, vSpan.length - 2 * c, railHeight - 2 * c]);
    return {
        lower, upper, keys: [combine(oc, [bridge, upperLip, lowerLip])],
        note: 'Butt the halves, then slide the external U clip in from the open edge; its two lips engage the opposed side rail recesses while the bridge stays outside the body.',
        print: { parts: ['n', '-n'], keys: ['v'] },
    };
}

export { makeButterfly, makeCrossKey, makeBayonet, makeBridgeClip };
