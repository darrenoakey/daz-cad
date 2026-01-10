/**
 * Gridfinity.js - Gridfinity bin/insert generator for daz-cad-2
 *
 * Extends the CAD library with Gridfinity-specific operations:
 * - Gridfinity.bin() - Create solid gridfinity bin with standardized base
 * - Gridfinity.plug() - Create solid insert plugs (fits inside a bin)
 * - Workplane.cutRectGrid() - Optimized rectangular cutout grid
 * - Workplane.cutCircleGrid() - Optimized circular cutout grid
 *
 * Example - Solid bin with cutouts:
 *   const bin = Gridfinity.bin({ x: 3, y: 2, z: 5 })
 *       .cutRectGrid({ width: 30, height: 40, count: 2, fillet: 3 });
 *
 * Example - Insert plug for existing bin:
 *   const plug = Gridfinity.plug({ x: 2, y: 3, z: 3 })
 *       .cutCircleGrid({ diameter: 20, count: 4 });
 */

import { Workplane, getOC } from './cad.js';

// ============================================================
// GRIDFINITY CONSTANTS
// ============================================================

const Gridfinity = {
    // Grid dimensions (from gridfinity spec)
    UNIT_SIZE: 42,           // mm per grid unit (x/y)
    UNIT_HEIGHT: 7,          // mm per height unit (z)
    BIN_CLEARANCE: 0.25,     // clearance from bin exterior (each side)
    OUTER_RADIUS: 3.75,      // corner radius of bin
    WALL_THICKNESS: 1.2,     // shell thickness of bin

    // Base profile dimensions (stepped z-shaped profile)
    // See: https://github.com/KittyCAD/kcl-samples/blob/main/gridfinity-bins-stacking-lip/main.kcl
    BASE_HEIGHT: 4.75,       // total base height (0.8 + 1.8 + 2.15)
    STEP1_HEIGHT: 0.8,       // first 45° step (bottom)
    STEP2_HEIGHT: 1.8,       // vertical wall section
    STEP3_HEIGHT: 2.15,      // second 45° step (top)
    BASE_TAPER: 2.95,        // total horizontal taper per side (0.8 + 2.15)

    // Insert parameters
    TOLERANCE: 0.30,         // wall clearance for inner plug
    TOP_GAP: 1.0,            // gap above stackable plug for extraction
    STACKING_LIP: 4.4,       // height of stacking lip

    // Cutout defaults
    MIN_SPACING_RECT: 0.6,   // minimum space between rectangular cutouts
    MIN_SPACING_CIRCLE: 2.0, // minimum space between circular cutouts
    MIN_BORDER: 2.0,         // default minimum shell thickness

    /**
     * Create a single base unit with stepped profile (internal helper)
     * @private
     */
    _createBaseUnit(cellX, cellY) {
        // Single cell dimensions
        const cellSize = this.UNIT_SIZE - 2 * this.BIN_CLEARANCE; // 41.5mm
        const outerRadius = this.OUTER_RADIUS - this.BIN_CLEARANCE; // 3.5mm

        // Dimensions at each level (bottom to top)
        // At Z=0: smallest (cellSize - 2 * BASE_TAPER)
        // At Z=BASE_HEIGHT: full cellSize
        const bottomSize = cellSize - 2 * this.BASE_TAPER; // 35.6mm
        const middleSize = bottomSize + 2 * this.STEP1_HEIGHT; // 37.2mm (after first 45° step)

        // Calculate corner radii for each level (proportional)
        const bottomRadius = Math.max(outerRadius - this.BASE_TAPER, 0.5);
        const middleRadius = Math.max(outerRadius - this.STEP3_HEIGHT, 0.5);

        // Build the stepped base from 3 layers
        // Layer 1: Bottom step (0.8mm tall, 35.6mm -> 37.2mm, 45° sides)
        let layer1 = new Workplane("XY")
            .box(middleSize, middleSize, this.STEP1_HEIGHT)
            .translate(cellX, cellY, this.STEP1_HEIGHT / 2);
        layer1 = layer1.edges("|Z").fillet(middleRadius);
        layer1 = layer1.faces("<Z").edges().chamfer(this.STEP1_HEIGHT - 0.01);

        // Layer 2: Middle section (1.8mm tall, 37.2mm constant, vertical sides)
        let layer2 = new Workplane("XY")
            .box(middleSize, middleSize, this.STEP2_HEIGHT)
            .translate(cellX, cellY, this.STEP1_HEIGHT + this.STEP2_HEIGHT / 2);
        layer2 = layer2.edges("|Z").fillet(middleRadius);

        // Layer 3: Top step (2.15mm tall, 37.2mm -> 41.5mm, 45° sides)
        let layer3 = new Workplane("XY")
            .box(cellSize, cellSize, this.STEP3_HEIGHT)
            .translate(cellX, cellY, this.STEP1_HEIGHT + this.STEP2_HEIGHT + this.STEP3_HEIGHT / 2);
        layer3 = layer3.edges("|Z").fillet(outerRadius);
        layer3 = layer3.faces("<Z").edges().chamfer(this.STEP3_HEIGHT - 0.01);

        // Union all layers
        let baseUnit = layer1.union(layer2).union(layer3);

        return baseUnit;
    },

    /**
     * Create a solid gridfinity bin with standardized base profile
     *
     * This creates a complete gridfinity-compatible unit with:
     * - Separate base feet for each grid cell
     * - Stepped z-shaped profile for baseplate compatibility
     * - Rounded corners (3.5mm radius)
     *
     * @param {Object} options
     * @param {number} options.x - X dimension in grid units (1 unit = 42mm)
     * @param {number} options.y - Y dimension in grid units
     * @param {number} options.z - Z dimension in height units (1 unit = 7mm)
     * @param {boolean} [options.stackable=false] - Include stacking lip at top
     * @param {boolean} [options.solid=true] - Create solid (true) or hollow shell (false)
     * @returns {Workplane} - A Workplane object with the gridfinity bin
     */
    bin(options) {
        const {
            x,
            y,
            z,
            stackable = false,
            solid = true
        } = options;

        if (!x || !y || !z) {
            console.error('[Gridfinity] bin requires x, y, z dimensions');
            return new Workplane("XY");
        }

        // Calculate outer dimensions for the body
        const outerX = x * this.UNIT_SIZE - 2 * this.BIN_CLEARANCE;
        const outerY = y * this.UNIT_SIZE - 2 * this.BIN_CLEARANCE;
        const outerRadius = this.OUTER_RADIUS - this.BIN_CLEARANCE;

        // Calculate total height (body height above base)
        const bodyHeight = z * this.UNIT_HEIGHT - this.BASE_HEIGHT;
        const totalHeight = z * this.UNIT_HEIGHT;

        console.log(`[Gridfinity] Creating ${x}x${y}x${z} bin:`);
        console.log(`  Grid cells: ${x * y} (${x}x${y})`);
        console.log(`  Outer dimensions: ${outerX.toFixed(2)} x ${outerY.toFixed(2)} x ${totalHeight.toFixed(2)} mm`);
        console.log(`  Base height: ${this.BASE_HEIGHT} mm (stepped profile)`);
        console.log(`  Body height: ${bodyHeight.toFixed(2)} mm`);

        // Create base units for each grid cell
        let result = null;
        const startX = -(x - 1) * this.UNIT_SIZE / 2;
        const startY = -(y - 1) * this.UNIT_SIZE / 2;

        for (let gy = 0; gy < y; gy++) {
            for (let gx = 0; gx < x; gx++) {
                const cellX = startX + gx * this.UNIT_SIZE;
                const cellY = startY + gy * this.UNIT_SIZE;

                const baseUnit = this._createBaseUnit(cellX, cellY);

                if (result === null) {
                    result = baseUnit;
                } else {
                    result = result.union(baseUnit);
                }
            }
        }

        // Create the body above the base (overlap into base to ensure solid union)
        const overlap = 0.5; // mm overlap with base for solid connection
        if (bodyHeight > 0) {
            const adjustedBodyHeight = bodyHeight + overlap;
            const bodyStartZ = this.BASE_HEIGHT - overlap; // Start inside the base
            let body = new Workplane("XY")
                .box(outerX, outerY, adjustedBodyHeight)
                .translate(0, 0, bodyStartZ + adjustedBodyHeight / 2);
            body = body.edges("|Z").fillet(outerRadius);

            result = result.union(body);
        }

        // If hollow (shell), cut out the interior
        if (!solid) {
            const innerX = outerX - 2 * this.WALL_THICKNESS;
            const innerY = outerY - 2 * this.WALL_THICKNESS;
            const innerRadius = Math.max(outerRadius - this.WALL_THICKNESS, 0.5);
            const cavityHeight = totalHeight - this.BASE_HEIGHT + 1; // +1 to cut through top

            let cavity = new Workplane("XY")
                .box(innerX, innerY, cavityHeight)
                .edges("|Z")
                .fillet(innerRadius)
                .translate(0, 0, this.BASE_HEIGHT + cavityHeight / 2 - 0.5);

            result = result.cut(cavity);
        }

        if (stackable) {
            console.log(`  Note: Stacking lip not yet implemented - using flat top`);
        }

        return result;
    },

    /**
     * Create a solid gridfinity insert plug (fits inside a bin)
     *
     * @param {Object} options
     * @param {number} options.x - X dimension in grid units (1 unit = 42mm)
     * @param {number} options.y - Y dimension in grid units
     * @param {number} options.z - Z dimension in height units (1 unit = 7mm)
     * @param {number} [options.tolerance=0.30] - Wall clearance in mm
     * @param {boolean} [options.stackable=true] - Account for stacking lip
     * @returns {Workplane} - A Workplane object with the plug shape
     */
    plug(options) {
        const {
            x,
            y,
            z,
            tolerance = this.TOLERANCE,
            stackable = true
        } = options;

        if (!x || !y || !z) {
            console.error('[Gridfinity] plug requires x, y, z dimensions');
            return new Workplane("XY");
        }

        // Calculate inner dimensions
        // inner = cols * bin_size - 2 * (bin_clearance + wall_thickness + tolerance)
        const innerX = x * this.UNIT_SIZE - 2 * (this.BIN_CLEARANCE + this.WALL_THICKNESS + tolerance);
        const innerY = y * this.UNIT_SIZE - 2 * (this.BIN_CLEARANCE + this.WALL_THICKNESS + tolerance);
        const innerRadius = Math.max(this.OUTER_RADIUS - this.BIN_CLEARANCE - this.WALL_THICKNESS - tolerance, 0);

        // Calculate height based on stackability
        let innerZ;
        if (stackable) {
            // With stacking lip, leave room for the lip and a gap to pull out
            innerZ = z * this.UNIT_HEIGHT - this.TOP_GAP;
        } else {
            // Without stacking lip, extend all the way to the top
            innerZ = z * this.UNIT_HEIGHT;
        }

        console.log(`[Gridfinity] Creating ${x}x${y}x${z} plug:`);
        console.log(`  Inner dimensions: ${innerX.toFixed(2)} x ${innerY.toFixed(2)} x ${innerZ.toFixed(2)} mm`);
        console.log(`  Corner radius: ${innerRadius.toFixed(2)} mm`);
        console.log(`  Stackable: ${stackable}`);

        // Create rounded rectangle and extrude
        // For now, use box with fillet since we don't have roundedBox primitive
        // The fillet radius needs to be applied to vertical edges only
        const result = new Workplane("XY")
            .box(innerX, innerY, innerZ)
            .edges("|Z")
            .fillet(innerRadius);

        return result;
    }
};


