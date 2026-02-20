/**
 * naming.js - Named references system for daz-cad
 *
 * Extends Workplane with semantic face/edge names that survive transforms and booleans.
 * Provides high-level relative operations (extrudeOn, cutInto, alignTo, etc.).
 *
 * Convention: Front=+Y, Back=-Y, Right=+X, Left=-X, Top=+Z, Bottom=-Z
 *
 * Example usage:
 *   const box = new Workplane("XY").box(10, 20, 30);
 *   box.faces("front")  // same as faces(">Y")
 *   box.extrudeOn("front", 5, 5, 3)  // extrude box outward from front face
 */

import { Workplane, getOC } from '/static/cad.js';


// ============================================================
// CANONICAL FACE NAMES BY NORMAL DIRECTION
// ============================================================

const CANONICAL_NAMES = [
    { name: 'right',  normal: [ 1,  0,  0] },
    { name: 'left',   normal: [-1,  0,  0] },
    { name: 'front',  normal: [ 0,  1,  0] },
    { name: 'back',   normal: [ 0, -1,  0] },
    { name: 'top',    normal: [ 0,  0,  1] },
    { name: 'bottom', normal: [ 0,  0, -1] },
];

// Threshold for dot product to consider normals "aligned"
const NORMAL_THRESHOLD = 0.95;


// ============================================================
// HELPER FUNCTIONS
// ============================================================

function _dotProduct(a, b) {
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
}

function _vecLength(v) {
    return Math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]);
}

function _normalize(v) {
    const len = _vecLength(v);
    if (len < 1e-10) return [0, 0, 0];
    return [v[0] / len, v[1] / len, v[2] / len];
}

function _vecDistance(a, b) {
    const dx = a[0] - b[0], dy = a[1] - b[1], dz = a[2] - b[2];
    return Math.sqrt(dx * dx + dy * dy + dz * dz);
}

/**
 * Apply a rotation matrix to a 3D vector
 * @param {number[]} v - [x,y,z]
 * @param {number[]} axis - rotation axis [ax,ay,az] (normalized)
 * @param {number} angleDeg - rotation angle in degrees
 * @returns {number[]} rotated vector
 */
function _rotateVector(v, axis, angleDeg) {
    const rad = angleDeg * Math.PI / 180;
    const cos = Math.cos(rad);
    const sin = Math.sin(rad);
    const [ux, uy, uz] = _normalize(axis);
    const dot = ux * v[0] + uy * v[1] + uz * v[2];
    // Rodrigues' rotation formula: v*cos + (u×v)*sin + u*(u·v)*(1-cos)
    return [
        v[0] * cos + (uy * v[2] - uz * v[1]) * sin + ux * dot * (1 - cos),
        v[1] * cos + (uz * v[0] - ux * v[2]) * sin + uy * dot * (1 - cos),
        v[2] * cos + (ux * v[1] - uy * v[0]) * sin + uz * dot * (1 - cos),
    ];
}


// ============================================================
// FACE PROPERTY COMPUTATION
// ============================================================

/**
 * Compute normal, centroid, area, and planarity for an OC face in a single pass.
 * Combines what were separate _computeFaceProps and _isFacePlanar calls
 * to avoid creating multiple BRepAdaptor_Surface instances.
 * @returns {{ normal: number[], centroid: number[], area: number, isPlanar: boolean }}
 */
function _computeFaceProps(face) {
    const oc = getOC();

    // Centroid and area via GProp
    const props = new oc.GProp_GProps_1();
    oc.BRepGProp.SurfaceProperties_1(face, props, false, false);
    const center = props.CentreOfMass();
    const area = props.Mass();
    const centroid = [center.X(), center.Y(), center.Z()];
    props.delete();

    // Normal via BRepAdaptor_Surface + D1 cross product
    const adaptor = new oc.BRepAdaptor_Surface_2(face, true);
    const uMin = adaptor.FirstUParameter();
    const uMax = adaptor.LastUParameter();
    const vMin = adaptor.FirstVParameter();
    const vMax = adaptor.LastVParameter();
    const uMid = (uMin + uMax) / 2;
    const vMid = (vMin + vMax) / 2;

    const pnt = new oc.gp_Pnt_1();
    const d1u = new oc.gp_Vec_1();
    const d1v = new oc.gp_Vec_1();
    adaptor.D1(uMid, vMid, pnt, d1u, d1v);

    let normalVec = d1u.Crossed(d1v);
    if (face.Orientation_1() === oc.TopAbs_Orientation.TopAbs_REVERSED) {
        normalVec.Reverse();
    }
    const mag = normalVec.Magnitude();
    const normal = mag > 1e-10
        ? [normalVec.X() / mag, normalVec.Y() / mag, normalVec.Z() / mag]
        : [0, 0, 1];

    // Check planarity: sample a second point and compare normals
    let isPlanar = true;
    const pnt2 = new oc.gp_Pnt_1();
    const d1u2 = new oc.gp_Vec_1();
    const d1v2 = new oc.gp_Vec_1();
    const uQ = uMin + (uMax - uMin) * 0.25;
    const vQ = vMin + (vMax - vMin) * 0.25;
    adaptor.D1(uQ, vQ, pnt2, d1u2, d1v2);
    const n2 = d1u2.Crossed(d1v2);
    const mag2 = n2.Magnitude();
    if (mag > 1e-10 && mag2 > 1e-10) {
        const dot = (normalVec.X() * n2.X() + normalVec.Y() * n2.Y() + normalVec.Z() * n2.Z()) / (mag * mag2);
        isPlanar = Math.abs(dot) > 0.99;
    }

    adaptor.delete();
    pnt.delete(); d1u.delete(); d1v.delete();
    pnt2.delete(); d1u2.delete(); d1v2.delete();

    return { normal, centroid, area, isPlanar };
}

