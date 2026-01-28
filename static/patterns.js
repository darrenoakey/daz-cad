/**
 * patterns.js - Unified pattern cutting API for daz-cad-2
 *
 * Provides a single cutPattern() method that can generate thousands of pattern variations:
 * - Shape types: line, rect, square, circle, hexagon, octagon, triangle, or any n-sided polygon
 * - Layout options: spacing, borders, columns/rows grouping, staggering, rotation
 * - Modifiers: fillet, roundEnds, shear, individual rotation
 *
 * Example usage:
 *   box.faces(">Z").cutPattern({
 *       shape: 'line',
 *       width: 1.0,
 *       spacing: 2.0,
 *       depth: 0.4,
 *       border: 3.0
 *   });
 */

// Absolute path for import map cache busting
import { Workplane, getOC } from '/static/cad.js';


// ============================================================
// SHAPE GENERATOR FUNCTIONS
// ============================================================

/**
 * Create a line cutter (rectangular groove, optionally with rounded ends)
 * @private
 */
function _createLineCutter(oc, width, length, depth, roundEnds = false) {
    if (roundEnds && width > 0) {
        // Stadium/pill shape: rectangle with semicircle ends
        // Create by unioning a box with two cylinders
        const halfWidth = width / 2;
        const boxLength = length - width; // Shorter box, cylinders extend it

        if (boxLength <= 0) {
            // Just a cylinder if length <= width
            const cyl = new oc.BRepPrimAPI_MakeCylinder_1(halfWidth, depth);
            return cyl.Shape();
        }

        // Central box
        const box = new oc.BRepPrimAPI_MakeBox_3(
            new oc.gp_Pnt_3(-boxLength / 2, -halfWidth, 0),
            boxLength, width, depth
        );

        // Left end cylinder
        const leftCyl = new oc.BRepPrimAPI_MakeCylinder_1(halfWidth, depth);
        const leftTrsf = new oc.gp_Trsf_1();
        leftTrsf.SetTranslation_1(new oc.gp_Vec_4(-boxLength / 2, 0, 0));
        const leftMoved = leftCyl.Shape().Moved(new oc.TopLoc_Location_2(leftTrsf), false);

        // Right end cylinder
        const rightCyl = new oc.BRepPrimAPI_MakeCylinder_1(halfWidth, depth);
        const rightTrsf = new oc.gp_Trsf_1();
        rightTrsf.SetTranslation_1(new oc.gp_Vec_4(boxLength / 2, 0, 0));
        const rightMoved = rightCyl.Shape().Moved(new oc.TopLoc_Location_2(rightTrsf), false);

        // Union all three
        const fuse1 = new oc.BRepAlgoAPI_Fuse_3(box.Shape(), leftMoved, new oc.Message_ProgressRange_1());
        const fuse2 = new oc.BRepAlgoAPI_Fuse_3(fuse1.Shape(), rightMoved, new oc.Message_ProgressRange_1());

        return fuse2.Shape();
    } else {
        // Simple rectangular box
        const box = new oc.BRepPrimAPI_MakeBox_3(
            new oc.gp_Pnt_3(-length / 2, -width / 2, 0),
            length, width, depth
        );
        return box.Shape();
    }
}

/**
 * Create a rectangular cutter with optional corner radius and shear
 * @private
 */
function _createRectCutter(oc, width, height, depth, cornerRadius = 0, shear = 0) {
    const hw = width / 2;
    const hh = height / 2;

    // Clamp corner radius to half the smaller dimension
    const maxRadius = Math.min(hw, hh) - 0.01;
    const r = Math.min(Math.max(0, cornerRadius), maxRadius);

    let wire;

    if (r > 0.01 && shear === 0) {
        // Create rounded rectangle using boolean union of:
        // - Center cross (two overlapping rectangles)
        // - 4 corner cylinders

        // Horizontal rectangle (full width, reduced height)
        const hRect = new oc.BRepPrimAPI_MakeBox_3(
            new oc.gp_Pnt_3(-hw, -hh + r, 0),
            width, height - 2 * r, depth
        );

        // Vertical rectangle (reduced width, full height)
        const vRect = new oc.BRepPrimAPI_MakeBox_3(
            new oc.gp_Pnt_3(-hw + r, -hh, 0),
            width - 2 * r, height, depth
        );

        // Union the two rectangles
        let shape = new oc.BRepAlgoAPI_Fuse_3(
            hRect.Shape(), vRect.Shape(), new oc.Message_ProgressRange_1()
        ).Shape();

        // Add corner cylinders
        const corners = [
            [-hw + r, -hh + r],  // bottom-left
            [hw - r, -hh + r],   // bottom-right
            [hw - r, hh - r],    // top-right
            [-hw + r, hh - r]    // top-left
        ];

        for (const [cx, cy] of corners) {
            const cyl = new oc.BRepPrimAPI_MakeCylinder_1(r, depth);
            const trsf = new oc.gp_Trsf_1();
            trsf.SetTranslation_1(new oc.gp_Vec_4(cx, cy, 0));
            const movedCyl = cyl.Shape().Moved(new oc.TopLoc_Location_2(trsf), false);
            shape = new oc.BRepAlgoAPI_Fuse_3(shape, movedCyl, new oc.Message_ProgressRange_1()).Shape();
        }

        return shape;
    } else if (shear !== 0) {
        // Create parallelogram
        const shearRad = (shear * Math.PI) / 180;
        const shearOffset = height * Math.tan(shearRad);

        const p1 = new oc.gp_Pnt_3(-hw, -hh, 0);
        const p2 = new oc.gp_Pnt_3(hw, -hh, 0);
        const p3 = new oc.gp_Pnt_3(hw + shearOffset, hh, 0);
        const p4 = new oc.gp_Pnt_3(-hw + shearOffset, hh, 0);

        const wireBuilder = new oc.BRepBuilderAPI_MakeWire_1();
        wireBuilder.Add_1(new oc.BRepBuilderAPI_MakeEdge_3(p1, p2).Edge());
        wireBuilder.Add_1(new oc.BRepBuilderAPI_MakeEdge_3(p2, p3).Edge());
        wireBuilder.Add_1(new oc.BRepBuilderAPI_MakeEdge_3(p3, p4).Edge());
        wireBuilder.Add_1(new oc.BRepBuilderAPI_MakeEdge_3(p4, p1).Edge());
        wire = wireBuilder.Wire();
    } else {
        // Simple rectangle - use box for efficiency
        const box = new oc.BRepPrimAPI_MakeBox_3(
            new oc.gp_Pnt_3(-hw, -hh, 0),
            width, height, depth
        );
        return box.Shape();
    }

    // Extrude the wire into a solid
    const face = new oc.BRepBuilderAPI_MakeFace_15(wire, true);
    const prism = new oc.BRepPrimAPI_MakePrism_1(
        face.Face(),
        new oc.gp_Vec_4(0, 0, depth),
        false, true
    );
    return prism.Shape();
}

/**
 * Create a circular cutter
 * @private
 */
function _createCircleCutter(oc, diameter, depth) {
    const radius = diameter / 2;
    const cyl = new oc.BRepPrimAPI_MakeCylinder_1(radius, depth);
    return cyl.Shape();
}

/**
 * Create a regular polygon cutter (n-sided)
 * @private
 */