// ============================================================
// GRID OPTIMIZATION ALGORITHMS
// ============================================================

/**
 * Find optimal grid layout for rectangular cutouts
 *
 * @param {number} partX - Available width in mm
 * @param {number} partY - Available height in mm
 * @param {number} rectX - Cutout width in mm
 * @param {number} rectY - Cutout height in mm
 * @param {number} minSpacing - Minimum spacing between cutouts
 * @param {number|null} count - Target count (null = maximize)
 * @returns {Object} - { cols, rows, spacingX, spacingY }
 */
function bestGrid(partX, partY, rectX, rectY, minSpacing = 0.6, count = null) {
    const maxCols = Math.floor((partX + minSpacing) / (rectX + minSpacing));
    const maxRows = Math.floor((partY + minSpacing) / (rectY + minSpacing));

    console.log(`[bestGrid] Part: ${partX.toFixed(1)}x${partY.toFixed(1)}, Rect: ${rectX}x${rectY}`);
    console.log(`[bestGrid] Max possible: ${maxCols}x${maxRows}`);

    if (maxCols === 0 || maxRows === 0) {
        throw new Error('Cutouts do not fit - part too small');
    }

    let best = null;

    for (let rows = 1; rows <= maxRows; rows++) {
        for (let cols = 1; cols <= maxCols; cols++) {
            const total = rows * cols;

            if (count !== null && total < count) {
                continue; // not enough pockets
            }

            const sx = (partX - cols * rectX) / (cols + 1);
            const sy = (partY - rows * rectY) / (rows + 1);

            if (sx < minSpacing || sy < minSpacing) {
                continue; // spacing too tight
            }

            // Score: prefer more square-like arrangements (minimize |rows - cols|), then maximize count
            const squareness = Math.abs(rows - cols);
            const score = [squareness, -total];
            const candidate = { total, cols, rows, sx, sy, score };

            if (best === null || compareTuples(candidate.score, best.score) < 0) {
                best = candidate;
            }
        }
    }

    if (best === null) {
        throw new Error(`Unable to fit rectangular cutouts with >= ${minSpacing}mm spacing`);
    }

    console.log(`[bestGrid] Selected: ${best.cols}x${best.rows} = ${best.total} cutouts`);
    console.log(`[bestGrid] Spacing: ${best.sx.toFixed(2)} x ${best.sy.toFixed(2)} mm`);

    return {
        cols: best.cols,
        rows: best.rows,
        spacingX: best.sx,
        spacingY: best.sy
    };
}