/**
 * Enumerate all faces of a shape and compute their properties
 * @returns {Array<{ face, normal, centroid, area, isPlanar }>}
 */
function _enumerateFaces(shape) {
    const oc = getOC();
    const explorer = new oc.TopExp_Explorer_2(
        shape,
        oc.TopAbs_ShapeEnum.TopAbs_FACE,
        oc.TopAbs_ShapeEnum.TopAbs_SHAPE
    );
    const result = [];
    while (explorer.More()) {
        const face = oc.TopoDS.Face_1(explorer.Current());
        const props = _computeFaceProps(face);
        result.push({ face, ...props });
        explorer.Next();
    }
    explorer.delete();
    return result;
}


// ============================================================
// AUTO-NAMING LOGIC
// ============================================================

/**
 * Assign canonical names to faces based on their normals
 * Returns { name: FaceRef } map
 */
function _autoNameFaces(facePropsList) {
    const named = {};
    const usedNames = new Set();

    for (const { normal, centroid, area } of facePropsList) {
        for (const canonical of CANONICAL_NAMES) {
            const dot = _dotProduct(normal, canonical.normal);
            if (dot > NORMAL_THRESHOLD && !usedNames.has(canonical.name)) {
                named[canonical.name] = { normal: [...normal], centroid: [...centroid], area };
                usedNames.add(canonical.name);
                break;
            }
        }
    }
    return named;
}

/**
 * Auto-name faces for a cylinder: top, bottom, side
 */
function _autoNameCylinderFaces(facePropsList) {
    const named = {};

    for (const { normal, centroid, area } of facePropsList) {
        const isPlanar = Math.abs(Math.abs(normal[2]) - 1) < 0.05;
        if (isPlanar) {
            if (normal[2] > 0 && !named.top) {
                named.top = { normal: [...normal], centroid: [...centroid], area };
            } else if (normal[2] < 0 && !named.bottom) {
                named.bottom = { normal: [...normal], centroid: [...centroid], area };
            }
        } else if (!named.side) {
            // Curved face — average normal is outward radially
            named.side = { normal: [...normal], centroid: [...centroid], area };
        }
    }
    return named;
}

/**
 * Auto-name edges as "faceA-faceB" where faceA < faceB alphabetically
 * Only edges bordering two named faces get names
 */
function _autoNameEdges(shape, namedFaces) {
    const oc = getOC();
    if (!shape || Object.keys(namedFaces).length === 0) return {};

    // Build map: edgeHash → Set of face names
    const edgeFaceMap = {};

    // For each named face, find its edges and record the face name
    const allFaces = _enumerateFaces(shape);

    for (const { face, normal, centroid, area } of allFaces) {
        // Find which named face this is (by matching centroid/normal)
        let faceName = null;
        let bestDist = Infinity;
        for (const [name, ref] of Object.entries(namedFaces)) {
            const dot = _dotProduct(normal, ref.normal);
            const dist = _vecDistance(centroid, ref.centroid);
            if (dot > 0.95 && dist < 1.0 && dist < bestDist) {
                faceName = name;
                bestDist = dist;
            }
        }
        if (!faceName) continue;

        // Enumerate edges of this face
        const edgeExplorer = new oc.TopExp_Explorer_2(
            face,
            oc.TopAbs_ShapeEnum.TopAbs_EDGE,
            oc.TopAbs_ShapeEnum.TopAbs_SHAPE
        );
        while (edgeExplorer.More()) {
            const edge = oc.TopoDS.Edge_1(edgeExplorer.Current());
            const hash = edge.HashCode(1000000);
            if (!edgeFaceMap[hash]) {
                edgeFaceMap[hash] = { names: new Set(), edge };
            }
            edgeFaceMap[hash].names.add(faceName);
            edgeExplorer.Next();
        }
        edgeExplorer.delete();
    }

    // Edges with exactly 2 named faces get compound name
    const namedEdges = {};
    for (const { names, edge } of Object.values(edgeFaceMap)) {
        if (names.size === 2) {
            const sorted = [...names].sort();
            const edgeName = sorted.join('-');
            if (!namedEdges[edgeName]) {
                // Compute edge geometry
                const curve = new oc.BRepAdaptor_Curve_2(edge);
                const first = curve.FirstParameter();
                const last = curve.LastParameter();
                const p1 = curve.Value(first);
                const p2 = curve.Value(last);
                const mid = curve.Value((first + last) / 2);

                const dx = p2.X() - p1.X(), dy = p2.Y() - p1.Y(), dz = p2.Z() - p1.Z();
                const len = Math.sqrt(dx * dx + dy * dy + dz * dz);
                const direction = len > 1e-6 ? [dx / len, dy / len, dz / len] : [0, 0, 0];
                const midpoint = [mid.X(), mid.Y(), mid.Z()];

                namedEdges[edgeName] = { midpoint, direction, length: len };

                curve.delete();
                p1.delete();
                p2.delete();
                mid.delete();
            }
        }
    }

    return namedEdges;
}


// ============================================================
// FACE SIMILARITY SCORING FOR BOOLEAN RE-MATCHING
// ============================================================

/**
 * Score how similar a live face is to a stored FaceRef
 * Returns 0..1 (1 = perfect match)
 */
function _faceSimilarityScore(liveProps, storedRef, shapeSize) {
    // Normal similarity: dot product (50% weight)
    const normalDot = _dotProduct(liveProps.normal, storedRef.normal);
    const normalScore = Math.max(0, normalDot); // 0 if perpendicular or opposing

    // Centroid proximity (35% weight) — normalized by shape bounding sphere
    const dist = _vecDistance(liveProps.centroid, storedRef.centroid);
    const maxDist = shapeSize > 0 ? shapeSize : 100;
    const centroidScore = Math.max(0, 1 - dist / maxDist);

    // Area ratio (15% weight) — ratio closer to 1 is better
    const areaRatio = storedRef.area > 1e-10
        ? Math.min(liveProps.area, storedRef.area) / Math.max(liveProps.area, storedRef.area)
        : 0;

    return 0.50 * normalScore + 0.35 * centroidScore + 0.15 * areaRatio;
}