function _createPolygonCutter(oc, sides, flatToFlat, depth) {
    // Calculate circumradius from flat-to-flat distance
    const inradius = flatToFlat / 2;
    const circumradius = inradius / Math.cos(Math.PI / sides);

    // Build polygon wire
    const wireBuilder = new oc.BRepBuilderAPI_MakeWire_1();
    const points = [];

    for (let i = 0; i < sides; i++) {
        // Start with flat side horizontal (rotated by half step)
        const angle = (2 * Math.PI * i / sides) + (Math.PI / sides) + (Math.PI / 2);
        const x = circumradius * Math.cos(angle);
        const y = circumradius * Math.sin(angle);
        points.push(new oc.gp_Pnt_3(x, y, 0));
    }

    for (let i = 0; i < sides; i++) {
        const p1 = points[i];
        const p2 = points[(i + 1) % sides];
        const edge = new oc.BRepBuilderAPI_MakeEdge_3(p1, p2).Edge();
        wireBuilder.Add_1(edge);
    }

    // Validate wire construction
    if (!wireBuilder.IsDone()) {
        console.error(`[_createPolygonCutter] Wire construction failed for ${sides}-sided polygon, flatToFlat=${flatToFlat}`);
        return null;
    }

    const wire = wireBuilder.Wire();
    const faceMaker = new oc.BRepBuilderAPI_MakeFace_15(wire, true);

    // Validate face construction
    if (!faceMaker.IsDone()) {
        console.error(`[_createPolygonCutter] Face construction failed for ${sides}-sided polygon, flatToFlat=${flatToFlat}`);
        return null;
    }

    const prism = new oc.BRepPrimAPI_MakePrism_1(
        faceMaker.Face(),
        new oc.gp_Vec_4(0, 0, depth),
        false, true
    );

    // Validate prism construction
    if (!prism.IsDone()) {
        console.error(`[_createPolygonCutter] Prism construction failed for ${sides}-sided polygon, flatToFlat=${flatToFlat}, depth=${depth}`);
        return null;
    }

    return prism.Shape();
}


// ============================================================
// LAYOUT GENERATOR
// ============================================================

/**
 * Calculate grid positions for pattern layout
 * @private
 * @returns {Array<{x: number, y: number}>} Array of center positions
 */
function _calculateGridPositions(options, faceWidth, faceHeight) {
    const {
        spacing: rawSpacing = null,
        spacingX = null,
        spacingY = null,
        border = 2.0,
        borderX = null,
        borderY = null,
        columns = 1,
        columnGap = 5.0,
        rows = null,
        rowGap = null,
        stagger = false,
        staggerAmount = 0.5,
        angle = 0,
        direction = 'x',
        shape = 'rect',
        width = 1.0,
        height = null,
        wallThickness = null
    } = options;

    // Default spacing to width (50% solid, 50% gap)
    const spacing = rawSpacing ?? width;
    const actualSpacingX = spacingX ?? spacing;
    const actualSpacingY = spacingY ?? spacing;
    const actualBorderX = borderX ?? border;
    const actualBorderY = borderY ?? border;
    const actualRowGap = rowGap ?? columnGap;
    const actualRows = rows ?? 1;

    // Calculate effective spacing (center-to-center distance)
    // spacing parameter is the GAP between shapes, so add shape dimensions
    const effectiveWidth = width;
    const effectiveHeight = height ?? width;

    let effectiveSpacingX, effectiveSpacingY;

    if (wallThickness !== null) {
        // wallThickness overrides spacing - it's the wall between shapes
        effectiveSpacingX = effectiveWidth + wallThickness;
        effectiveSpacingY = effectiveHeight + wallThickness;
    } else {
        // spacing is the gap between shapes, add shape size for center-to-center
        effectiveSpacingX = effectiveWidth + actualSpacingX;
        effectiveSpacingY = effectiveHeight + actualSpacingY;
    }

    // Calculate usable area per column/row group
    const totalColumnGaps = columns > 1 ? (columns - 1) * columnGap : 0;
    const totalRowGaps = actualRows > 1 ? (actualRows - 1) * actualRowGap : 0;

    const usableWidth = faceWidth - 2 * actualBorderX - totalColumnGaps;
    const usableHeight = faceHeight - 2 * actualBorderY - totalRowGaps;

    const columnWidth = usableWidth / columns;
    const rowHeight = usableHeight / actualRows;

    const positions = [];

    // For each column group
    for (let col = 0; col < columns; col++) {
        // For each row group
        for (let rowGroup = 0; rowGroup < actualRows; rowGroup++) {
            // Calculate the region for this group
            const regionStartX = actualBorderX + col * (columnWidth + columnGap) - faceWidth / 2;
            const regionEndX = regionStartX + columnWidth;
            const regionStartY = actualBorderY + rowGroup * (rowHeight + actualRowGap) - faceHeight / 2;
            const regionEndY = regionStartY + rowHeight;

            const regionWidth = regionEndX - regionStartX;
            const regionHeight = regionEndY - regionStartY;

            // Calculate number of items that fit in this region
            const nCols = Math.max(1, Math.floor(regionWidth / effectiveSpacingX));
            const nRows = Math.max(1, Math.floor(regionHeight / effectiveSpacingY));

            // Center the grid within the region
            const gridWidth = (nCols - 1) * effectiveSpacingX;
            const gridHeight = (nRows - 1) * effectiveSpacingY;
            const gridStartX = regionStartX + (regionWidth - gridWidth) / 2;
            const gridStartY = regionStartY + (regionHeight - gridHeight) / 2;

            // Generate positions within this region
            for (let r = 0; r < nRows; r++) {
                for (let c = 0; c < nCols; c++) {
                    let x = gridStartX + c * effectiveSpacingX;
                    let y = gridStartY + r * effectiveSpacingY;

                    // Apply stagger offset for odd rows
                    if (stagger && r % 2 === 1) {
                        x += effectiveSpacingX * staggerAmount;
                    }

                    // Apply pattern rotation if specified
                    if (angle !== 0) {
                        const angleRad = (angle * Math.PI) / 180;
                        const cos = Math.cos(angleRad);
                        const sin = Math.sin(angleRad);
                        const newX = x * cos - y * sin;
                        const newY = x * sin + y * cos;
                        x = newX;
                        y = newY;
                    }

                    positions.push({ x, y });
                }
            }
        }
    }

    return positions;
}


// ============================================================
// FACE BOUNDARY AND CLIPPING HELPERS
// ============================================================

/**
 * Create an inset face by offsetting the boundary inward
 * @private
 * For circles: creates a smaller circle
 * For polygons: offsets each vertex along bisector of adjacent edges
 */