/**
 * Find optimal grid layout for circular cutouts
 *
 * @param {number} partX - Available width in mm
 * @param {number} partY - Available height in mm
 * @param {number} radius - Circle radius in mm
 * @param {number} minSpacing - Minimum spacing between circles
 * @param {number|null} count - Target count (null = maximize)
 * @returns {Object} - { cols, rows, spacingX, spacingY }
 */
function bestCircleGrid(partX, partY, radius, minSpacing = 2.0, count = null) {
    const diameter = 2 * radius;
    const maxCols = Math.floor((partX + minSpacing) / (diameter + minSpacing));
    const maxRows = Math.floor((partY + minSpacing) / (diameter + minSpacing));

    console.log(`[bestCircleGrid] Part: ${partX.toFixed(1)}x${partY.toFixed(1)}, Diameter: ${diameter}`);
    console.log(`[bestCircleGrid] Max possible: ${maxCols}x${maxRows}`);

    if (maxCols === 0 || maxRows === 0) {
        throw new Error('Circles do not fit - part too small or radius too large');
    }

    let best = null;

    for (let rows = 1; rows <= maxRows; rows++) {
        for (let cols = 1; cols <= maxCols; cols++) {
            const total = rows * cols;

            if (count !== null && total < count) {
                continue;
            }

            const sx = (partX - cols * diameter) / (cols + 1);
            const sy = (partY - rows * diameter) / (rows + 1);

            if (sx < minSpacing || sy < minSpacing) {
                continue;
            }

            // Score: prefer more square-like arrangements (minimize |rows - cols|), then maximize count
            const squareness = Math.abs(rows - cols);
            const score = [squareness, -total];
            const candidate = { total, cols, rows, sx, sy, score };

            if (best === null || compareTuples(candidate.score, best.score) < 0) {
                best = candidate;
            }
        }
    }

    if (best === null) {
        throw new Error(`Unable to fit circular cutouts with >= ${minSpacing}mm spacing`);
    }

    console.log(`[bestCircleGrid] Selected: ${best.cols}x${best.rows} = ${best.total} circles`);
    console.log(`[bestCircleGrid] Spacing: ${best.sx.toFixed(2)} x ${best.sy.toFixed(2)} mm`);

    return {
        cols: best.cols,
        rows: best.rows,
        spacingX: best.sx,
        spacingY: best.sy
    };
}