/**
 * Re-match named faces after a boolean operation
 * Uses greedy best-match assignment
 */
function _rematchFaces(shape, oldNamedFaces) {
    if (!shape || Object.keys(oldNamedFaces).length === 0) return {};

    const oc = getOC();

    // Compute shape bounding diagonal for normalization
    const bndBox = new oc.Bnd_Box_1();
    oc.BRepBndLib.Add(shape, bndBox, false);
    const xMin = { current: 0 }, yMin = { current: 0 }, zMin = { current: 0 };
    const xMax = { current: 0 }, yMax = { current: 0 }, zMax = { current: 0 };
    bndBox.Get(xMin, yMin, zMin, xMax, yMax, zMax);
    bndBox.delete();
    const dx = xMax.current - xMin.current;
    const dy = yMax.current - yMin.current;
    const dz = zMax.current - zMin.current;
    const shapeSize = Math.sqrt(dx * dx + dy * dy + dz * dz);

    // Enumerate live faces (isPlanar computed in same pass)
    const liveFaces = _enumerateFaces(shape);

    // Only match planar faces (curved faces can have misleading normals)
    const planarLive = liveFaces.filter(f => f.isPlanar);

    // Build score matrix: [nameIdx][faceIdx] = score
    const nameEntries = Object.entries(oldNamedFaces);
    const scores = [];
    for (const [, ref] of nameEntries) {
        const row = planarLive.map(f => _faceSimilarityScore(f, ref, shapeSize));
        scores.push(row);
    }

    // Greedy assignment: pick best score, assign, remove both from candidates
    const assigned = {};
    const usedFaces = new Set();
    const usedNames = new Set();
    const minThreshold = 0.3;

    for (let round = 0; round < nameEntries.length; round++) {
        let bestScore = -1;
        let bestName = -1;
        let bestFace = -1;

        for (let ni = 0; ni < nameEntries.length; ni++) {
            if (usedNames.has(ni)) continue;
            for (let fi = 0; fi < planarLive.length; fi++) {
                if (usedFaces.has(fi)) continue;
                if (scores[ni][fi] > bestScore) {
                    bestScore = scores[ni][fi];
                    bestName = ni;
                    bestFace = fi;
                }
            }
        }

        if (bestScore < minThreshold) break;

        const [name] = nameEntries[bestName];
        const live = planarLive[bestFace];
        assigned[name] = {
            normal: [...live.normal],
            centroid: [...live.centroid],
            area: live.area
        };
        usedNames.add(bestName);
        usedFaces.add(bestFace);
    }

    return assigned;
}


// ============================================================
// RESOLVE FACE NAME → OC FACE
// ============================================================

/**
 * Find the actual OC face(s) matching a named FaceRef
 * Matches by normal direction and centroid proximity
 */
function _resolveNamedFace(shape, faceRef) {
    const oc = getOC();

    // Compute shape size for distance tolerance
    const bndBox = new oc.Bnd_Box_1();
    oc.BRepBndLib.Add(shape, bndBox, false);
    const xMin = { current: 0 }, yMin = { current: 0 }, zMin = { current: 0 };
    const xMax = { current: 0 }, yMax = { current: 0 }, zMax = { current: 0 };
    bndBox.Get(xMin, yMin, zMin, xMax, yMax, zMax);
    bndBox.delete();
    const dx = xMax.current - xMin.current;
    const dy = yMax.current - yMin.current;
    const dz = zMax.current - zMin.current;
    const shapeSize = Math.sqrt(dx * dx + dy * dy + dz * dz);
    // Distance tolerance: 10% of shape diagonal, min 1mm
    const distTol = Math.max(1.0, shapeSize * 0.1);

    const explorer = new oc.TopExp_Explorer_2(
        shape,
        oc.TopAbs_ShapeEnum.TopAbs_FACE,
        oc.TopAbs_ShapeEnum.TopAbs_SHAPE
    );

    // Find best-matching face by normal + proximity
    let bestFace = null;
    let bestScore = -1;

    while (explorer.More()) {
        const face = oc.TopoDS.Face_1(explorer.Current());
        const props = _computeFaceProps(face);
        const normalDot = _dotProduct(props.normal, faceRef.normal);
        const dist = _vecDistance(props.centroid, faceRef.centroid);

        if (normalDot > 0.9) {
            const score = normalDot * 0.6 + Math.max(0, 1 - dist / distTol) * 0.4;
            if (score > bestScore) {
                bestScore = score;
                bestFace = face;
            }
        }
        explorer.Next();
    }
    explorer.delete();
    return bestFace && bestScore > 0.3 ? [bestFace] : [];
}

/**
 * Find OC edges matching a named EdgeRef
 */
function _resolveNamedEdge(shape, edgeRef) {
    const oc = getOC();
    const explorer = new oc.TopExp_Explorer_2(
        shape,
        oc.TopAbs_ShapeEnum.TopAbs_EDGE,
        oc.TopAbs_ShapeEnum.TopAbs_SHAPE
    );

    const matches = [];
    const seen = new Set();
    while (explorer.More()) {
        const edge = oc.TopoDS.Edge_1(explorer.Current());
        const hash = edge.HashCode(1000000);
        if (!seen.has(hash)) {
            seen.add(hash);
            try {
                const curve = new oc.BRepAdaptor_Curve_2(edge);
                const first = curve.FirstParameter();
                const last = curve.LastParameter();
                const mid = curve.Value((first + last) / 2);
                const midpoint = [mid.X(), mid.Y(), mid.Z()];
                const dist = _vecDistance(midpoint, edgeRef.midpoint);
                if (dist < 1.0) {
                    matches.push(edge);
                }
                curve.delete();
                mid.delete();
            } catch (e) {
                // skip problematic edges
            }
        }
        explorer.Next();
    }
    explorer.delete();
    return matches;
}