function _createOffsetFace(oc, face, border, faceInfo) {
    try {
        const outerWire = oc.BRepTools.OuterWire(face);
        if (!outerWire || outerWire.IsNull()) {
            return null;
        }

        // Collect vertices IN ORDER around the wire using BRepTools_WireExplorer
        // This ensures we get vertices in the correct sequence for polygon offset
        const vertices = [];
        const wireExplorer = new oc.BRepTools_WireExplorer_1();
        wireExplorer.Init_1(outerWire);

        while (wireExplorer.More()) {
            const vertex = wireExplorer.CurrentVertex();
            const pnt = oc.BRep_Tool.Pnt(vertex);
            vertices.push({ x: pnt.X(), y: pnt.Y(), z: pnt.Z() });
            pnt.delete();
            wireExplorer.Next();
        }
        wireExplorer.delete();

        // Check if it's a circular face (single curved edge)
        const edges = [];
        const edgeExp = new oc.TopExp_Explorer_2(
            outerWire,
            oc.TopAbs_ShapeEnum.TopAbs_EDGE,
            oc.TopAbs_ShapeEnum.TopAbs_SHAPE
        );
        while (edgeExp.More()) {
            edges.push(oc.TopoDS.Edge_1(edgeExp.Current()));
            edgeExp.Next();
        }
        edgeExp.delete();

        // If single edge and few vertices, might be a circle
        if (edges.length === 1 && vertices.length <= 2) {
            // Check if it's a circle
            const curve = new oc.BRepAdaptor_Curve_2(edges[0]);
            const curveType = curve.GetType();
            if (curveType === oc.GeomAbs_CurveType.GeomAbs_Circle) {
                const circle = curve.Circle();
                const radius = circle.Radius();
                const center = circle.Location();
                const axis = circle.Axis();

                if (radius > border) {
                    // Create smaller circle
                    const newCircle = new oc.Geom_Circle_2(
                        new oc.gp_Ax2_3(center, axis.Direction()),
                        radius - border
                    );
                    const newEdge = new oc.BRepBuilderAPI_MakeEdge_24(
                        new oc.Handle_Geom_Curve_2(newCircle)
                    ).Edge();
                    const newWire = new oc.BRepBuilderAPI_MakeWire_2(newEdge).Wire();
                    const newFace = new oc.BRepBuilderAPI_MakeFace_15(newWire, true);
                    if (newFace.IsDone()) {
                        console.log(`[_createOffsetFace] Created offset circle, radius ${radius.toFixed(1)} -> ${(radius-border).toFixed(1)}`);
                        curve.delete();
                        return newFace.Face();
                    }
                }
            }
            curve.delete();
        }

        // For polygonal faces, use proper edge-based offset algorithm
        // The correct approach: offset each EDGE inward, then find intersections
        if (vertices.length >= 3) {
            // First, determine if polygon is CCW or CW (for correct inward direction)
            // Use signed area - positive = CCW, negative = CW
            let signedArea = 0;
            for (let i = 0; i < vertices.length; i++) {
                const v1 = vertices[i];
                const v2 = vertices[(i + 1) % vertices.length];
                signedArea += (v2.x - v1.x) * (v2.y + v1.y);
            }
            // If CW (signedArea > 0), inward normal is (dy, -dx)
            // If CCW (signedArea < 0), inward normal is (-dy, dx)
            const cwFactor = signedArea > 0 ? 1 : -1;

            // Calculate inward normal for each edge
            const edgeNormals = [];
            for (let i = 0; i < vertices.length; i++) {
                const v1 = vertices[i];
                const v2 = vertices[(i + 1) % vertices.length];
                const dx = v2.x - v1.x;
                const dy = v2.y - v1.y;
                const len = Math.sqrt(dx*dx + dy*dy);
                if (len > 0.0001) {
                    // Inward normal (perpendicular to edge)
                    edgeNormals.push({
                        x: cwFactor * dy / len,
                        y: cwFactor * -dx / len
                    });
                } else {
                    edgeNormals.push({ x: 0, y: 0 });
                }
            }

            // For each vertex, find intersection of the two adjacent offset edges
            const offsetVertices = [];
            for (let i = 0; i < vertices.length; i++) {
                const prevIdx = (i - 1 + vertices.length) % vertices.length;

                // Previous edge (from prevIdx to i), offset by its normal
                const v0 = vertices[prevIdx];
                const v1 = vertices[i];
                const n0 = edgeNormals[prevIdx];

                // Current edge (from i to next), offset by its normal
                const nextIdx = (i + 1) % vertices.length;
                const v2 = vertices[nextIdx];
                const n1 = edgeNormals[i];

                // Offset points on each edge
                const p1 = { x: v0.x + n0.x * border, y: v0.y + n0.y * border };
                const p2 = { x: v1.x + n0.x * border, y: v1.y + n0.y * border };
                const p3 = { x: v1.x + n1.x * border, y: v1.y + n1.y * border };
                const p4 = { x: v2.x + n1.x * border, y: v2.y + n1.y * border };

                // Edge directions
                const d1x = p2.x - p1.x;
                const d1y = p2.y - p1.y;
                const d2x = p4.x - p3.x;
                const d2y = p4.y - p3.y;

                // Find intersection of two lines:
                // Line 1: p1 + t * d1
                // Line 2: p3 + s * d2
                // Solve: p1 + t * d1 = p3 + s * d2
                const cross = d1x * d2y - d1y * d2x;

                if (Math.abs(cross) > 0.0001) {
                    // Lines are not parallel - find intersection
                    const t = ((p3.x - p1.x) * d2y - (p3.y - p1.y) * d2x) / cross;
                    offsetVertices.push({
                        x: p1.x + t * d1x,
                        y: p1.y + t * d1y,
                        z: v1.z  // Keep Z from original vertex
                    });
                } else {
                    // Parallel edges - use midpoint of offset points
                    offsetVertices.push({
                        x: (p2.x + p3.x) / 2,
                        y: (p2.y + p3.y) / 2,
                        z: v1.z
                    });
                }
            }

            // Validate: check that offset polygon doesn't self-intersect
            // (can happen with large offsets on concave polygons)
            // Simple check: all offset vertices should be "inside" original polygon direction
            let validOffset = true;
            for (let i = 0; i < offsetVertices.length; i++) {
                const prevIdx = (i - 1 + offsetVertices.length) % offsetVertices.length;
                const v1 = offsetVertices[prevIdx];
                const v2 = offsetVertices[i];
                const dx = v2.x - v1.x;
                const dy = v2.y - v1.y;
                if (Math.sqrt(dx*dx + dy*dy) < 0.001) {
                    validOffset = false;
                    break;
                }
            }

            if (!validOffset) {
                console.warn('[_createOffsetFace] Offset produces degenerate polygon, falling back');
                return null;
            }

            // Build wire from offset vertices
            if (offsetVertices.length >= 3) {
                const wireBuilder = new oc.BRepBuilderAPI_MakeWire_1();
                for (let i = 0; i < offsetVertices.length; i++) {
                    const p1 = offsetVertices[i];
                    const p2 = offsetVertices[(i + 1) % offsetVertices.length];
                    const edge = new oc.BRepBuilderAPI_MakeEdge_3(
                        new oc.gp_Pnt_3(p1.x, p1.y, p1.z),
                        new oc.gp_Pnt_3(p2.x, p2.y, p2.z)
                    ).Edge();
                    wireBuilder.Add_1(edge);
                }

                if (wireBuilder.IsDone()) {
                    const newWire = wireBuilder.Wire();
                    const newFace = new oc.BRepBuilderAPI_MakeFace_15(newWire, true);
                    if (newFace.IsDone()) {
                        console.log(`[_createOffsetFace] Created offset polygon with ${offsetVertices.length} vertices`);
                        return newFace.Face();
                    }
                }
            }
        }

        console.warn('[_createOffsetFace] Could not create offset face');
        return null;

    } catch (e) {
        console.warn('[_createOffsetFace] Exception:', e.message);
        return null;
    }
}


/**
 * Get the outer wire of a face, offset it inward, and create a clipping solid
 * @private
 * @param {Object} oc - OpenCascade instance
 * @param {TopoDS_Face} face - The face to get boundary from
 * @param {number} border - Inward offset distance
 * @param {number} depth - Extrusion depth for clipping solid
 * @param {Object} faceInfo - Face coordinate system info
 * @returns {Object} { clipSolid, clipWire, success }
 */
function _createClipBoundary(oc, face, border, depth, faceInfo) {
    try {
        let clipFace = face;

        // If border > 0, create an inset face by offsetting the boundary
        if (border > 0.001) {
            clipFace = _createOffsetFace(oc, face, border, faceInfo) || face;
        }

        // Extrude the face in BOTH directions to fully contain the cutters
        // Cutters extend both above and below the face
        const { normal } = faceInfo;

        // First, extrude downward (into the solid)
        const downVec = new oc.gp_Vec_4(
            -normal.x * (depth + 5),
            -normal.y * (depth + 5),
            -normal.z * (depth + 5)
        );
        const downPrism = new oc.BRepPrimAPI_MakePrism_1(clipFace, downVec, false, true);

        if (!downPrism.IsDone()) {
            console.warn('[_createClipBoundary] Could not extrude clip face downward');
            return { success: false };
        }

        // Then extrude upward (above the face) and union
        const upVec = new oc.gp_Vec_4(
            normal.x * 5,
            normal.y * 5,
            normal.z * 5
        );
        const upPrism = new oc.BRepPrimAPI_MakePrism_1(clipFace, upVec, false, true);

        let clipSolid;
        if (upPrism.IsDone()) {
            // Union the two extrusions
            const fused = new oc.BRepAlgoAPI_Fuse_3(
                downPrism.Shape(),
                upPrism.Shape(),
                new oc.Message_ProgressRange_1()
            );
            if (fused.IsDone()) {
                clipSolid = fused.Shape();
            } else {
                clipSolid = downPrism.Shape();  // Fallback to just downward
            }
        } else {
            clipSolid = downPrism.Shape();
        }

        console.log('[_createClipBoundary] Created clip boundary solid');

        return {
            success: true,
            clipSolid
        };

    } catch (e) {
        console.error('[_createClipBoundary] Exception:', e.message);
        return { success: false };
    }
}

/**
 * Check if a shape is fully contained within another shape
 * @private
 */