/**
 * Compare two tuples lexicographically
 */
function compareTuples(a, b) {
    for (let i = 0; i < Math.min(a.length, b.length); i++) {
        if (a[i] < b[i]) return -1;
        if (a[i] > b[i]) return 1;
    }
    return a.length - b.length;
}


// ============================================================
// WORKPLANE EXTENSIONS
// ============================================================

/**
 * Cut a grid of rectangular pockets with automatic spacing optimization
 *
 * @param {Object} options
 * @param {number} options.width - Pocket width in mm
 * @param {number} options.height - Pocket height in mm
 * @param {number} [options.count=null] - Target count (null = maximize)
 * @param {number} [options.fillet=0] - Corner fillet radius
 * @param {number} [options.depth=null] - Cut depth (null = auto: shape height - minBorder)
 * @param {number} [options.minBorder=2.0] - Minimum shell thickness
 * @param {number} [options.minSpacing=0.6] - Minimum spacing between cutouts
 * @returns {Workplane} - New Workplane with cuts applied
 */
Workplane.prototype.cutRectGrid = function(options) {
    const {
        width,
        height,
        count = null,
        fillet = 0,
        depth = null,
        minBorder = Gridfinity.MIN_BORDER,
        minSpacing = Gridfinity.MIN_SPACING_RECT
    } = options;

    if (!width || !height) {
        console.error('[cutRectGrid] width and height are required');
        return this;
    }

    if (!this._shape) {
        console.error('[cutRectGrid] No shape to cut');
        return this;
    }

    // Get bounding box of current shape
    const bbox = this._getBoundingBox();
    if (!bbox) {
        console.error('[cutRectGrid] Could not get bounding box');
        return this;
    }

    const partX = bbox.sizeX - 2 * minBorder;
    const partY = bbox.sizeY - 2 * minBorder;

    // Calculate depth
    let cutDepth;
    if (depth !== null) {
        cutDepth = depth;
        if (cutDepth > bbox.sizeZ - minBorder) {
            console.warn(`[cutRectGrid] Depth ${cutDepth}mm exceeds max ${bbox.sizeZ - minBorder}mm`);
            cutDepth = bbox.sizeZ - minBorder;
        }
    } else {
        cutDepth = bbox.sizeZ - minBorder;
    }

    if (cutDepth <= 0) {
        console.error('[cutRectGrid] Computed depth <= 0 - part too shallow');
        return this;
    }

    console.log(`[cutRectGrid] Part: ${bbox.sizeX.toFixed(1)}x${bbox.sizeY.toFixed(1)}x${bbox.sizeZ.toFixed(1)} mm`);
    console.log(`[cutRectGrid] Usable area: ${partX.toFixed(1)}x${partY.toFixed(1)} mm`);
    console.log(`[cutRectGrid] Cut depth: ${cutDepth.toFixed(2)} mm`);

    // Get optimal grid layout
    let grid;
    try {
        grid = bestGrid(partX, partY, width, height, minSpacing, count);
    } catch (e) {
        console.error('[cutRectGrid] ' + e.message);
        return this;
    }

    // Calculate starting positions (centered)
    const startX = bbox.centerX - (grid.cols - 1) * (width + grid.spacingX) / 2;
    const startY = bbox.centerY - (grid.rows - 1) * (height + grid.spacingY) / 2;

    // Apply fillet (clamp to valid range)
    const actualFillet = Math.min(fillet, Math.min(width, height) / 2 - 0.01);

    console.log(`[cutRectGrid] Creating ${grid.cols}x${grid.rows} = ${grid.cols * grid.rows} cutouts`);

    // Create and subtract all cutters
    let result = this;

    for (let r = 0; r < grid.rows; r++) {
        const cy = startY + r * (height + grid.spacingY);
        for (let c = 0; c < grid.cols; c++) {
            const cx = startX + c * (width + grid.spacingX);

            // Create cutter at this position
            // Position at top of shape and cut down
            let cutter = new Workplane("XY")
                .box(width, height, cutDepth + 1) // +1 to ensure clean cut through top
                .translate(cx, cy, bbox.maxZ - cutDepth / 2 + 0.5);

            if (actualFillet > 0) {
                cutter = cutter.edges("|Z").fillet(actualFillet);
            }

            result = result.cut(cutter);
        }
    }

    return result;
};