// ============================================================
// LAZY EDGE NAMING
// ============================================================

/**
 * Ensure _namedFaces is computed. Called lazily on first face name access.
 * Resolves _pendingAutoName from box()/cylinder() calls.
 */
function _ensureNamedFaces(wp) {
    if (wp._namedFaces) return; // already computed
    if (!wp._pendingAutoName || !wp._shape) return;

    const faceProps = _enumerateFaces(wp._shape);
    if (wp._pendingAutoName === 'cylinder') {
        wp._namedFaces = _autoNameCylinderFaces(faceProps);
    } else {
        wp._namedFaces = _autoNameFaces(faceProps);
    }
    wp._pendingAutoName = null;
}

/**
 * Ensure _namedEdges is computed. Called lazily on first edge access.
 */
function _ensureNamedEdges(wp) {
    if (wp._namedEdges !== null && wp._namedEdges !== undefined) return; // already computed (or explicitly empty {})
    _ensureNamedFaces(wp);
    if (!wp._namedFaces || !wp._shape) {
        wp._namedEdges = {};
        return;
    }
    wp._namedEdges = _autoNameEdges(wp._shape, wp._namedFaces);
}


// ============================================================
// CHECK IF SELECTOR IS A NAME (not axis selector like ">Z")
// ============================================================

function _isAxisSelector(selector) {
    // Single axis selector: >X, <Y, |Z
    return /^[|><][XYZxyz]$/.test(selector.trim());
}

/**
 * Check if selector contains a named reference (not just axis selectors)
 * Handles compound selectors like "front and top" or "base.front"
 */
function _hasNamedSelector(selector) {
    if (!selector || typeof selector !== 'string') return false;
    // If it's purely axis selectors (possibly compound), return false
    const parts = selector.split(/\s+(?:and|or)\s+/i);
    return parts.some(p => !_isAxisSelector(p));
}


// ============================================================
// WRAP _cloneProperties
// ============================================================

const _origCloneProperties = Workplane.prototype._cloneProperties;

Workplane.prototype._cloneProperties = function(source) {
    _origCloneProperties.call(this, source);

    // Deep-clone naming data
    if (source._namedFaces) {
        this._namedFaces = {};
        for (const [name, ref] of Object.entries(source._namedFaces)) {
            this._namedFaces[name] = {
                normal: [...ref.normal],
                centroid: [...ref.centroid],
                area: ref.area
            };
        }
    } else {
        this._namedFaces = null;
    }

    if (source._namedEdges) {
        this._namedEdges = {};
        for (const [name, ref] of Object.entries(source._namedEdges)) {
            this._namedEdges[name] = {
                midpoint: [...ref.midpoint],
                direction: [...ref.direction],
                length: ref.length
            };
        }
    } else {
        this._namedEdges = null;
    }

    this._shapeName = source._shapeName || null;
    this._pendingAutoName = source._pendingAutoName || null;

    if (source._subParts) {
        this._subParts = {};
        for (const [partName, part] of Object.entries(source._subParts)) {
            this._subParts[partName] = {
                namedFaces: { ...part.namedFaces },
                namedEdges: { ...part.namedEdges }
            };
        }
    } else {
        this._subParts = null;
    }

    return this;
};


// ============================================================
// WRAP box() — auto-name faces after creation
// ============================================================

const _origBox = Workplane.prototype.box;

Workplane.prototype.box = function(length, width, height, centered = true) {
    const result = _origBox.call(this, length, width, height, centered);
    if (result._shape && !result._shape.IsNull()) {
        const faceProps = _enumerateFaces(result._shape);
        result._namedFaces = _autoNameFaces(faceProps);
        // Edge naming is lazy — computed on first access
    }
    return result;
};


// ============================================================
// WRAP cylinder() — auto-name faces after creation
// ============================================================

const _origCylinder = Workplane.prototype.cylinder;

Workplane.prototype.cylinder = function(arg1, arg2) {
    const result = _origCylinder.call(this, arg1, arg2);
    if (result._shape && !result._shape.IsNull()) {
        const faceProps = _enumerateFaces(result._shape);
        result._namedFaces = _autoNameCylinderFaces(faceProps);
        // Edge naming is lazy — computed on first access
    }
    return result;
};


// ============================================================
// WRAP translate() — transform stored vectors
// ============================================================

const _origTranslate = Workplane.prototype.translate;

Workplane.prototype.translate = function(x, y, z) {
    const result = _origTranslate.call(this, x, y, z);

    // Translate centroids (normals don't change under translation)
    if (result._namedFaces) {
        for (const ref of Object.values(result._namedFaces)) {
            ref.centroid[0] += x;
            ref.centroid[1] += y;
            ref.centroid[2] += z;
        }
    }
    if (result._namedEdges) {
        for (const ref of Object.values(result._namedEdges)) {
            ref.midpoint[0] += x;
            ref.midpoint[1] += y;
            ref.midpoint[2] += z;
        }
    }
    if (result._subParts) {
        for (const part of Object.values(result._subParts)) {
            for (const ref of Object.values(part.namedFaces)) {
                ref.centroid[0] += x;
                ref.centroid[1] += y;
                ref.centroid[2] += z;
            }
            for (const ref of Object.values(part.namedEdges)) {
                ref.midpoint[0] += x;
                ref.midpoint[1] += y;
                ref.midpoint[2] += z;
            }
        }
    }

    return result;
};