function _isFullyContained(oc, shape, container) {
    try {
        // Compute common (intersection)
        const common = new oc.BRepAlgoAPI_Common_3(
            shape,
            container,
            new oc.Message_ProgressRange_1()
        );

        if (!common.IsDone()) {
            common.delete();
            return false;
        }

        const intersection = common.Shape();
        common.delete();

        if (!intersection || intersection.IsNull()) {
            return false;
        }

        // Compare volumes - if intersection volume equals original, it's fully contained
        const originalProps = new oc.GProp_GProps_1();
        oc.BRepGProp.VolumeProperties_1(shape, originalProps, true, false, false);
        const originalVol = originalProps.Mass();
        originalProps.delete();

        const intersectProps = new oc.GProp_GProps_1();
        oc.BRepGProp.VolumeProperties_1(intersection, intersectProps, true, false, false);
        const intersectVol = intersectProps.Mass();
        intersectProps.delete();

        // Allow 1% tolerance for numerical precision
        const ratio = intersectVol / originalVol;
        return ratio > 0.99;

    } catch (e) {
        console.warn('[_isFullyContained] Exception:', e.message);
        return false;
    }
}

/**
 * Clip a shape to a boundary (intersection)
 * @private
 */
function _clipToBoundary(oc, shape, boundary) {
    try {
        const common = new oc.BRepAlgoAPI_Common_3(
            shape,
            boundary,
            new oc.Message_ProgressRange_1()
        );

        if (!common.IsDone()) {
            common.delete();
            return null;
        }

        const result = common.Shape();
        common.delete();

        if (!result || result.IsNull()) {
            return null;
        }

        // Check if result has volume
        const props = new oc.GProp_GProps_1();
        oc.BRepGProp.VolumeProperties_1(result, props, true, false, false);
        const vol = props.Mass();
        props.delete();

        if (vol < 0.001) {
            return null;  // Too small, skip
        }

        return result;

    } catch (e) {
        console.warn('[_clipToBoundary] Exception:', e.message);
        return null;
    }
}


// ============================================================
// FACE ANALYSIS HELPERS
// ============================================================

/**
 * Get the normal vector and local coordinate system of a face
 * @private
 * @returns {Object} { normal: {x,y,z}, uAxis: {x,y,z}, vAxis: {x,y,z}, center: {x,y,z}, uSize, vSize }
 */
function _getFaceCoordinateSystem(oc, face, shape) {
    // Get face bounding box for dimensions and center
    const faceBbox = new oc.Bnd_Box_1();
    oc.BRepBndLib.Add(face, faceBbox, false);
    const fxMin = { current: 0 }, fyMin = { current: 0 }, fzMin = { current: 0 };
    const fxMax = { current: 0 }, fyMax = { current: 0 }, fzMax = { current: 0 };
    faceBbox.Get(fxMin, fyMin, fzMin, fxMax, fyMax, fzMax);

    const sizeX = fxMax.current - fxMin.current;
    const sizeY = fyMax.current - fyMin.current;
    const sizeZ = fzMax.current - fzMin.current;

    const centerX = (fxMin.current + fxMax.current) / 2;
    const centerY = (fyMin.current + fyMax.current) / 2;
    const centerZ = (fzMin.current + fzMax.current) / 2;

    // Get the face's actual outward normal using BRepAdaptor_Surface
    const adaptor = new oc.BRepAdaptor_Surface_2(face, true);

    // Get UV bounds of the face
    const uMin = adaptor.FirstUParameter();
    const uMax = adaptor.LastUParameter();
    const vMin = adaptor.FirstVParameter();
    const vMax = adaptor.LastVParameter();

    // Evaluate at center of the face in UV space
    const uMid = (uMin + uMax) / 2;
    const vMid = (vMin + vMax) / 2;

    // Get point and derivatives at center
    const pnt = new oc.gp_Pnt_1();
    const d1u = new oc.gp_Vec_1();
    const d1v = new oc.gp_Vec_1();
    adaptor.D1(uMid, vMid, pnt, d1u, d1v);

    // Compute normal from cross product of derivatives
    let normalVec = d1u.Crossed(d1v);

    // Check face orientation - if reversed, flip the normal
    const orientation = face.Orientation_1();
    if (orientation === oc.TopAbs_Orientation.TopAbs_REVERSED) {
        normalVec.Reverse();
    }

    // Normalize
    const mag = normalVec.Magnitude();
    const normal = {
        x: normalVec.X() / mag,
        y: normalVec.Y() / mag,
        z: normalVec.Z() / mag
    };

    // Determine face dimensions based on which axis the normal is closest to
    const absNormal = { x: Math.abs(normal.x), y: Math.abs(normal.y), z: Math.abs(normal.z) };
    let uSize, vSize;

    if (absNormal.z > absNormal.x && absNormal.z > absNormal.y) {
        // Face perpendicular to Z
        uSize = sizeX;
        vSize = sizeY;
    } else if (absNormal.x > absNormal.y) {
        // Face perpendicular to X
        uSize = sizeY;
        vSize = sizeZ;
    } else {
        // Face perpendicular to Y
        uSize = sizeX;
        vSize = sizeZ;
    }

    const center = { x: centerX, y: centerY, z: centerZ };

    return { normal, center, uSize, vSize, absNormal };
}

/**
 * Create a transformation matrix to position a cutter on a face
 * @private
 * Cutters are created in XY plane at Z=0, extending upward in +Z.
 * This transforms them to cut into the selected face from outside.
 */
function _createFaceTransform(oc, faceInfo, localX, localY, cutDepth) {
    const { normal, center, absNormal } = faceInfo;

    // World position where the cutter center should end up
    let worldX, worldY, worldZ;

    // Rotation to orient the cutter perpendicular to the face
    let rotationAxis = null;
    let rotationAngle = 0;

    if (absNormal.z > absNormal.x && absNormal.z > absNormal.y) {
        // Face perpendicular to Z (horizontal face)
        // localX -> world X, localY -> world Y
        worldX = center.x + localX;
        worldY = center.y + localY;

        if (normal.z > 0) {
            // Top face (+Z normal) - cutter at surface-depth, extends up through surface
            worldZ = center.z - cutDepth;
            // No rotation needed, cutter already extends in +Z
        } else {
            // Bottom face (-Z normal) - cutter at surface+depth, extends down through surface
            worldZ = center.z + cutDepth;
            // Rotate 180° around X to flip the cutter
            rotationAxis = new oc.gp_Dir_4(1, 0, 0);
            rotationAngle = Math.PI;
        }
    } else if (absNormal.x > absNormal.y) {
        // Face perpendicular to X (front/back face)
        // localX -> world Y, localY -> world Z
        worldY = center.y + localX;
        worldZ = center.z + localY;

        if (normal.x > 0) {
            // Back face (+X normal) - cutter at surface-depth, extends in +X through surface
            worldX = center.x - cutDepth;
            // Rotate +90° around Y: +Z becomes +X
            rotationAxis = new oc.gp_Dir_4(0, 1, 0);
            rotationAngle = Math.PI / 2;
        } else {
            // Front face (-X normal) - cutter at surface+depth, extends in -X through surface
            worldX = center.x + cutDepth;
            // Rotate -90° around Y: +Z becomes -X
            rotationAxis = new oc.gp_Dir_4(0, 1, 0);
            rotationAngle = -Math.PI / 2;
        }
    } else {
        // Face perpendicular to Y (left/right face)
        // localX -> world X, localY -> world Z
        worldX = center.x + localX;
        worldZ = center.z + localY;

        if (normal.y > 0) {
            // Right face (+Y normal) - cutter at surface-depth, extends in +Y through surface
            worldY = center.y - cutDepth;
            // Rotate -90° around X: +Z becomes +Y
            rotationAxis = new oc.gp_Dir_4(1, 0, 0);
            rotationAngle = -Math.PI / 2;
        } else {
            // Left face (-Y normal) - cutter at surface+depth, extends in -Y through surface
            worldY = center.y + cutDepth;
            // Rotate +90° around X: +Z becomes -Y
            rotationAxis = new oc.gp_Dir_4(1, 0, 0);
            rotationAngle = Math.PI / 2;
        }
    }

    // Build transformation: first rotate (around origin), then translate
    const trsf = new oc.gp_Trsf_1();

    if (rotationAxis) {
        const ax1 = new oc.gp_Ax1_2(new oc.gp_Pnt_3(0, 0, 0), rotationAxis);
        trsf.SetRotation_1(ax1, rotationAngle);
    }

    // Create translation and compose: T * R (apply rotation first, then translation)
    const transTrsf = new oc.gp_Trsf_1();
    transTrsf.SetTranslation_1(new oc.gp_Vec_4(worldX, worldY, worldZ));

    // trsf.Multiply(other) computes trsf = trsf * other
    // We want final = T * R, so: start with R, multiply by T gives R * T
    // But that applies T first then R - wrong order!
    // We need to do: transTrsf.Multiply(trsf) to get T * R
    transTrsf.Multiply(trsf);

    return transTrsf;
}