/**
 * Cut a grid of circular pockets with automatic spacing optimization
 *
 * @param {Object} options
 * @param {number} options.radius - Circle radius in mm (or use diameter)
 * @param {number} [options.diameter] - Circle diameter in mm (alternative to radius)
 * @param {number} [options.count=null] - Target count (null = maximize)
 * @param {number} [options.depth=null] - Cut depth (null = auto: shape height - minBorder)
 * @param {number} [options.minBorder=2.0] - Minimum shell thickness
 * @param {number} [options.minSpacing=2.0] - Minimum spacing between circles
 * @returns {Workplane} - New Workplane with cuts applied
 */
Workplane.prototype.cutCircleGrid = function(options) {
    let {
        radius,
        diameter,
        count = null,
        depth = null,
        minBorder = Gridfinity.MIN_BORDER,
        minSpacing = Gridfinity.MIN_SPACING_CIRCLE
    } = options;

    // Handle diameter vs radius
    if (diameter !== undefined) {
        radius = diameter / 2;
    }

    if (!radius) {
        console.error('[cutCircleGrid] radius or diameter is required');
        return this;
    }

    if (!this._shape) {
        console.error('[cutCircleGrid] No shape to cut');
        return this;
    }

    // Get bounding box of current shape
    const bbox = this._getBoundingBox();
    if (!bbox) {
        console.error('[cutCircleGrid] Could not get bounding box');
        return this;
    }

    const partX = bbox.sizeX - 2 * minBorder;
    const partY = bbox.sizeY - 2 * minBorder;

    // Calculate depth
    let cutDepth;
    if (depth !== null) {
        cutDepth = depth;
        if (cutDepth > bbox.sizeZ - minBorder) {
            console.warn(`[cutCircleGrid] Depth ${cutDepth}mm exceeds max ${bbox.sizeZ - minBorder}mm`);
            cutDepth = bbox.sizeZ - minBorder;
        }
    } else {
        cutDepth = bbox.sizeZ - minBorder;
    }

    if (cutDepth <= 0) {
        console.error('[cutCircleGrid] Computed depth <= 0 - part too shallow');
        return this;
    }

    console.log(`[cutCircleGrid] Part: ${bbox.sizeX.toFixed(1)}x${bbox.sizeY.toFixed(1)}x${bbox.sizeZ.toFixed(1)} mm`);
    console.log(`[cutCircleGrid] Usable area: ${partX.toFixed(1)}x${partY.toFixed(1)} mm`);
    console.log(`[cutCircleGrid] Circle radius: ${radius} mm`);
    console.log(`[cutCircleGrid] Cut depth: ${cutDepth.toFixed(2)} mm`);

    // Get optimal grid layout
    let grid;
    try {
        grid = bestCircleGrid(partX, partY, radius, minSpacing, count);
    } catch (e) {
        console.error('[cutCircleGrid] ' + e.message);
        return this;
    }

    // Calculate starting positions (centered)
    const diameter2 = 2 * radius;
    const startX = bbox.centerX - (grid.cols - 1) * (diameter2 + grid.spacingX) / 2;
    const startY = bbox.centerY - (grid.rows - 1) * (diameter2 + grid.spacingY) / 2;

    console.log(`[cutCircleGrid] Creating ${grid.cols}x${grid.rows} = ${grid.cols * grid.rows} circles`);

    // Create and subtract all cutters
    let result = this;

    for (let r = 0; r < grid.rows; r++) {
        const cy = startY + r * (diameter2 + grid.spacingY);
        for (let c = 0; c < grid.cols; c++) {
            const cx = startX + c * (diameter2 + grid.spacingX);

            // Create cylinder cutter at this position
            const cutter = new Workplane("XY")
                .cylinder(radius, cutDepth + 1)
                .translate(cx, cy, bbox.maxZ - cutDepth / 2 + 0.5);

            result = result.cut(cutter);
        }
    }

    return result;
};