// ============================================================
// WRAP rotate() — transform stored vectors
// ============================================================

const _origRotate = Workplane.prototype.rotate;

Workplane.prototype.rotate = function(axisX, axisY, axisZ, angleDegrees) {
    const result = _origRotate.call(this, axisX, axisY, axisZ, angleDegrees);
    const axis = [axisX, axisY, axisZ];

    if (result._namedFaces) {
        for (const ref of Object.values(result._namedFaces)) {
            ref.normal = _rotateVector(ref.normal, axis, angleDegrees);
            ref.centroid = _rotateVector(ref.centroid, axis, angleDegrees);
        }
    }
    if (result._namedEdges) {
        for (const ref of Object.values(result._namedEdges)) {
            ref.midpoint = _rotateVector(ref.midpoint, axis, angleDegrees);
            ref.direction = _rotateVector(ref.direction, axis, angleDegrees);
        }
    }
    if (result._subParts) {
        for (const part of Object.values(result._subParts)) {
            for (const ref of Object.values(part.namedFaces)) {
                ref.normal = _rotateVector(ref.normal, axis, angleDegrees);
                ref.centroid = _rotateVector(ref.centroid, axis, angleDegrees);
            }
            for (const ref of Object.values(part.namedEdges)) {
                ref.midpoint = _rotateVector(ref.midpoint, axis, angleDegrees);
                ref.direction = _rotateVector(ref.direction, axis, angleDegrees);
            }
        }
    }

    return result;
};


// ============================================================
// WRAP union(), cut(), intersect() — re-match faces
// ============================================================

function _wrapBoolean(origMethod, methodName) {
    return function(other) {
        const result = origMethod.call(this, other);

        // Resolve pending auto-names before checking
        _ensureNamedFaces(this);
        if (other) _ensureNamedFaces(other);

        // Skip expensive re-matching if neither operand has named faces
        const thisHasNames = this._namedFaces && Object.keys(this._namedFaces).length > 0;
        const otherHasNames = other && other._namedFaces && Object.keys(other._namedFaces).length > 0;

        if (!thisHasNames && !otherHasNames) {
            return result;
        }

        if (result._shape && !result._shape.IsNull()) {
            // Merge named faces from both operands, then re-match
            const combined = {};
            if (thisHasNames) Object.assign(combined, this._namedFaces);
            if (otherHasNames) {
                for (const [name, ref] of Object.entries(other._namedFaces)) {
                    if (!combined[name]) {
                        combined[name] = ref;
                    }
                }
            }

            if (Object.keys(combined).length > 0) {
                result._namedFaces = _rematchFaces(result._shape, combined);
                result._namedEdges = null; // lazy — computed on first access
            }

            // Store sub-parts for dotted access (only when shapes are named)
            if (this._shapeName || (other && other._shapeName)) {
                result._subParts = result._subParts || {};
                if (this._shapeName && thisHasNames) {
                    result._subParts[this._shapeName] = {
                        namedFaces: _rematchFaces(result._shape, this._namedFaces),
                        namedEdges: {}
                    };
                }
                if (other && other._shapeName && otherHasNames) {
                    result._subParts[other._shapeName] = {
                        namedFaces: _rematchFaces(result._shape, other._namedFaces),
                        namedEdges: {}
                    };
                }
            }
        }

        return result;
    };
}

const _origUnion = Workplane.prototype.union;
const _origCut = Workplane.prototype.cut;
const _origIntersect = Workplane.prototype.intersect;

Workplane.prototype.union = _wrapBoolean(_origUnion, 'union');
Workplane.prototype.cut = _wrapBoolean(_origCut, 'cut');
Workplane.prototype.intersect = _wrapBoolean(_origIntersect, 'intersect');


// ============================================================
// WRAP faces() and _filterFaces() — resolve names
// ============================================================

const _origFaces = Workplane.prototype.faces;
const _origFilterFaces = Workplane.prototype._filterFaces;

Workplane.prototype.faces = function(selector = null) {
    if (!selector || !_hasNamedSelector(selector)) {
        return _origFaces.call(this, selector);
    }

    // Named selector — resolve by geometry matching
    const result = new Workplane(this._plane);
    result._cloneProperties(this);
    result._shape = this._shape;
    result._selectionMode = 'faces';
    result._selectedFaces = [];

    _ensureNamedFaces(this);
    if (!this._shape || !this._namedFaces) return result;

    // Handle compound named selectors ("front and top" is meaningless for faces,
    // but "front or top" could select both)
    const orParts = selector.split(/\s+or\s+/i);
    if (orParts.length > 1) {
        const allMatches = [];
        const seen = new Set();
        for (const part of orParts) {
            const trimmed = part.trim();
            let partFaces;
            if (_isAxisSelector(trimmed)) {
                // Delegate axis selectors to original
                const allFaces = _getAllFaces(this._shape);
                partFaces = _origFilterFaces.call(this, allFaces, trimmed);
            } else {
                partFaces = this._resolveNamedFacesFromSelector(trimmed);
            }
            for (const f of partFaces) {
                const hash = f.HashCode(1000000);
                if (!seen.has(hash)) {
                    seen.add(hash);
                    allMatches.push(f);
                }
            }
        }
        result._selectedFaces = allMatches;
        return result;
    }

    result._selectedFaces = this._resolveNamedFacesFromSelector(selector.trim());
    return result;
};

/**
 * Resolve a single named face selector to OC faces
 * Handles dotted notation like "base.front"
 */
