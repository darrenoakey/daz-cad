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

import { Workplane, getOC } from './cad.js';


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

    const wire = wireBuilder.Wire();
    const face = new oc.BRepBuilderAPI_MakeFace_15(wire, true);
    const prism = new oc.BRepPrimAPI_MakePrism_1(
        face.Face(),
        new oc.gp_Vec_4(0, 0, depth),
        false, true
    );

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
        spacing = 2.0,
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

    const actualSpacingX = spacingX ?? spacing;
    const actualSpacingY = spacingY ?? spacing;
    const actualBorderX = borderX ?? border;
    const actualBorderY = borderY ?? border;
    const actualRowGap = rowGap ?? columnGap;
    const actualRows = rows ?? 1;

    // Calculate effective spacing if wallThickness is specified
    let effectiveSpacingX = actualSpacingX;
    let effectiveSpacingY = actualSpacingY;

    if (wallThickness !== null) {
        const effectiveWidth = width;
        const effectiveHeight = height ?? width;
        effectiveSpacingX = effectiveWidth + wallThickness;
        effectiveSpacingY = effectiveHeight + wallThickness;
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
// MAIN cutPattern() METHOD
// ============================================================

/**
 * Cut a unified pattern into a selected face or the top of a shape
 *
 * This is a comprehensive pattern cutting method that supports:
 * - Multiple shape types: line, rect, square, circle, hexagon, octagon, triangle, or any n-sided polygon
 * - Full layout control: spacing, borders, column/row groups, staggering, pattern rotation
 * - Shape modifiers: fillet, round ends, shear, individual rotation
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
 * @param {number} [options.spacing=2.0] - Space between shape centers
 * @param {number} [options.spacingX=null] - Override X spacing
 * @param {number} [options.spacingY=null] - Override Y spacing
 * @param {number} [options.wallThickness=null] - Alternative: specify wall between shapes
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
 * @returns {Workplane} - New Workplane with pattern cut
 *
 * @example
 * // Horizontal grip lines
 * box.faces(">Z").cutPattern({
 *     shape: 'line',
 *     width: 1.0,
 *     spacing: 2.0,
 *     depth: 0.4,
 *     border: 3.0
 * });
 *
 * @example
 * // Hex pattern holes
 * box.faces(">Z").cutPattern({
 *     shape: 'hexagon',
 *     width: 5,
 *     wallThickness: 0.6,
 *     stagger: true,
 *     depth: null  // through
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
        spacing = 2.0,
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
        angle = 0,
        direction = 'x'
    } = options;

    const shape = effectiveShape;
    const width = effectiveWidth;

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
        // Determine face bounds
        let faceBbox;
        let cutZ;

        if (this._selectedFaces && this._selectedFaces.length > 0) {
            // Use selected face
            const face = this._selectedFaces[0];
            faceBbox = this._getFaceBoundingBox(face);
            if (!faceBbox) {
                console.error('[cutPattern] Could not get face bounding box');
                result._shape = this._shape;
                return result;
            }
            cutZ = faceBbox.maxZ;
        } else {
            // Fall back to shape bounding box
            faceBbox = this._getBoundingBox();
            if (!faceBbox) {
                console.error('[cutPattern] Could not get bounding box');
                result._shape = this._shape;
                return result;
            }
            cutZ = faceBbox.maxZ;
        }

        const faceWidth = faceBbox.sizeX;
        const faceHeight = faceBbox.sizeY;
        const faceCenterX = faceBbox.centerX;
        const faceCenterY = faceBbox.centerY;

        // Calculate cut depth
        const shapeBbox = this._getBoundingBox();
        const maxDepth = shapeBbox ? shapeBbox.sizeZ + 2 : 100;
        const actualDepth = depth ?? maxDepth;

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
            // Lines are a special case - they span the face width/height
            const lineWidth = width;
            const lineLength = length ?? (direction === 'x' ? faceWidth - 2 * actualBorderX : faceHeight - 2 * actualBorderY);

            // Calculate line positions
            const startPos = direction === 'x' ? actualBorderY : actualBorderX;
            const endPos = direction === 'x' ? faceHeight - actualBorderY : faceWidth - actualBorderX;
            const actualSpacing = spacingX ?? spacingY ?? spacing;

            const numLines = Math.floor((endPos - startPos) / actualSpacing);
            const totalSpan = numLines * actualSpacing;
            const offset = (endPos - startPos - totalSpan) / 2;

            for (let i = 0; i <= numLines; i++) {
                const pos = startPos + offset + i * actualSpacing;

                // Create line cutter
                const lineCutter = _createLineCutter(oc, lineWidth, lineLength, actualDepth + 1, roundEnds);

                // Position and orient the cutter
                const trsf = new oc.gp_Trsf_1();

                if (direction === 'x') {
                    // Horizontal lines
                    const x = faceCenterX;
                    const y = faceBbox.minY + pos;

                    if (angle !== 0) {
                        const rotTrsf = new oc.gp_Trsf_1();
                        rotTrsf.SetRotation_1(
                            new oc.gp_Ax1_2(new oc.gp_Pnt_3(0, 0, 0), new oc.gp_Dir_4(0, 0, 1)),
                            (angle * Math.PI) / 180
                        );
                        trsf.Multiply(rotTrsf);
                    }

                    const transTrsf = new oc.gp_Trsf_1();
                    transTrsf.SetTranslation_1(new oc.gp_Vec_4(x, y, cutZ - actualDepth));
                    trsf.Multiply(transTrsf);
                } else {
                    // Vertical lines - rotate 90 degrees
                    const x = faceBbox.minX + pos;
                    const y = faceCenterY;

                    const rotTrsf = new oc.gp_Trsf_1();
                    rotTrsf.SetRotation_1(
                        new oc.gp_Ax1_2(new oc.gp_Pnt_3(0, 0, 0), new oc.gp_Dir_4(0, 0, 1)),
                        Math.PI / 2 + (angle * Math.PI) / 180
                    );
                    trsf.Multiply(rotTrsf);

                    const transTrsf = new oc.gp_Trsf_1();
                    transTrsf.SetTranslation_1(new oc.gp_Vec_4(x, y, cutZ - actualDepth));
                    trsf.Multiply(transTrsf);
                }

                const loc = new oc.TopLoc_Location_2(trsf);
                cutterShapes.push(lineCutter.Moved(loc, false));
            }
        } else {
            // Grid-based patterns (rect, square, circle, polygons)
            const positions = _calculateGridPositions(
                { ...options, width: effectiveWidth, height: effectiveHeight },
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

            // Position cutters at each grid location
            for (const pos of positions) {
                const trsf = new oc.gp_Trsf_1();

                // Apply individual rotation if specified
                if (rotation !== 0) {
                    const rotTrsf = new oc.gp_Trsf_1();
                    rotTrsf.SetRotation_1(
                        new oc.gp_Ax1_2(new oc.gp_Pnt_3(0, 0, 0), new oc.gp_Dir_4(0, 0, 1)),
                        (rotation * Math.PI) / 180
                    );
                    trsf.Multiply(rotTrsf);
                }

                // Translate to position
                const x = faceCenterX + pos.x;
                const y = faceCenterY + pos.y;

                // Only include if within face bounds (with some tolerance)
                const margin = Math.max(effectiveWidth, effectiveHeight) / 2;
                if (x - margin < faceBbox.minX - 0.1 || x + margin > faceBbox.maxX + 0.1 ||
                    y - margin < faceBbox.minY - 0.1 || y + margin > faceBbox.maxY + 0.1) {
                    continue;
                }

                const transTrsf = new oc.gp_Trsf_1();
                transTrsf.SetTranslation_1(new oc.gp_Vec_4(x, y, cutZ - actualDepth));
                trsf.Multiply(transTrsf);

                const loc = new oc.TopLoc_Location_2(trsf);
                cutterShapes.push(templateCutter.Moved(loc, false));
            }
        }

        console.log(`[cutPattern] Creating ${cutterShapes.length} cutters (${shape})`);

        if (cutterShapes.length > 0) {
            // Create clipping box to trim cutters at border edges
            // This ensures shapes don't extend past the border
            const clipMinX = faceBbox.minX + actualBorderX;
            const clipMaxX = faceBbox.maxX - actualBorderX;
            const clipMinY = faceBbox.minY + actualBorderY;
            const clipMaxY = faceBbox.maxY - actualBorderY;
            const clipZ = cutZ - actualDepth - 1;
            const clipHeight = actualDepth + 3;

            const clipBox = new oc.BRepPrimAPI_MakeBox_3(
                new oc.gp_Pnt_3(clipMinX, clipMinY, clipZ),
                clipMaxX - clipMinX,
                clipMaxY - clipMinY,
                clipHeight
            );
            const clipShape = clipBox.Shape();

            // Create compound of all cutters
            const builder = new oc.BRep_Builder();
            const compound = new oc.TopoDS_Compound();
            builder.MakeCompound(compound);
            for (const cutter of cutterShapes) {
                builder.Add(compound, cutter);
            }

            // Intersect compound with clip box to trim at borders
            const commonOp = new oc.BRepAlgoAPI_Common_3(compound, clipShape, new oc.Message_ProgressRange_1());
            let clippedCutters;
            if (commonOp.IsDone()) {
                clippedCutters = commonOp.Shape();
            } else {
                console.warn('[cutPattern] Clipping failed, using unclipped cutters');
                clippedCutters = compound;
            }
            commonOp.delete();

            // Perform batch boolean cut with clipped cutters
            const toolList = new oc.TopTools_ListOfShape_1();
            toolList.Append_1(clippedCutters);

            const argList = new oc.TopTools_ListOfShape_1();
            argList.Append_1(this._shape);

            const cut = new oc.BRepAlgoAPI_Cut_1();
            cut.SetArguments(argList);
            cut.SetTools(toolList);
            cut.Build(new oc.Message_ProgressRange_1());

            if (cut.IsDone()) {
                result._shape = cut.Shape();
            } else {
                console.error('[cutPattern] Boolean cut failed');
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
// EXPORTS
// ============================================================

export { };