// ============================================================
// MAIN cutPattern() METHOD
// ============================================================

/**
 * Cut a unified pattern into a selected face or the top of a shape
 *
 * This is a comprehensive pattern cutting method that supports:
 * - Multiple shape types: line, rect, square, circle, hexagon, octagon, triangle, or any n-sided polygon
 * - Full layout control: spacing, borders, column/row groups, staggering, pattern rotation
 * - Shape modifiers: fillet, round ends, shear, individual rotation
 * - Works on any face orientation (top, bottom, front, back, left, right)
 *
 * @param {Object} options - Configuration object
 * @param {string|number} [options.shape='line'] - Shape type or number of sides
 * @param {number} [options.width=1.0] - Primary dimension (line width, rect width, circle diameter, polygon flat-to-flat)
 * @param {number} [options.height=null] - Secondary dimension (rect height). Defaults to width
 * @param {number} [options.length=null] - For lines: line length (null = auto fill face width minus borders)
 * @param {number} [options.fillet=0] - Corner radius for rectangles/squares
 * @param {boolean} [options.roundEnds=false] - Round the ends of lines (stadium shape)
 * @param {number} [options.shear=0] - Shear angle in degrees (parallelograms)
 * @param {number} [options.rotation=0] - Rotate each individual shape by this angle
 * @param {number} [options.depth=null] - Cut depth in mm. null = through-cut
 * @param {number} [options.spacing=width] - Gap between shapes (defaults to width for 50% solid/50% cut)
 * @param {number} [options.spacingX=null] - Override X gap
 * @param {number} [options.spacingY=null] - Override Y gap
 * @param {number} [options.wallThickness=null] - Alternative name for spacing: wall between shapes
 * @param {number} [options.border=2.0] - Margin from face edges
 * @param {number} [options.borderX=null] - Override X border
 * @param {number} [options.borderY=null] - Override Y border
 * @param {number} [options.columns=1] - Split pattern into N column groups
 * @param {number} [options.columnGap=5.0] - Gap between column groups
 * @param {number} [options.rows=null] - Split into N row groups
 * @param {number} [options.rowGap=null] - Gap between row groups
 * @param {boolean} [options.stagger=false] - Offset alternate rows (brick/hex pattern)
 * @param {number} [options.staggerAmount=0.5] - Fraction of spacingX to offset
 * @param {number} [options.angle=0] - Rotate entire pattern (degrees)
 * @param {string} [options.direction='x'] - For lines: 'x' (horizontal) or 'y' (vertical)
 * @param {string} [options.clip='none'] - Clip mode for non-rectangular faces:
 *   - 'none': No clipping (default, backward compatible)
 *   - 'partial': Clip shapes to face boundary (partial shapes at edges)
 *   - 'whole': Only keep shapes fully inside boundary (no partial shapes)
 * @returns {Workplane} - New Workplane with pattern cut
 *
 * @example
 * // Horizontal grip lines on top face
 * box.faces(">Z").cutPattern({
 *     shape: 'line',
 *     width: 1.0,
 *     spacing: 2.0,
 *     depth: 0.4,
 *     border: 3.0
 * });
 *
 * @example
 * // Hex pattern on circular face with partial clipping
 * cylinder.faces(">Z").cutPattern({
 *     shape: 'hexagon',
 *     width: 5,
 *     wallThickness: 1,
 *     stagger: true,
 *     clip: 'partial',  // Clips hexagons at circle edge
 *     border: 2
 * });
 *
 * @example
 * // Hex pattern on circular face - whole shapes only
 * cylinder.faces(">Z").cutPattern({
 *     shape: 'hexagon',
 *     width: 5,
 *     wallThickness: 1,
 *     stagger: true,
 *     clip: 'whole',  // Only full hexagons, none cut off
 *     border: 2
 * });
 */