Workplane.prototype._resolveNamedFacesFromSelector = function(name) {
    if (!this._shape) return [];
    _ensureNamedFaces(this);

    // Check for dotted sub-part access: "partName.faceName"
    const dotIdx = name.indexOf('.');
    if (dotIdx >= 0) {
        const partName = name.substring(0, dotIdx);
        const faceName = name.substring(dotIdx + 1);
        if (this._subParts && this._subParts[partName] &&
            this._subParts[partName].namedFaces[faceName]) {
            return _resolveNamedFace(this._shape, this._subParts[partName].namedFaces[faceName]);
        }
        return [];
    }

    // Direct name lookup
    if (this._namedFaces && this._namedFaces[name]) {
        return _resolveNamedFace(this._shape, this._namedFaces[name]);
    }

    // Check sub-parts for non-dotted access
    if (this._subParts) {
        for (const part of Object.values(this._subParts)) {
            if (part.namedFaces[name]) {
                return _resolveNamedFace(this._shape, part.namedFaces[name]);
            }
        }
    }

    return [];
};

Workplane.prototype._filterFaces = function(faces, selector) {
    if (_hasNamedSelector(selector)) {
        // Named selector — resolve to faces, then filter the input list
        const resolved = this._resolveNamedFacesFromSelector(selector.trim());
        if (resolved.length > 0) {
            const resolvedHashes = new Set(resolved.map(f => f.HashCode(1000000)));
            return faces.filter(f => resolvedHashes.has(f.HashCode(1000000)));
        }
        return [];
    }
    return _origFilterFaces.call(this, faces, selector);
};


// Helper to get all faces from a shape
function _getAllFaces(shape) {
    const oc = getOC();
    const explorer = new oc.TopExp_Explorer_2(
        shape,
        oc.TopAbs_ShapeEnum.TopAbs_FACE,
        oc.TopAbs_ShapeEnum.TopAbs_SHAPE
    );
    const faces = [];
    while (explorer.More()) {
        faces.push(oc.TopoDS.Face_1(explorer.Current()));
        explorer.Next();
    }
    explorer.delete();
    return faces;
}


// ============================================================
// WRAP edges() and _filterEdges() — resolve compound names
// ============================================================

const _origEdges = Workplane.prototype.edges;
const _origFilterEdges = Workplane.prototype._filterEdges;
const _origFilterEdgesSingle = Workplane.prototype._filterEdgesSingle;

Workplane.prototype.edges = function(selector = null) {
    if (!selector || !_hasNamedSelector(selector)) {
        return _origEdges.call(this, selector);
    }

    // Named edge selector
    const result = new Workplane(this._plane);
    result._cloneProperties(this);
    result._shape = this._shape;
    result._selectionMode = 'edges';
    result._selectedEdges = [];

    if (!this._shape) return result;

    // Check for named edge like "front-top" (lazy compute)
    _ensureNamedEdges(this);
    if (this._namedEdges && this._namedEdges[selector.trim()]) {
        result._selectedEdges = _resolveNamedEdge(this._shape, this._namedEdges[selector.trim()]);
        return result;
    }

    // Fall back to original for axis selectors
    return _origEdges.call(this, selector);
};

Workplane.prototype._filterEdges = function(edges, selector) {
    if (_hasNamedSelector(selector)) {
        _ensureNamedEdges(this);
        const trimmed = selector.trim();
        if (this._namedEdges && this._namedEdges[trimmed]) {
            const resolved = _resolveNamedEdge(this._shape, this._namedEdges[trimmed]);
            const resolvedHashes = new Set(resolved.map(e => e.HashCode(1000000)));
            return edges.filter(e => resolvedHashes.has(e.HashCode(1000000)));
        }
        return [];
    }
    return _origFilterEdges.call(this, edges, selector);
};


// ============================================================
// CUSTOM NAMING API
// ============================================================

/**
 * Name the whole shape for sub-part access after boolean ops
 * @param {string} shapeName
 * @returns {Workplane}
 */
Workplane.prototype.name = function(shapeName) {
    const oc = getOC();
    const result = new Workplane(this._plane);
    result._shape = this._shape;
    result._cloneProperties(this);
    result._shapeName = shapeName;
    return result;
};

/**
 * Add a custom name for a face matching a selector
 * @param {string} selector - Axis selector (">Z") or existing name
 * @param {string} customName - New name to assign
 * @returns {Workplane}
 */
Workplane.prototype.nameFace = function(selector, customName) {
    const result = new Workplane(this._plane);
    result._shape = this._shape;
    result._cloneProperties(this);
    _ensureNamedFaces(result);
    if (!result._namedFaces) result._namedFaces = {};

    // Resolve the selector to find the face
    const selectedWp = this.faces(selector);
    if (selectedWp._selectedFaces && selectedWp._selectedFaces.length > 0) {
        const face = selectedWp._selectedFaces[0];
        const props = _computeFaceProps(face);
        result._namedFaces[customName] = {
            normal: [...props.normal],
            centroid: [...props.centroid],
            area: props.area
        };
    }

    return result;
};

/**
 * Add a custom name for edge(s) matching a selector
 * @param {string} selector - Edge selector
 * @param {string} customName - New name to assign
 * @returns {Workplane}
 */
Workplane.prototype.nameEdge = function(selector, customName) {
    const result = new Workplane(this._plane);
    result._shape = this._shape;
    result._cloneProperties(this);
    _ensureNamedEdges(result);
    if (!result._namedEdges) result._namedEdges = {};

    const selectedWp = this.edges(selector);
    if (selectedWp._selectedEdges && selectedWp._selectedEdges.length > 0) {
        const edge = selectedWp._selectedEdges[0];
        const oc = getOC();
        const curve = new oc.BRepAdaptor_Curve_2(edge);
        const first = curve.FirstParameter();
        const last = curve.LastParameter();
        const p1 = curve.Value(first);
        const p2 = curve.Value(last);
        const mid = curve.Value((first + last) / 2);
        const dx = p2.X() - p1.X(), dy = p2.Y() - p1.Y(), dz = p2.Z() - p1.Z();
        const len = Math.sqrt(dx * dx + dy * dy + dz * dz);

        result._namedEdges[customName] = {
            midpoint: [mid.X(), mid.Y(), mid.Z()],
            direction: len > 1e-6 ? [dx / len, dy / len, dz / len] : [0, 0, 0],
            length: len
        };

        curve.delete();
        p1.delete();
        p2.delete();
        mid.delete();
    }

    return result;
};

