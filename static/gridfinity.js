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

// Absolute path for import map cache busting
import { Workplane, getOC } from '/static/cad.js';

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

    // Baseplate profile dimensions (inverse of bin base, slightly different)
    // See: https://github.com/ostat/gridfinity_extended_openscad
    BP_LOWER_TAPER: 0.7,     // bottom 45° step height
    BP_RISER: 1.8,           // vertical wall section
    BP_UPPER_TAPER: 2.15,    // top 45° step height
    BP_HEIGHT: 4.65,         // total baseplate rim height (0.7 + 1.8 + 2.15)
    BP_CORNER_RADIUS: 4.0,   // corner radius of baseplate pockets
    BP_FLOOR: 1.0,           // minimal floor thickness for thin baseplate

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
        const middleRadius = Math.max(outerRadius - this.STEP3_HEIGHT, 0.5);

        // Build the stepped base from 3 layers
        // box() creates with bottom at Z=0, so translate Z positions the bottom

        // Layer 1: Bottom step (0.8mm tall, chamfered from 35.6mm to 37.2mm)
        // Z = 0 to 0.8mm
        let layer1 = new Workplane("XY")
            .box(middleSize, middleSize, this.STEP1_HEIGHT)
            .translate(cellX, cellY, 0);
        layer1 = layer1.edges("|Z").fillet(middleRadius);
        layer1 = layer1.faces("<Z").edges().chamfer(this.STEP1_HEIGHT - 0.01);

        // Layer 2: Middle section (1.8mm tall, 37.2mm constant, vertical sides)
        // Z = 0.8 to 2.6mm
        let layer2 = new Workplane("XY")
            .box(middleSize, middleSize, this.STEP2_HEIGHT)
            .translate(cellX, cellY, this.STEP1_HEIGHT);
        layer2 = layer2.edges("|Z").fillet(middleRadius);

        // Layer 3: Top step (2.15mm tall, chamfered from 37.2mm to 41.5mm)
        // Z = 2.6 to 4.75mm
        let layer3 = new Workplane("XY")
            .box(cellSize, cellSize, this.STEP3_HEIGHT)
            .translate(cellX, cellY, this.STEP1_HEIGHT + this.STEP2_HEIGHT);
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
        // box() creates with bottom at Z=0, so translate Z positions the bottom
        const overlap = 0.5; // mm overlap with base for solid connection
        if (bodyHeight > 0) {
            const adjustedBodyHeight = bodyHeight + overlap;
            const bodyBottomZ = this.BASE_HEIGHT - overlap; // Start inside the base
            let body = new Workplane("XY")
                .box(outerX, outerY, adjustedBodyHeight)
                .translate(0, 0, bodyBottomZ); // Position bottom at bodyBottomZ
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

        // Set default gridfinity metadata for 3MF export
        // minCutZ tells cutRectGrid/cutCircleGrid where to stop cutting
        // (just above the base profile, leaving a thin floor)
        const floorThickness = 1.0; // mm floor above base
        result = result
            .meta('infillDensity', 5)
            .meta('infillPattern', 'gyroid')
            .meta('minCutZ', this.BASE_HEIGHT + floorThickness);

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
        let result = new Workplane("XY")
            .box(innerX, innerY, innerZ)
            .edges("|Z")
            .fillet(innerRadius);

        // Set default gridfinity metadata for 3MF export
        result = result
            .meta('infillDensity', 5)
            .meta('infillPattern', 'gyroid');

        return result;
    },

    /**
     * Create a gridfinity bin with multiple custom-sized cutouts
     * Automatically finds the smallest bin that fits all cuts
     *
     * @param {Object} options
     * @param {Array} options.cuts - Array of [width, height] or {width, height, fillet?}
     * @param {number} options.z - Height in gridfinity units (1 unit = 7mm)
     * @param {number} [options.spacing=1.5] - Minimum spacing between cuts and edges (mm)
     * @param {number} [options.fillet=3] - Default corner fillet radius (mm)
     * @returns {Workplane} - A Workplane with the bin and all cuts applied
     *
     * @example
     * // Fit three different compartments in the smallest possible bin
     * const bin = Gridfinity.fitBin({
     *     cuts: [[80, 40], [30, 20], [35, 20]],
     *     z: 3
     * });
     *
     * @example
     * // With custom fillets per cut
     * const bin = Gridfinity.fitBin({
     *     cuts: [
     *         { width: 80, height: 40, fillet: 5 },
     *         { width: 30, height: 20 },
     *         { width: 35, height: 20, fillet: 0 }
     *     ],
     *     z: 4,
     *     spacing: 2
     * });
     */
    fitBin(options) {
        const {
            cuts,
            z,
            spacing = 1.5,
            fillet: defaultFillet = 3
        } = options;

        if (!cuts || !Array.isArray(cuts) || cuts.length === 0) {
            console.error('[Gridfinity.fitBin] cuts array is required');
            return new Workplane("XY");
        }

        if (!z) {
            console.error('[Gridfinity.fitBin] z (height in units) is required');
            return new Workplane("XY");
        }

        // Normalize cuts to [{width, height, fillet}] format
        const normalizedCuts = cuts.map((cut, i) => {
            if (Array.isArray(cut)) {
                return { width: cut[0], height: cut[1], fillet: defaultFillet, id: i };
            }
            return { width: cut.width, height: cut.height, fillet: cut.fillet ?? defaultFillet, id: i };
        });

        console.log(`[Gridfinity.fitBin] Fitting ${normalizedCuts.length} cuts with ${spacing}mm spacing:`);
        normalizedCuts.forEach((c, i) => console.log(`  Cut ${i + 1}: ${c.width}x${c.height}mm`));

        // Find minimum bin size that fits all cuts
        const result = this._findMinBin(normalizedCuts, spacing, z);

        if (!result) {
            console.error('[Gridfinity.fitBin] Could not fit cuts in any reasonable bin size');
            return new Workplane("XY");
        }

        console.log(`[Gridfinity.fitBin] Best fit: ${result.x}x${result.y} bin`);
        console.log(`[Gridfinity.fitBin] Placements:`);
        result.placements.forEach((p, i) => {
            console.log(`  Cut ${i + 1}: (${p.x.toFixed(1)}, ${p.y.toFixed(1)}) ${p.width}x${p.height}mm`);
        });

        // Create the bin
        let bin = this.bin({ x: result.x, y: result.y, z });

        // Get bounding box for positioning cuts
        const bbox = bin._getBoundingBox();
        if (!bbox) {
            console.error('[Gridfinity.fitBin] Could not get bin bounding box');
            return bin;
        }

        // Apply each cut at its calculated position
        const minCutZ = bin._meta?.minCutZ ?? (this.BASE_HEIGHT + 1.0);
        const cutDepth = bbox.maxZ - minCutZ;

        for (const placement of result.placements) {
            // Position is relative to bin center
            const cx = placement.x + placement.width / 2;
            const cy = placement.y + placement.height / 2;

            // Create and apply the cutter
            const cutFloorZ = bbox.maxZ - cutDepth;
            let cutter = new Workplane("XY")
                .box(placement.width, placement.height, cutDepth + 1)
                .translate(cx, cy, cutFloorZ);

            if (placement.fillet > 0) {
                const actualFillet = Math.min(placement.fillet, Math.min(placement.width, placement.height) / 2 - 0.01);
                if (actualFillet > 0) {
                    cutter = cutter.edges("|Z").fillet(actualFillet);
                }
            }

            bin = bin.cut(cutter);
        }

        return bin;
    },

    /**
     * Find the minimum bin size that fits all cuts
     * @private
     */
    _findMinBin(cuts, spacing, z) {
        // Calculate usable inner dimensions for a given bin size
        const getUsable = (x, y) => {
            const outerX = x * this.UNIT_SIZE - 2 * this.BIN_CLEARANCE;
            const outerY = y * this.UNIT_SIZE - 2 * this.BIN_CLEARANCE;
            // Subtract spacing from edges (acts as border)
            return {
                width: outerX - 2 * spacing,
                height: outerY - 2 * spacing,
                // Offset from bin center to usable area corner
                offsetX: -outerX / 2 + spacing,
                offsetY: -outerY / 2 + spacing
            };
        };

        // Find max dimensions needed
        const maxWidth = Math.max(...cuts.map(c => Math.min(c.width, c.height)));
        const maxHeight = Math.max(...cuts.map(c => Math.max(c.width, c.height)));
        const totalArea = cuts.reduce((sum, c) => sum + (c.width + spacing) * (c.height + spacing), 0);

        // Generate bin sizes to try, sorted by area
        const maxUnits = 8; // Don't try bins larger than 8x8
        const binSizes = [];
        for (let x = 1; x <= maxUnits; x++) {
            for (let y = x; y <= maxUnits; y++) {  // y >= x to avoid duplicates
                binSizes.push({ x, y });
                if (x !== y) binSizes.push({ x: y, y: x });  // Add rotated version
            }
        }
        binSizes.sort((a, b) => (a.x * a.y) - (b.x * b.y));

        // Try each bin size
        for (const size of binSizes) {
            const usable = getUsable(size.x, size.y);

            // Quick check: does the largest cut fit?
            if (usable.width < maxWidth || usable.height < maxHeight) {
                continue;
            }

            // Quick check: is there enough total area?
            if (usable.width * usable.height < totalArea * 0.7) {  // Allow some inefficiency
                continue;
            }

            // Try to pack all cuts
            const placements = this._packRectangles(cuts, usable.width, usable.height, spacing);

            if (placements) {
                // Adjust positions from usable-area-relative to bin-center-relative
                const adjustedPlacements = placements.map(p => ({
                    ...p,
                    x: p.x + usable.offsetX,
                    y: p.y + usable.offsetY
                }));

                return {
                    x: size.x,
                    y: size.y,
                    placements: adjustedPlacements
                };
            }
        }

        return null;  // No fit found
    },

    /**
     * Pack rectangles into a given space using shelf algorithm with centering
     * @private
     * @returns {Array|null} - Array of placements or null if doesn't fit
     */
    _packRectangles(cuts, areaWidth, areaHeight, spacing) {
        // Sort cuts by height (tallest first) for better shelf packing
        const sortedCuts = [...cuts].sort((a, b) => {
            // Sort by max dimension descending
            const maxA = Math.max(a.width, a.height);
            const maxB = Math.max(b.width, b.height);
            return maxB - maxA;
        });

        // Initial shelf packing (bottom-left)
        const placements = [];
        const shelves = [];  // {y, height, items: [{x, width, ...}]}

        for (const cut of sortedCuts) {
            let placed = false;

            // Try to place in existing shelf
            for (const shelf of shelves) {
                const totalWidth = shelf.items.reduce((sum, item) => sum + item.width, 0);
                const usedWidth = totalWidth + (shelf.items.length) * spacing;

                // Try original orientation
                if (usedWidth + cut.width <= areaWidth && cut.height <= shelf.height) {
                    shelf.items.push({
                        width: cut.width,
                        height: cut.height,
                        fillet: cut.fillet,
                        id: cut.id
                    });
                    placed = true;
                    break;
                }
                // Try rotated
                if (usedWidth + cut.height <= areaWidth && cut.width <= shelf.height) {
                    shelf.items.push({
                        width: cut.height,  // swapped
                        height: cut.width,  // swapped
                        fillet: cut.fillet,
                        id: cut.id
                    });
                    placed = true;
                    break;
                }
            }

            if (!placed) {
                // Calculate where new shelf would start
                const totalShelfHeight = shelves.reduce((sum, s) => sum + s.height, 0);
                const shelfY = totalShelfHeight + shelves.length * spacing;

                // Try original orientation
                if (cut.width <= areaWidth && shelfY + cut.height <= areaHeight) {
                    shelves.push({
                        height: cut.height,
                        items: [{
                            width: cut.width,
                            height: cut.height,
                            fillet: cut.fillet,
                            id: cut.id
                        }]
                    });
                    placed = true;
                }
                // Try rotated
                else if (cut.height <= areaWidth && shelfY + cut.width <= areaHeight) {
                    shelves.push({
                        height: cut.width,  // swapped
                        items: [{
                            width: cut.height,  // swapped
                            height: cut.width,  // swapped
                            fillet: cut.fillet,
                            id: cut.id
                        }]
                    });
                    placed = true;
                }
            }

            if (!placed) {
                return null;  // Doesn't fit
            }
        }

        // Now center everything with equal spacing
        // Calculate total height used by shelves
        const totalShelvesHeight = shelves.reduce((sum, s) => sum + s.height, 0);
        const verticalGaps = shelves.length + 1;  // gaps above, between, and below
        const verticalSpacing = (areaHeight - totalShelvesHeight) / verticalGaps;

        console.log(`[_packRectangles] Centering: area ${areaWidth.toFixed(1)}x${areaHeight.toFixed(1)}, ${shelves.length} shelves`);
        console.log(`[_packRectangles] Vertical: totalHeight=${totalShelvesHeight.toFixed(1)}, spacing=${verticalSpacing.toFixed(1)}`);

        let shelfY = verticalSpacing;

        for (let shelfIdx = 0; shelfIdx < shelves.length; shelfIdx++) {
            const shelf = shelves[shelfIdx];
            // Calculate horizontal spacing for this shelf independently
            const totalItemsWidth = shelf.items.reduce((sum, item) => sum + item.width, 0);
            const horizontalGaps = shelf.items.length + 1;
            const horizontalSpacing = (areaWidth - totalItemsWidth) / horizontalGaps;

            console.log(`[_packRectangles] Shelf ${shelfIdx}: ${shelf.items.length} items, totalWidth=${totalItemsWidth.toFixed(1)}, hSpacing=${horizontalSpacing.toFixed(1)}`);

            let currentX = horizontalSpacing;

            for (const item of shelf.items) {
                // Center each item vertically within the shelf (not just aligned to bottom)
                const itemVerticalOffset = (shelf.height - item.height) / 2;
                const itemY = shelfY + itemVerticalOffset;

                const centerX = currentX + item.width / 2;
                const centerY = itemY + item.height / 2;
                console.log(`[_packRectangles]   Item ${item.width}x${item.height}: x=${currentX.toFixed(1)}, y=${itemY.toFixed(1)}, center=(${centerX.toFixed(1)}, ${centerY.toFixed(1)})`);
                placements.push({
                    x: currentX,
                    y: itemY,
                    width: item.width,
                    height: item.height,
                    fillet: item.fillet,
                    id: item.id
                });
                currentX += item.width + horizontalSpacing;
            }

            shelfY += shelf.height + verticalSpacing;
        }

        return placements;
    },

    /**
     * Create a single baseplate pocket cutter with stepped profile (internal helper)
     * This is the inverse of the bin base profile - creates the pocket shape
     * @private
     */
    _createPocketCutter(cellX, cellY, floorZ) {
        // Pocket dimensions at each level
        // At top (opening): full 42mm grid cell
        // Tapers in as we go down to floor
        const topSize = this.UNIT_SIZE;  // 42mm at opening
        const midSize = topSize - 2 * this.BP_UPPER_TAPER;  // 37.7mm after upper taper
        const bottomSize = midSize - 2 * this.BP_LOWER_TAPER;  // 36.3mm at floor

        // Corner radii (proportional to size)
        const topRadius = this.BP_CORNER_RADIUS;  // 4.0mm
        const midRadius = Math.max(topRadius - this.BP_UPPER_TAPER, 0.5);  // ~1.85mm
        const bottomRadius = Math.max(midRadius - this.BP_LOWER_TAPER, 0.3);  // ~1.15mm

        // Layer 1: Bottom step (at floor, chamfered upward)
        // Z = floorZ to floorZ + 0.7
        let layer1 = new Workplane("XY")
            .box(midSize, midSize, this.BP_LOWER_TAPER)
            .translate(cellX, cellY, floorZ);
        layer1 = layer1.edges("|Z").fillet(midRadius);
        layer1 = layer1.faces("<Z").edges().chamfer(this.BP_LOWER_TAPER - 0.01);

        // Layer 2: Middle section (vertical walls)
        // Z = floorZ + 0.7 to floorZ + 2.5
        let layer2 = new Workplane("XY")
            .box(midSize, midSize, this.BP_RISER)
            .translate(cellX, cellY, floorZ + this.BP_LOWER_TAPER);
        layer2 = layer2.edges("|Z").fillet(midRadius);

        // Layer 3: Top step (chamfered from mid to top)
        // Z = floorZ + 2.5 to floorZ + 4.65
        let layer3 = new Workplane("XY")
            .box(topSize, topSize, this.BP_UPPER_TAPER)
            .translate(cellX, cellY, floorZ + this.BP_LOWER_TAPER + this.BP_RISER);
        layer3 = layer3.edges("|Z").fillet(topRadius);
        layer3 = layer3.faces("<Z").edges().chamfer(this.BP_UPPER_TAPER - 0.01);

        // Union all layers to create pocket cutter
        return layer1.union(layer2).union(layer3);
    },

    /**
     * Create a minimal gridfinity baseplate
     *
     * Creates the thinnest possible baseplate with no magnets - just the
     * stepped grid walls that bins clip into. No solid floor - just an
     * open frame/grid structure.
     *
     * @param {Object} options
     * @param {number} options.x - X dimension in grid units (1 unit = 42mm)
     * @param {number} options.y - Y dimension in grid units
     * @param {boolean} [options.fillet=true] - Round outer corners (reduces curling)
     * @param {boolean} [options.chamfer=true] - Chamfer bottom edge (better bed adhesion)
     * @returns {Workplane} - A Workplane object with the baseplate
     *
     * @example
     * // Create a 3x2 baseplate
     * const plate = Gridfinity.baseplate({ x: 3, y: 2 });
     *
     * @example
     * // Without chamfer (for mounting on a surface)
     * const plate = Gridfinity.baseplate({ x: 3, y: 2, chamfer: false });
     */
    baseplate(options) {
        const {
            x,
            y,
            fillet = true,
            chamfer = true
        } = options;

        if (!x || !y) {
            console.error('[Gridfinity] baseplate requires x, y dimensions');
            return new Workplane("XY");
        }

        const totalHeight = this.BP_HEIGHT;  // 4.65mm - just the rim height
        const outerX = x * this.UNIT_SIZE;
        const outerY = y * this.UNIT_SIZE;

        console.log(`[Gridfinity] Creating ${x}x${y} baseplate (open grid):`);
        console.log(`  Outer dimensions: ${outerX} x ${outerY} x ${totalHeight.toFixed(2)} mm`);

        // Create solid base block at rim height
        // Apply corner treatments BEFORE cutting pockets (while it's a simple box)
        let result = new Workplane("XY")
            .box(outerX, outerY, totalHeight);

        if (fillet) {
            result = result.edges("|Z").fillet(4);      // Round outer vertical corners (reduces curling)
        }
        if (chamfer) {
            result = result.faces("<Z").edges().chamfer(0.5);  // Chamfer bottom edge (better bed adhesion)
        }

        // Cut completely through for each grid cell (no floor)
        const startX = -(x - 1) * this.UNIT_SIZE / 2;
        const startY = -(y - 1) * this.UNIT_SIZE / 2;

        for (let gy = 0; gy < y; gy++) {
            for (let gx = 0; gx < x; gx++) {
                const cellX = startX + gx * this.UNIT_SIZE;
                const cellY = startY + gy * this.UNIT_SIZE;

                // Create through-cutter starting at Z=0 (cuts all the way through)
                const throughCutter = this._createPocketCutter(cellX, cellY, 0);

                result = result.cut(throughCutter);
            }
        }

        // Set metadata
        result = result
            .meta('infillDensity', 10)
            .meta('infillPattern', 'grid');

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
    // Use minCutZ metadata if available (e.g., Gridfinity bins set this to preserve base)
    const minCutZ = this._meta?.minCutZ;
    let cutDepth;
    if (depth !== null) {
        cutDepth = depth;
        const maxDepth = minCutZ !== undefined ? (bbox.maxZ - minCutZ) : (bbox.sizeZ - minBorder);
        if (cutDepth > maxDepth) {
            console.warn(`[cutRectGrid] Depth ${cutDepth}mm exceeds max ${maxDepth.toFixed(2)}mm`);
            cutDepth = maxDepth;
        }
    } else if (minCutZ !== undefined) {
        // Use minCutZ to determine depth (cut from top down to minCutZ)
        cutDepth = bbox.maxZ - minCutZ;
    } else {
        cutDepth = bbox.sizeZ - minBorder;
    }

    if (cutDepth <= 0) {
        console.error('[cutRectGrid] Computed depth <= 0 - part too shallow');
        return this;
    }

    console.log(`[cutRectGrid] Part: ${bbox.sizeX.toFixed(1)}x${bbox.sizeY.toFixed(1)}x${bbox.sizeZ.toFixed(1)} mm`);
    console.log(`[cutRectGrid] Usable area: ${partX.toFixed(1)}x${partY.toFixed(1)} mm`);
    console.log(`[cutRectGrid] minCutZ: ${minCutZ !== undefined ? minCutZ.toFixed(2) : 'not set'}, bbox.maxZ: ${bbox.maxZ.toFixed(2)}`);
    console.log(`[cutRectGrid] Cut depth: ${cutDepth.toFixed(2)} mm (cuts from Z=${bbox.maxZ.toFixed(2)} to Z=${(bbox.maxZ - cutDepth).toFixed(2)})`);

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
            // box() places bottom at Z=0, so translate to position bottom at cut floor
            const cutFloorZ = bbox.maxZ - cutDepth;
            let cutter = new Workplane("XY")
                .box(width, height, cutDepth + 1) // +1 to ensure clean cut through top
                .translate(cx, cy, cutFloorZ);

            console.log(`[cutRectGrid] Cutter at (${cx.toFixed(1)}, ${cy.toFixed(1)}), bottom Z=${cutFloorZ.toFixed(2)}, top Z=${(cutFloorZ + cutDepth + 1).toFixed(2)}`);

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
    // Use minCutZ metadata if available (e.g., Gridfinity bins set this to preserve base)
    const minCutZ = this._meta?.minCutZ;
    let cutDepth;
    if (depth !== null) {
        cutDepth = depth;
        const maxDepth = minCutZ !== undefined ? (bbox.maxZ - minCutZ) : (bbox.sizeZ - minBorder);
        if (cutDepth > maxDepth) {
            console.warn(`[cutCircleGrid] Depth ${cutDepth}mm exceeds max ${maxDepth.toFixed(2)}mm`);
            cutDepth = maxDepth;
        }
    } else if (minCutZ !== undefined) {
        // Use minCutZ to determine depth (cut from top down to minCutZ)
        cutDepth = bbox.maxZ - minCutZ;
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
            // cylinder() places bottom at Z=0, so translate to position bottom at cut floor
            const cutFloorZ = bbox.maxZ - cutDepth;
            const cutter = new Workplane("XY")
                .cylinder(radius, cutDepth + 1)
                .translate(cx, cy, cutFloorZ);

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


/**
 * Get bounding box of a single face
 * @private
 */
Workplane.prototype._getFaceBoundingBox = function(face) {
    const oc = this._getOC();
    try {
        const bbox = new oc.Bnd_Box_1();
        oc.BRepBndLib.Add(face, bbox, false);

        const xMin = { current: 0 }, yMin = { current: 0 }, zMin = { current: 0 };
        const xMax = { current: 0 }, yMax = { current: 0 }, zMax = { current: 0 };
        bbox.Get(xMin, yMin, zMin, xMax, yMax, zMax);
        bbox.delete();

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
        console.error('[_getFaceBoundingBox] Error:', e);
        return null;
    }
};


/**
 * Add a gridfinity baseplate onto a selected face (or top of shape if no face selected)
 *
 * Use .faces(">Z") or similar to select a face first, then call .addBaseplate().
 * The baseplate will be sized to fit the selected face and positioned on it.
 *
 * @param {Object} [options]
 * @param {boolean} [options.fillet=true] - Round outer corners of baseplate
 * @returns {Workplane} - New Workplane with baseplate attached
 *
 * @example
 * // Add baseplate to the top face of a box
 * const boxWithPlate = new Workplane("XY")
 *     .box(150, 100, 10)
 *     .faces(">Z")
 *     .addBaseplate();
 *
 * @example
 * // Without rounded corners
 * const sharpPlate = myShape.faces(">Z").addBaseplate({ fillet: false });
 */
Workplane.prototype.addBaseplate = function(options = {}) {
    const { fillet = true } = options;

    if (!this._shape) {
        console.error('[addBaseplate] No shape to add baseplate to');
        return this;
    }

    let availableX, availableY, posX, posY, posZ;

    // Check if a face is selected
    if (this._selectedFaces && this._selectedFaces.length > 0) {
        // Use the first selected face
        const face = this._selectedFaces[0];
        const faceBbox = this._getFaceBoundingBox(face);

        if (!faceBbox) {
            console.error('[addBaseplate] Could not get face bounding box');
            return this;
        }

        availableX = faceBbox.sizeX;
        availableY = faceBbox.sizeY;
        posX = faceBbox.centerX;
        posY = faceBbox.centerY;
        posZ = faceBbox.maxZ;  // Top of the face

        console.log(`[addBaseplate] Using selected face at Z=${posZ.toFixed(1)}`);
    } else {
        // Fall back to shape bounding box (top face)
        const bbox = this._getBoundingBox();
        if (!bbox) {
            console.error('[addBaseplate] Could not get bounding box');
            return this;
        }

        availableX = bbox.sizeX;
        availableY = bbox.sizeY;
        posX = bbox.centerX;
        posY = bbox.centerY;
        posZ = bbox.maxZ;

        console.log('[addBaseplate] No face selected, using top of bounding box');
    }

    // Calculate how many grid cells fit
    const gridX = Math.floor(availableX / Gridfinity.UNIT_SIZE);
    const gridY = Math.floor(availableY / Gridfinity.UNIT_SIZE);

    if (gridX < 1 || gridY < 1) {
        console.error(`[addBaseplate] Face too small for baseplate. Need at least ${Gridfinity.UNIT_SIZE}x${Gridfinity.UNIT_SIZE}mm, have ${availableX.toFixed(1)}x${availableY.toFixed(1)}mm`);
        return this;
    }

    console.log(`[addBaseplate] Available area: ${availableX.toFixed(1)}x${availableY.toFixed(1)}mm`);
    console.log(`[addBaseplate] Fitting ${gridX}x${gridY} baseplate (${gridX * Gridfinity.UNIT_SIZE}x${gridY * Gridfinity.UNIT_SIZE}mm)`);

    // Create the baseplate (no chamfer since we're on a surface, not the build plate)
    const baseplate = Gridfinity.baseplate({ x: gridX, y: gridY, fillet, chamfer: false });

    // Translate baseplate to position on the face
    const positioned = baseplate.translate(posX, posY, posZ);

    // Union with current shape
    return this.union(positioned);
};


/**
 * Cut horizontal line grooves into a selected face (DEPRECATED)
 *
 * @deprecated Use cutPattern({ shape: 'line', ... }) instead. This method is kept for backward compatibility.
 * @param {Object} [options]
 * @param {number} [options.width=1.0] - Width of each groove in mm
 * @param {number} [options.depth=0.4] - Depth of grooves in mm
 * @param {number} [options.spacing=2.0] - Distance between groove centers in mm
 * @param {number} [options.border=2.0] - Margin from face edges in mm
 * @returns {Workplane} - New Workplane with grooves cut
 */
Workplane.prototype.cutLines = function(options = {}) {
    // Delegate to the new unified cutPattern() API
    console.log('[cutLines] DEPRECATED: Use cutPattern({ shape: "line", ... }) instead');
    return this.cutPattern({
        shape: 'line',
        width: options.width ?? 1.0,
        depth: options.depth ?? 0.4,
        spacing: options.spacing ?? 2.0,
        border: options.border ?? 2.0,
        direction: 'x'
    });
};


// ============================================================
// EXPORTS
// ============================================================

export { Gridfinity, bestGrid, bestCircleGrid };