/**
 * Helper to get bounding box info from current shape
 * @private
 */
Workplane.prototype._getBoundingBox = function() {
    if (!this._shape) return null;

    try {
        const oc = this._getOC();
        const bndBox = new oc.Bnd_Box_1();
        oc.BRepBndLib.Add(this._shape, bndBox, false);

        const xMin = { current: 0 }, yMin = { current: 0 }, zMin = { current: 0 };
        const xMax = { current: 0 }, yMax = { current: 0 }, zMax = { current: 0 };
        bndBox.Get(xMin, yMin, zMin, xMax, yMax, zMax);
        bndBox.delete();

        return {
            minX: xMin.current,
            minY: yMin.current,
            minZ: zMin.current,
            maxX: xMax.current,
            maxY: yMax.current,
            maxZ: zMax.current,
            sizeX: xMax.current - xMin.current,
            sizeY: yMax.current - yMin.current,
            sizeZ: zMax.current - zMin.current,
            centerX: (xMin.current + xMax.current) / 2,
            centerY: (yMin.current + yMax.current) / 2,
            centerZ: (zMin.current + zMax.current) / 2
        };
    } catch (e) {
        console.error('[_getBoundingBox] Error:', e);
        return null;
    }
};


/**
 * Get the OpenCascade instance
 * @private
 */
Workplane.prototype._getOC = function() {
    const oc = getOC();
    if (!oc) {
        throw new Error('OpenCascade not initialized');
    }
    return oc;
};


// ============================================================
// EXPORTS
// ============================================================

export { Gridfinity, bestGrid, bestCircleGrid };