/**
 * Get the FaceRef for a named face (for inspection)
 * @param {string} name - Face name
 * @returns {object|null} FaceRef { normal, centroid, area }
 */
Workplane.prototype.face = function(name) {
    _ensureNamedFaces(this);
    if (this._namedFaces && this._namedFaces[name]) {
        return { ...this._namedFaces[name] };
    }
    if (this._subParts) {
        for (const part of Object.values(this._subParts)) {
            if (part.namedFaces[name]) {
                return { ...part.namedFaces[name] };
            }
        }
    }
    return null;
};


// ============================================================
// RELATIVE OPERATIONS
// ============================================================

/**
 * Get bounding box of the current shape
 * @private
 */
function _getShapeBBox(shape) {
    const oc = getOC();
    const bndBox = new oc.Bnd_Box_1();
    oc.BRepBndLib.Add(shape, bndBox, false);
    const xMin = { current: 0 }, yMin = { current: 0 }, zMin = { current: 0 };
    const xMax = { current: 0 }, yMax = { current: 0 }, zMax = { current: 0 };
    bndBox.Get(xMin, yMin, zMin, xMax, yMax, zMax);
    bndBox.delete();
    return {
        minX: xMin.current, minY: yMin.current, minZ: zMin.current,
        maxX: xMax.current, maxY: yMax.current, maxZ: zMax.current,
    };
}

/**
 * Extrude a box or shape outward from a named face, auto-union
 *
 * extrudeOn("front", width, height, depth) — extrude a box
 * extrudeOn("front", otherShape) — position other on face + union
 *
 * @param {string} faceName - Named face to extrude from
 * @param {number|Workplane} widthOrShape - Box width or other Workplane
 * @param {number} [height] - Box height (if creating box)
 * @param {number} [depth] - Extrusion depth outward from face
 * @returns {Workplane}
 */
Workplane.prototype.extrudeOn = function(faceName, widthOrShape, height, depth) {
    _ensureNamedFaces(this);
    const faceRef = this._namedFaces && this._namedFaces[faceName];
    if (!faceRef) {
        console.error(`[naming] extrudeOn: face "${faceName}" not found`);
        return this;
    }

    const oc = getOC();
    const normal = faceRef.normal;
    const centroid = faceRef.centroid;

    if (typeof widthOrShape === 'object' && widthOrShape._shape) {
        // Position otherShape on face and union
        const other = widthOrShape;
        const otherBBox = _getShapeBBox(other._shape);
        const otherCenterX = (otherBBox.minX + otherBBox.maxX) / 2;
        const otherCenterY = (otherBBox.minY + otherBBox.maxY) / 2;
        const otherCenterZ = (otherBBox.minZ + otherBBox.maxZ) / 2;

        // Move other so its center is at the face centroid
        const tx = centroid[0] - otherCenterX;
        const ty = centroid[1] - otherCenterY;
        const tz = centroid[2] - otherCenterZ;

        const positioned = other.translate(tx, ty, tz);
        return this.union(positioned);
    }

    // Create a box and position it on the face
    const w = widthOrShape;
    const h = height;
    const d = depth;

    // Create box centered at origin
    const extrudeBox = new Workplane('XY').box(w, h, d, true);

    // Determine rotation to align box's +Z with face normal
    // The box's top (+Z) should face outward in the normal direction
    // We need to rotate the box so its +Z aligns with the face normal

    const boxBBox = _getShapeBBox(extrudeBox._shape);

    // Position: face centroid + offset along normal by half depth
    const cx = centroid[0] + normal[0] * d / 2;
    const cy = centroid[1] + normal[1] * d / 2;
    const cz = centroid[2] + normal[2] * d / 2;

    // Compute rotation from +Z to face normal
    let positioned = extrudeBox;
    const z = [0, 0, 1];
    const dot = _dotProduct(z, normal);

    if (Math.abs(dot + 1) < 1e-6) {
        // Normal is -Z: rotate 180 around X
        positioned = positioned.rotate(1, 0, 0, 180);
    } else if (Math.abs(dot - 1) > 1e-6) {
        // General rotation: axis = z × normal, angle = acos(dot)
        const crossX = z[1] * normal[2] - z[2] * normal[1];
        const crossY = z[2] * normal[0] - z[0] * normal[2];
        const crossZ = z[0] * normal[1] - z[1] * normal[0];
        const crossLen = Math.sqrt(crossX * crossX + crossY * crossY + crossZ * crossZ);
        if (crossLen > 1e-10) {
            const angle = Math.acos(Math.max(-1, Math.min(1, dot))) * 180 / Math.PI;
            positioned = positioned.rotate(crossX / crossLen, crossY / crossLen, crossZ / crossLen, angle);
        }
    }

    // Translate to position (accounting for box sitting on Z=0)
    const posBBox = _getShapeBBox(positioned._shape);
    const posCenterX = (posBBox.minX + posBBox.maxX) / 2;
    const posCenterY = (posBBox.minY + posBBox.maxY) / 2;
    const posCenterZ = (posBBox.minZ + posBBox.maxZ) / 2;

    positioned = positioned.translate(
        cx - posCenterX,
        cy - posCenterY,
        cz - posCenterZ
    );

    return this.union(positioned);
};

/**
 * Cut a box or shape inward from a named face
 *
 * cutInto("top", width, height, depth) — cut a pocket
 * cutInto("top", otherShape) — position other against face + cut
 */