Workplane.prototype.cutPattern = function(options = {}) {
    // Backward compatibility: if 'sides' is provided (old API), use it as shape
    // Also support 'type' from old API
    let effectiveShape = options.shape;
    if (effectiveShape === undefined) {
        if (options.sides !== undefined) {
            // Old API: { sides: 6, ... }
            effectiveShape = options.sides;
        } else if (options.type !== undefined) {
            // Old API: { type: 'hexagon', ... }
            effectiveShape = options.type;
        } else {
            effectiveShape = 'line';  // Default to line if nothing specified
        }
    }

    // Also support old 'size' parameter as width
    const effectiveWidth = options.width ?? options.size ?? 1.0;

    const {
        height = null,
        length = null,
        fillet = 0,
        roundEnds = false,
        shear = 0,
        rotation = 0,
        depth = null,
        spacing: rawSpacing = null,  // default to width if not specified
        spacingX = null,
        spacingY = null,
        wallThickness = null,
        border = 2.0,
        borderX = null,
        borderY = null,
        columns = 1,
        columnGap = 5.0,
        rows = null,
        rowGap = null,
        stagger = false,
        staggerAmount = 0.5,
        angle: rawAngle = null,
        direction = null,  // deprecated: use angle instead
        clip = 'none'  // 'none', 'partial', 'whole'
    } = options;

    const shape = effectiveShape;
    const width = effectiveWidth;
    // Default spacing to width if not specified (50% solid, 50% gap)
    const spacing = rawSpacing ?? width;

    // Backward compatibility: convert direction to angle
    // 'x'/'horizontal' = 0°, 'y'/'vertical' = 90°
    let angle = rawAngle ?? 0;
    if (direction !== null && rawAngle === null) {
        const d = direction.toLowerCase();
        if (d === 'y' || d === 'vertical' || d === 'v') {
            angle = 90;
        }
        // 'x', 'horizontal', 'h' all default to 0
    }

    // Compute actual border values
    const actualBorderX = borderX ?? border;
    const actualBorderY = borderY ?? border;

    if (!this._shape) {
        console.error('[cutPattern] No shape to cut');
        return this;
    }

    const oc = getOC();
    if (!oc) {
        console.error('[cutPattern] OpenCascade not initialized');
        return this;
    }

    const result = new Workplane(this._plane);
    result._cloneProperties(this);

    try {
        // Determine face info including normal and local coordinate system
        let faceInfo;
        let face;

        if (this._selectedFaces && this._selectedFaces.length > 0) {
            // Use selected face
            face = this._selectedFaces[0];
            faceInfo = _getFaceCoordinateSystem(oc, face, this._shape);
            if (!faceInfo) {
                console.error('[cutPattern] Could not get face coordinate system');
                result._shape = this._shape;
                return result;
            }
        } else {
            // Fall back to top face of shape bounding box (legacy behavior)
            const shapeBbox = this._getBoundingBox();
            if (!shapeBbox) {
                console.error('[cutPattern] Could not get bounding box');
                result._shape = this._shape;
                return result;
            }
            // Create a synthetic face info for XY-aligned top face
            faceInfo = {
                normal: { x: 0, y: 0, z: 1 },
                absNormal: { x: 0, y: 0, z: 1 },
                center: { x: shapeBbox.centerX, y: shapeBbox.centerY, z: shapeBbox.maxZ },
                uSize: shapeBbox.sizeX,
                vSize: shapeBbox.sizeY
            };
        }

        // Use face dimensions from coordinate system analysis
        const faceWidth = faceInfo.uSize;
        const faceHeight = faceInfo.vSize;

        console.log(`[cutPattern] Face normal: (${faceInfo.normal.x.toFixed(2)}, ${faceInfo.normal.y.toFixed(2)}, ${faceInfo.normal.z.toFixed(2)}), size: ${faceWidth.toFixed(1)} x ${faceHeight.toFixed(1)}`);

        // Calculate cut depth
        const shapeBbox = this._getBoundingBox();
        const maxDepth = shapeBbox ? Math.max(shapeBbox.sizeX, shapeBbox.sizeY, shapeBbox.sizeZ) + 2 : 100;
        const actualDepth = depth ?? maxDepth;

        // Create clip boundary if clipping is enabled and we have a face
        let clipBoundary = null;
        if (clip !== 'none' && face) {
            clipBoundary = _createClipBoundary(oc, face, border, actualDepth, faceInfo);
            if (clipBoundary.success) {
                console.log(`[cutPattern] Created clip boundary for mode: ${clip}`);
            } else {
                console.warn('[cutPattern] Could not create clip boundary, falling back to no clipping');
            }
        }

        // Resolve shape type to number of sides
        let sides = null;
        const shapeType = typeof shape === 'string' ? shape.toLowerCase() : shape;

        const shapeMap = {
            'line': 'line',
            'rect': 'rect',
            'rectangle': 'rect',
            'square': 'square',
            'circle': 'circle',
            'hexagon': 6,
            'hex': 6,
            'octagon': 8,
            'oct': 8,
            'triangle': 3,
            'tri': 3
        };

        let resolvedShape = shapeType;
        if (typeof shapeType === 'string' && shapeMap[shapeType] !== undefined) {
            resolvedShape = shapeMap[shapeType];
        } else if (typeof shapeType === 'number') {
            sides = shapeType;
            resolvedShape = 'polygon';
        }

        // Calculate effective dimensions
        const effectiveWidth = width;
        const effectiveHeight = height ?? width;

        // Determine actual border values
        const actualBorderX = borderX ?? border;
        const actualBorderY = borderY ?? border;

        // Generate cutter shapes based on type
        const cutterShapes = [];

        if (resolvedShape === 'line') {
            // Lines are positioned perpendicular to their direction
            // angle=0: horizontal lines (run along U, positioned along V)
            // angle=90: vertical lines (run along U rotated 90°, positioned along V)
            // Any angle works for diagonal lines
            const lineWidth = width;

            // Line length: if not specified, calculate from face dimensions
            // For diagonal lines, use the diagonal of the face
            const angleRad = (angle * Math.PI) / 180;
            const cosA = Math.cos(angleRad);
            const sinA = Math.sin(angleRad);
            const effectiveFaceWidth = Math.abs(cosA) * faceWidth + Math.abs(sinA) * faceHeight;
            const lineLength = length ?? (effectiveFaceWidth - 2 * border);

            // Spacing is perpendicular to the lines
            // For horizontal lines (angle=0), spacing is along Y (faceHeight direction)
            // For vertical lines (angle=90), spacing is along X (faceWidth direction)
            // spacing parameter is the GAP between lines, so center-to-center = lineWidth + spacing
            const gapSpacing = spacingX ?? spacingY ?? spacing;
            const effectiveSpacing = lineWidth + gapSpacing;

            // Calculate number of lines based on the perpendicular dimension
            const perpDimension = Math.abs(sinA) * faceWidth + Math.abs(cosA) * faceHeight;
            const startPos = border;
            const endPos = perpDimension - border;
            const availableSpace = endPos - startPos;

            const numLines = Math.max(0, Math.floor(availableSpace / effectiveSpacing));
            const totalSpan = numLines * effectiveSpacing;
            const offsetPos = (availableSpace - totalSpan) / 2;

            for (let i = 0; i <= numLines; i++) {
                const pos = startPos + offsetPos + i * effectiveSpacing;

                // Create line cutter (in XY plane, will be transformed)
                const lineCutter = _createLineCutter(oc, lineWidth, lineLength, actualDepth + 1, roundEnds);

                // Position in face-local coordinates
                // Lines are centered on the face, offset perpendicular to their direction
                const perpOffset = pos - perpDimension / 2;
                const localX = -sinA * perpOffset;
                const localY = cosA * perpOffset;

                // Apply rotation for the line angle
                // For X-aligned faces, we need an extra 90° rotation because the face transform
                // maps X->Z, but we want lines to run in Y direction (across the face)
                let cutterToPosition = lineCutter;
                let effectiveAngle = angleRad;

                // Check if face is X-aligned (front/back faces)
                const isXAlignedFace = faceInfo.absNormal.x > faceInfo.absNormal.y &&
                                       faceInfo.absNormal.x > faceInfo.absNormal.z;
                if (isXAlignedFace) {
                    // Add 90° to rotate line from X direction to Y direction
                    effectiveAngle += Math.PI / 2;
                }

                if (effectiveAngle !== 0) {
                    const rotTrsf = new oc.gp_Trsf_1();
                    rotTrsf.SetRotation_1(
                        new oc.gp_Ax1_2(new oc.gp_Pnt_3(0, 0, 0), new oc.gp_Dir_4(0, 0, 1)),
                        effectiveAngle
                    );
                    cutterToPosition = lineCutter.Moved(new oc.TopLoc_Location_2(rotTrsf), false);
                }

                // Transform cutter to face position
                const trsf = _createFaceTransform(oc, faceInfo, localX, localY, actualDepth);
                const loc = new oc.TopLoc_Location_2(trsf);
                cutterShapes.push(cutterToPosition.Moved(loc, false));
            }
        } else {
            // Grid-based patterns (rect, square, circle, polygons)
            const positions = _calculateGridPositions(
                { ...options, spacing, width: effectiveWidth, height: effectiveHeight },
                faceWidth, faceHeight
            );

            // Create template cutter based on shape
            let templateCutter;

            if (resolvedShape === 'rect' || resolvedShape === 'square') {
                templateCutter = _createRectCutter(oc, effectiveWidth, effectiveHeight, actualDepth + 1, fillet, shear);
            } else if (resolvedShape === 'circle') {
                templateCutter = _createCircleCutter(oc, effectiveWidth, actualDepth + 1);
            } else if (resolvedShape === 'polygon' || typeof resolvedShape === 'number') {
                const polySides = typeof resolvedShape === 'number' ? resolvedShape : sides;
                templateCutter = _createPolygonCutter(oc, polySides, effectiveWidth, actualDepth + 1);
            } else {
                console.error(`[cutPattern] Unknown shape: ${shape}`);
                result._shape = this._shape;
                return result;
            }

            // Check if template cutter was created successfully
            if (!templateCutter) {
                console.error(`[cutPattern] Failed to create template cutter for shape: ${shape}`);
                result._shape = this._shape;
                return result;
            }

            console.log(`[cutPattern] Created template cutter for ${shape}, width=${effectiveWidth}, positions=${positions.length}`);

            // Position cutters at each grid location
            for (const pos of positions) {
                // pos.x and pos.y are in face-local coordinates (centered)
                const localX = pos.x;
                const localY = pos.y;

                // Only include if within face bounds (with some tolerance)
                const margin = Math.max(effectiveWidth, effectiveHeight) / 2;
                const halfWidth = faceWidth / 2;
                const halfHeight = faceHeight / 2;
                if (localX - margin < -halfWidth - 0.1 || localX + margin > halfWidth + 0.1 ||
                    localY - margin < -halfHeight - 0.1 || localY + margin > halfHeight + 0.1) {
                    continue;
                }

                // Apply individual rotation if specified
                let cutterToPosition = templateCutter;
                if (rotation !== 0) {
                    const rotTrsf = new oc.gp_Trsf_1();
                    rotTrsf.SetRotation_1(
                        new oc.gp_Ax1_2(new oc.gp_Pnt_3(0, 0, 0), new oc.gp_Dir_4(0, 0, 1)),
                        (rotation * Math.PI) / 180
                    );
                    cutterToPosition = templateCutter.Moved(new oc.TopLoc_Location_2(rotTrsf), false);
                }

                // Transform cutter to face position
                const trsf = _createFaceTransform(oc, faceInfo, localX, localY, actualDepth);
                const loc = new oc.TopLoc_Location_2(trsf);
                const positionedCutter = cutterToPosition.Moved(loc, false);

                // For 'whole' mode, check if cutter is fully contained before adding
                if (clip === 'whole' && clipBoundary && clipBoundary.success) {
                    if (_isFullyContained(oc, positionedCutter, clipBoundary.clipSolid)) {
                        cutterShapes.push(positionedCutter);
                    }
                    // Skip cutters not fully contained
                } else {
                    cutterShapes.push(positionedCutter);
                }
            }
        }

        console.log(`[cutPattern] Creating ${cutterShapes.length} cutters (${shape})${clip === 'whole' ? ' (filtered for whole mode)' : ''}`);

        if (cutterShapes.length > 0) {
            // Fuse all cutters together to eliminate internal faces
            // This is important when cutters are close together or overlapping
            let fusedCutters;

            if (cutterShapes.length === 1) {
                // Single cutter, no need to fuse
                fusedCutters = cutterShapes[0];
            } else {
                // Multiple cutters - fuse them together
                try {
                    // Create argument list with first cutter
                    const fuseArgs = new oc.TopTools_ListOfShape_1();
                    fuseArgs.Append_1(cutterShapes[0]);

                    // Create tools list with remaining cutters
                    const fuseTools = new oc.TopTools_ListOfShape_1();
                    for (let i = 1; i < cutterShapes.length; i++) {
                        fuseTools.Append_1(cutterShapes[i]);
                    }

                    const fuser = new oc.BRepAlgoAPI_Fuse_1();
                    fuser.SetArguments(fuseArgs);
                    fuser.SetTools(fuseTools);
                    fuser.Build(new oc.Message_ProgressRange_1());

                    if (fuser.IsDone()) {
                        fusedCutters = fuser.Shape();
                        console.log('[cutPattern] Fused cutters successfully');
                    } else {
                        // Fallback to compound if fuse fails
                        console.warn('[cutPattern] Fuse failed, falling back to compound');
                        const builder = new oc.BRep_Builder();
                        const compound = new oc.TopoDS_Compound();
                        builder.MakeCompound(compound);
                        for (const cutter of cutterShapes) {
                            builder.Add(compound, cutter);
                        }
                        fusedCutters = compound;
                    }

                    fuser.delete();
                    fuseArgs.delete();
                    fuseTools.delete();
                } catch (e) {
                    // Fallback to compound if fuse throws
                    console.warn('[cutPattern] Fuse exception, falling back to compound:', e.message);
                    const builder = new oc.BRep_Builder();
                    const compound = new oc.TopoDS_Compound();
                    builder.MakeCompound(compound);
                    for (const cutter of cutterShapes) {
                        builder.Add(compound, cutter);
                    }
                    fusedCutters = compound;
                }
            }

            // Apply clipping if enabled
            let clippedCutters = fusedCutters;
            if (clipBoundary && clipBoundary.success && clip !== 'none') {
                if (clip === 'partial') {
                    // Intersect cutters with clip boundary
                    const clipped = _clipToBoundary(oc, fusedCutters, clipBoundary.clipSolid);
                    if (clipped) {
                        clippedCutters = clipped;
                        console.log('[cutPattern] Applied partial clipping');
                    } else {
                        console.warn('[cutPattern] Partial clipping failed, using unclipped cutters');
                    }
                } else if (clip === 'whole') {
                    // For whole mode, we need to filter individual cutters
                    // If we already fused, we can still clip and the result will only
                    // include the parts that were fully inside
                    // But for true "whole shapes only", we should have filtered before fusing
                    // For now, use intersection as an approximation
                    const clipped = _clipToBoundary(oc, fusedCutters, clipBoundary.clipSolid);
                    if (clipped) {
                        clippedCutters = clipped;
                        console.log('[cutPattern] Applied whole clipping (intersection mode)');
                    } else {
                        console.warn('[cutPattern] Whole clipping failed, using unclipped cutters');
                    }
                }
            }

            // Perform batch boolean cut with fused cutters
            const toolList = new oc.TopTools_ListOfShape_1();
            toolList.Append_1(clippedCutters);

            const argList = new oc.TopTools_ListOfShape_1();
            argList.Append_1(this._shape);

            const cut = new oc.BRepAlgoAPI_Cut_1();
            cut.SetArguments(argList);
            cut.SetTools(toolList);
            cut.Build(new oc.Message_ProgressRange_1());

            if (cut.IsDone()) {
                const resultShape = cut.Shape();

                // Check if result is null/invalid
                if (!resultShape || resultShape.IsNull()) {
                    console.error('[cutPattern] Boolean cut produced null shape');
                    result._shape = this._shape;
                } else {
                    // Check if result has any content (not empty)
                    const explorer = new oc.TopExp_Explorer_2(resultShape, oc.TopAbs_ShapeEnum.TopAbs_SOLID, oc.TopAbs_ShapeEnum.TopAbs_SHAPE);
                    if (!explorer.More()) {
                        console.error('[cutPattern] Boolean cut produced empty shape (no solids)');
                        result._shape = this._shape;
                    } else {
                        result._shape = resultShape;
                        console.log('[cutPattern] Boolean cut succeeded');
                    }
                    explorer.delete();
                }

                // Check for warnings
                if (cut.HasWarnings && cut.HasWarnings()) {
                    console.warn('[cutPattern] Boolean cut has warnings');
                }
            } else {
                console.error('[cutPattern] Boolean cut failed (IsDone=false)');
                result._shape = this._shape;
            }

            cut.delete();
            toolList.delete();
            argList.delete();
        } else {
            result._shape = this._shape;
        }

    } catch (e) {
        console.error('[cutPattern] Exception:', e, 'Parameters:', {
            shape, width, height: height ?? width, depth, border, borderX, borderY,
            fillet, shear, rotation, spacing, wallThickness, stagger, columns, angle, direction
        });
        result._shape = this._shape;
    }

    return result;
};