Workplane.prototype.cutInto = function(faceName, widthOrShape, height, depth) {
    _ensureNamedFaces(this);
    const faceRef = this._namedFaces && this._namedFaces[faceName];
    if (!faceRef) {
        console.error(`[naming] cutInto: face "${faceName}" not found`);
        return this;
    }

    const normal = faceRef.normal;
    const centroid = faceRef.centroid;

    if (typeof widthOrShape === 'object' && widthOrShape._shape) {
        const other = widthOrShape;
        const otherBBox = _getShapeBBox(other._shape);
        const otherCenterX = (otherBBox.minX + otherBBox.maxX) / 2;
        const otherCenterY = (otherBBox.minY + otherBBox.maxY) / 2;
        const otherCenterZ = (otherBBox.minZ + otherBBox.maxZ) / 2;

        const tx = centroid[0] - otherCenterX;
        const ty = centroid[1] - otherCenterY;
        const tz = centroid[2] - otherCenterZ;

        const positioned = other.translate(tx, ty, tz);
        return this.cut(positioned);
    }

    const w = widthOrShape;
    const h = height;
    const d = depth;

    // Create box for cutting — positioned inward from face
    const cutBox = new Workplane('XY').box(w, h, d, true);

    // Position: face centroid - offset along normal by half depth (inward)
    const cx = centroid[0] - normal[0] * d / 2;
    const cy = centroid[1] - normal[1] * d / 2;
    const cz = centroid[2] - normal[2] * d / 2;

    // Rotate to align with face normal
    let positioned = cutBox;
    const z = [0, 0, 1];
    const dot = _dotProduct(z, normal);

    if (Math.abs(dot + 1) < 1e-6) {
        positioned = positioned.rotate(1, 0, 0, 180);
    } else if (Math.abs(dot - 1) > 1e-6) {
        const crossX = z[1] * normal[2] - z[2] * normal[1];
        const crossY = z[2] * normal[0] - z[0] * normal[2];
        const crossZ = z[0] * normal[1] - z[1] * normal[0];
        const crossLen = Math.sqrt(crossX * crossX + crossY * crossY + crossZ * crossZ);
        if (crossLen > 1e-10) {
            const angle = Math.acos(Math.max(-1, Math.min(1, dot))) * 180 / Math.PI;
            positioned = positioned.rotate(crossX / crossLen, crossY / crossLen, crossZ / crossLen, angle);
        }
    }

    const posBBox = _getShapeBBox(positioned._shape);
    const posCenterX = (posBBox.minX + posBBox.maxX) / 2;
    const posCenterY = (posBBox.minY + posBBox.maxY) / 2;
    const posCenterZ = (posBBox.minZ + posBBox.maxZ) / 2;

    positioned = positioned.translate(
        cx - posCenterX,
        cy - posCenterY,
        cz - posCenterZ
    );

    return this.cut(positioned);
};

/**
 * Center this shape on another shape's named face
 * Places this shape's center at other's face centroid
 */
Workplane.prototype.centerOn = function(other, faceName) {
    _ensureNamedFaces(other);
    const faceRef = other._namedFaces && other._namedFaces[faceName];
    if (!faceRef) {
        console.error(`[naming] centerOn: face "${faceName}" not found on other shape`);
        return this;
    }

    const thisBBox = _getShapeBBox(this._shape);
    const cx = (thisBBox.minX + thisBBox.maxX) / 2;
    const cy = (thisBBox.minY + thisBBox.maxY) / 2;
    const cz = (thisBBox.minZ + thisBBox.maxZ) / 2;

    return this.translate(
        faceRef.centroid[0] - cx,
        faceRef.centroid[1] - cy,
        faceRef.centroid[2] - cz
    );
};

/**
 * Align this shape so its opposing face is coplanar with other's named face
 * E.g., alignTo(other, "front") moves this shape so its back aligns with other's front
 */
Workplane.prototype.alignTo = function(other, faceName) {
    _ensureNamedFaces(other);
    const faceRef = other._namedFaces && other._namedFaces[faceName];
    if (!faceRef) {
        console.error(`[naming] alignTo: face "${faceName}" not found on other shape`);
        return this;
    }

    // Project this shape's center onto the face plane
    const thisBBox = _getShapeBBox(this._shape);
    const cx = (thisBBox.minX + thisBBox.maxX) / 2;
    const cy = (thisBBox.minY + thisBBox.maxY) / 2;
    const cz = (thisBBox.minZ + thisBBox.maxZ) / 2;

    // Move to face centroid (XY centering)
    let result = this.translate(
        faceRef.centroid[0] - cx,
        faceRef.centroid[1] - cy,
        faceRef.centroid[2] - cz
    );

    // Offset along normal so the back face of this shape touches the target face
    const resultBBox = _getShapeBBox(result._shape);
    const normal = faceRef.normal;

    // Calculate how far to push along normal so the near side of this shape
    // sits at the face centroid plane
    const halfExtent = _getHalfExtentAlongNormal(resultBBox, normal);
    result = result.translate(
        normal[0] * halfExtent,
        normal[1] * halfExtent,
        normal[2] * halfExtent
    );

    return result;
};

/**
 * Place this shape on other's face and union
 * = centerOn + union
 */
Workplane.prototype.attachTo = function(other, faceName) {
    const centered = this.centerOn(other, faceName);
    return other.union(centered);
};


/**
 * Get the half-extent of a bounding box along a normal direction
 * @private
 */
function _getHalfExtentAlongNormal(bbox, normal) {
    const sx = (bbox.maxX - bbox.minX) / 2;
    const sy = (bbox.maxY - bbox.minY) / 2;
    const sz = (bbox.maxZ - bbox.minZ) / 2;
    return Math.abs(normal[0]) * sx + Math.abs(normal[1]) * sy + Math.abs(normal[2]) * sz;
}