// ============================================================
// cutBorder() - Cut out the center of a face, leaving a border frame
// ============================================================

/**
 * Cut the center out of the selected face, leaving a border frame.
 * Uses polygon offset algorithm internally.
 *
 * @param {Object} options - Cut options
 * @param {number} options.width - Border width in mm
 * @param {number} [options.depth=null] - Cut depth, null = through-cut
 * @returns {Workplane} New workplane with border cut
 *
 * @example
 *   // Create a 3mm border frame on a box
 *   box.faces(">Z").cutBorder({ width: 3 });
 *
 *   // Hexagon with 2mm border, 5mm deep
 *   hex.faces(">Z").cutBorder({ width: 2, depth: 5 });
 */
Workplane.prototype.cutBorder = function(options = {}) {
    const {
        width: borderWidth = 3,
        depth = null,
    } = options;

    if (!this._shape) {
        console.error('[cutBorder] No shape to cut');
        return this;
    }

    const oc = getOC();
    if (!oc) {
        console.error('[cutBorder] OpenCascade not initialized');
        return this;
    }

    const result = new Workplane(this._plane);
    result._cloneProperties(this);

    try {
        // Get the face to cut
        let face;
        if (this._selectedFaces && this._selectedFaces.length > 0) {
            face = this._selectedFaces[0];
        } else {
            // Default to top face
            const topFaceWp = this.faces(">Z");
            if (topFaceWp._selectedFaces && topFaceWp._selectedFaces.length > 0) {
                face = topFaceWp._selectedFaces[0];
            }
        }

        if (!face) {
            console.error('[cutBorder] No face selected');
            result._shape = this._shape;
            return result;
        }

        // Get face info for coordinate system
        const faceInfo = _getFaceCoordinateSystem(oc, face, this._shape);
        if (!faceInfo) {
            console.error('[cutBorder] Could not get face coordinate system');
            result._shape = this._shape;
            return result;
        }

        // Get the outer wire and vertices in order
        const outerWire = oc.BRepTools.OuterWire(face);
        if (!outerWire || outerWire.IsNull()) {
            console.error('[cutBorder] Could not get outer wire');
            result._shape = this._shape;
            return result;
        }

        // Collect vertices using WireExplorer for proper ordering
        const vertices = [];
        const wireExplorer = new oc.BRepTools_WireExplorer_1();
        wireExplorer.Init_1(outerWire);
        while (wireExplorer.More()) {
            const vertex = wireExplorer.CurrentVertex();
            const pnt = oc.BRep_Tool.Pnt(vertex);
            vertices.push({ x: pnt.X(), y: pnt.Y(), z: pnt.Z() });
            pnt.delete();
            wireExplorer.Next();
        }
        wireExplorer.delete();

        // Determine cut depth
        const bounds = this._getBoundingBox();
        const shapeHeight = bounds ? (bounds.zMax - bounds.zMin) : 10;
        const cutDepth = depth ?? (shapeHeight + 2);

        // Handle circles (single curved edge)
        const edges = [];
        const edgeExp = new oc.TopExp_Explorer_2(outerWire, oc.TopAbs_ShapeEnum.TopAbs_EDGE, oc.TopAbs_ShapeEnum.TopAbs_SHAPE);
        while (edgeExp.More()) {
            edges.push(oc.TopoDS.Edge_1(edgeExp.Current()));
            edgeExp.Next();
        }
        edgeExp.delete();

        let cutterShape = null;

        if (edges.length === 1 && vertices.length <= 2) {
            // Likely a circle
            const curve = new oc.BRepAdaptor_Curve_2(edges[0]);
            if (curve.GetType() === oc.GeomAbs_CurveType.GeomAbs_Circle) {
                const circle = curve.Circle();
                const radius = circle.Radius();
                const center = circle.Location();
                const innerRadius = radius - borderWidth;

                if (innerRadius > 0.1) {
                    // Create cylinder cutter
                    const cyl = new oc.BRepPrimAPI_MakeCylinder_1(innerRadius, cutDepth);
                    const trsf = new oc.gp_Trsf_1();
                    trsf.SetTranslation_1(new oc.gp_Vec_4(center.X(), center.Y(), faceInfo.center.z - 1));
                    cutterShape = cyl.Shape().Moved(new oc.TopLoc_Location_2(trsf), false);
                }
            }
            curve.delete();
        }

        // Handle polygons
        if (!cutterShape && vertices.length >= 3) {
            // Calculate polygon offset using edge-based algorithm
            let signedArea = 0;
            for (let i = 0; i < vertices.length; i++) {
                const v1 = vertices[i];
                const v2 = vertices[(i + 1) % vertices.length];
                signedArea += (v2.x - v1.x) * (v2.y + v1.y);
            }
            const cwFactor = signedArea > 0 ? 1 : -1;

            // Calculate inward normal for each edge
            const edgeNormals = [];
            for (let i = 0; i < vertices.length; i++) {
                const v1 = vertices[i];
                const v2 = vertices[(i + 1) % vertices.length];
                const dx = v2.x - v1.x;
                const dy = v2.y - v1.y;
                const len = Math.sqrt(dx*dx + dy*dy);
                if (len > 0.0001) {
                    edgeNormals.push({
                        x: cwFactor * dy / len,
                        y: cwFactor * -dx / len
                    });
                } else {
                    edgeNormals.push({ x: 0, y: 0 });
                }
            }

            // Find offset vertices
            const offsetVertices = [];
            for (let i = 0; i < vertices.length; i++) {
                const prevIdx = (i - 1 + vertices.length) % vertices.length;
                const v0 = vertices[prevIdx];
                const v1 = vertices[i];
                const n0 = edgeNormals[prevIdx];
                const nextIdx = (i + 1) % vertices.length;
                const v2 = vertices[nextIdx];
                const n1 = edgeNormals[i];

                const p1 = { x: v0.x + n0.x * borderWidth, y: v0.y + n0.y * borderWidth };
                const p2 = { x: v1.x + n0.x * borderWidth, y: v1.y + n0.y * borderWidth };
                const p3 = { x: v1.x + n1.x * borderWidth, y: v1.y + n1.y * borderWidth };
                const p4 = { x: v2.x + n1.x * borderWidth, y: v2.y + n1.y * borderWidth };

                const d1x = p2.x - p1.x;
                const d1y = p2.y - p1.y;
                const d2x = p4.x - p3.x;
                const d2y = p4.y - p3.y;

                const cross = d1x * d2y - d1y * d2x;

                if (Math.abs(cross) > 0.0001) {
                    const t = ((p3.x - p1.x) * d2y - (p3.y - p1.y) * d2x) / cross;
                    offsetVertices.push({
                        x: p1.x + t * d1x,
                        y: p1.y + t * d1y
                    });
                } else {
                    offsetVertices.push({
                        x: (p2.x + p3.x) / 2,
                        y: (p2.y + p3.y) / 2
                    });
                }
            }

            // For rectangular shapes, use a simple box cutter (more reliable)
            if (offsetVertices.length === 4) {
                // Find bounding box of offset vertices
                let minX = Infinity, maxX = -Infinity;
                let minY = Infinity, maxY = -Infinity;
                for (const v of offsetVertices) {
                    minX = Math.min(minX, v.x);
                    maxX = Math.max(maxX, v.x);
                    minY = Math.min(minY, v.y);
                    maxY = Math.max(maxY, v.y);
                }
                const innerWidth = maxX - minX;
                const innerHeight = maxY - minY;
                const centerX = (minX + maxX) / 2;
                const centerY = (minY + maxY) / 2;

                // Create box cutter
                const box = new oc.BRepPrimAPI_MakeBox_3(
                    new oc.gp_Pnt_3(minX, minY, faceInfo.center.z - cutDepth),
                    innerWidth, innerHeight, cutDepth * 2
                );
                cutterShape = box.Shape();
            } else if (offsetVertices.length >= 3) {
                // Build inner polygon wire for non-rectangular shapes
                const wireBuilder = new oc.BRepBuilderAPI_MakeWire_1();
                for (let i = 0; i < offsetVertices.length; i++) {
                    const p1 = offsetVertices[i];
                    const p2 = offsetVertices[(i + 1) % offsetVertices.length];
                    const edge = new oc.BRepBuilderAPI_MakeEdge_3(
                        new oc.gp_Pnt_3(p1.x, p1.y, 0),
                        new oc.gp_Pnt_3(p2.x, p2.y, 0)
                    ).Edge();
                    wireBuilder.Add_1(edge);
                }

                if (wireBuilder.IsDone()) {
                    const innerWire = wireBuilder.Wire();
                    const innerFace = new oc.BRepBuilderAPI_MakeFace_15(innerWire, true);
                    if (innerFace.IsDone()) {
                        // Extrude to create cutter
                        const prism = new oc.BRepPrimAPI_MakePrism_1(
                            innerFace.Face(),
                            new oc.gp_Vec_4(0, 0, cutDepth),
                            false, true
                        );
                        // Position the cutter
                        const trsf = new oc.gp_Trsf_1();
                        trsf.SetTranslation_1(new oc.gp_Vec_4(0, 0, faceInfo.center.z - 1));
                        cutterShape = prism.Shape().Moved(new oc.TopLoc_Location_2(trsf), false);
                    }
                }
            }
        }

        if (cutterShape) {
            // Perform the cut using the same approach as cutPattern
            const toolList = new oc.TopTools_ListOfShape_1();
            toolList.Append_1(cutterShape);

            const argList = new oc.TopTools_ListOfShape_1();
            argList.Append_1(this._shape);

            const cut = new oc.BRepAlgoAPI_Cut_1();
            cut.SetArguments(argList);
            cut.SetTools(toolList);
            cut.Build(new oc.Message_ProgressRange_1());

            if (cut.IsDone()) {
                const cutResult = cut.Shape();
                if (cutResult && !cutResult.IsNull()) {
                    result._shape = cutResult;
                } else {
                    console.error('[cutBorder] Cut result is null');
                    result._shape = this._shape;
                }
            } else {
                console.error('[cutBorder] Boolean cut failed (IsDone=false)');
                result._shape = this._shape;
            }
            cut.delete();
            toolList.delete();
            argList.delete();
        } else {
            console.error('[cutBorder] Could not create cutter shape');
            result._shape = this._shape;
        }

    } catch (e) {
        console.error('[cutBorder] Exception:', e);
        result._shape = this._shape;
    }

    return result;
};


// ============================================================
// EXPORTS
// ============================================================

export { };
