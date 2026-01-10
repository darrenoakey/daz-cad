/**
 * CAD.js - A CadQuery-like JavaScript wrapper for OpenCascade.js
 *
 * Provides a fluent API for creating 3D CAD models.
 *
 * Example:
 *   const shape = new Workplane("XY")
 *     .box(10, 20, 30)
 *     .faces(">Z")
 *     .hole(5)
 *     .edges()
 *     .chamfer(1);
 */

// Import opentype.js for font parsing
import * as opentype from './opentype.module.js';

// Import JSZip for 3MF export (using jsDelivr ESM conversion)
import JSZip from 'https://cdn.jsdelivr.net/npm/jszip@3.10.1/+esm';

// Ensure OpenCascade is loaded
let oc = null;

// Error tracking for the current operation
let lastError = null;

/**
 * Profiler - Simple timing profiler for CAD operations
 * Create an instance, call checkpoint() at each step, then finished() to log results
 */
class Profiler {
    constructor(name = 'Profile') {
        this._name = name;
        this._startTime = performance.now();
        this._checkpoints = [];
        this._lastTime = this._startTime;
    }

    /**
     * Record a checkpoint with a label
     */
    checkpoint(label) {
        const now = performance.now();
        this._checkpoints.push({
            label,
            time: now,
            sinceStart: now - this._startTime,
            sinceLast: now - this._lastTime
        });
        this._lastTime = now;
        return this;
    }

    /**
     * Finish profiling and log the results table
     */
    finished() {
        this.checkpoint('end');

        // Format number with commas
        const fmt = (n) => Math.round(n).toLocaleString();

        // Find max label length for alignment
        const maxLabelLen = Math.max(...this._checkpoints.map(c => c.label.length), 10);
        const colWidth = 12;

        // Build header
        const header = [
            'Step'.padEnd(maxLabelLen),
            'Since Start'.padStart(colWidth),
            'Delta'.padStart(colWidth)
        ].join(' │ ');

        const separator = [
            '─'.repeat(maxLabelLen),
            '─'.repeat(colWidth),
            '─'.repeat(colWidth)
        ].join('─┼─');

        // Build rows
        const rows = this._checkpoints.map(c => [
            c.label.padEnd(maxLabelLen),
            (fmt(c.sinceStart) + ' ms').padStart(colWidth),
            (fmt(c.sinceLast) + ' ms').padStart(colWidth)
        ].join(' │ '));

        // Log the table
        console.log(`\n┌${'─'.repeat(header.length + 2)}┐`);
        console.log(`│ ${this._name.padEnd(header.length)} │`);
        console.log(`├${'─'.repeat(header.length + 2)}┤`);
        console.log(`│ ${header} │`);
        console.log(`│ ${separator} │`);
        for (const row of rows) {
            console.log(`│ ${row} │`);
        }
        console.log(`└${'─'.repeat(header.length + 2)}┘\n`);

        return this;
    }

    /**
     * Get total elapsed time in ms
     */
    elapsed() {
        return performance.now() - this._startTime;
    }
}

/**
 * Log and track CAD errors
 */
function cadError(operation, message, originalError = null) {
    const errorInfo = {
        operation,
        message,
        originalError: originalError?.message || originalError,
        timestamp: new Date().toISOString()
    };
    lastError = errorInfo;
    console.error(`[CAD Error] ${operation}: ${message}`, originalError || '');
    return errorInfo;
}

/**
 * Get the last CAD error (useful for debugging)
 */
function getLastError() {
    return lastError;
}

/**
 * Clear the last CAD error
 */
function clearLastError() {
    lastError = null;
}

// Font cache for text rendering using opentype.js
let loadedFonts = new Map(); // fontPath -> opentype.Font object
let defaultFontPath = null;

/**
 * Load a font file and parse it with opentype.js
 * @param {string} url - URL to fetch the font from
 * @param {string} [fontName] - Name to cache the font under (defaults to filename)
 * @returns {Promise<string>} - The font name/path
 */
async function loadFont(url, fontName = null) {
    // Generate font name if not provided
    if (!fontName) {
        fontName = url.split('/').pop() || 'font.ttf';
    }

    // Check if already loaded
    if (loadedFonts.has(fontName)) {
        return fontName;
    }

    // Fetch the font file
    const response = await fetch(url);
    if (!response.ok) {
        throw new Error(`Failed to fetch font from ${url}: ${response.status}`);
    }
    const fontData = await response.arrayBuffer();

    // Parse with opentype.js (imported as ES module)
    const font = opentype.parse(fontData);
    if (!font) {
        throw new Error(`Failed to parse font from ${url}`);
    }

    loadedFonts.set(fontName, font);
    console.log(`[CAD] Loaded font: ${fontName}`);

    // Set as default if this is the first font loaded
    if (!defaultFontPath) {
        defaultFontPath = fontName;
    }

    return fontName;
}

/**
 * Get a loaded font by name
 * @param {string} fontName - The font name/path
 * @returns {object|null} - The opentype.Font object or null
 */
function getFont(fontName) {
    return loadedFonts.get(fontName) || null;
}

/**
 * Get the default font, loading Overpass Bold if needed
 */
async function getDefaultFont() {
    if (defaultFontPath && loadedFonts.has(defaultFontPath)) {
        return defaultFontPath;
    }

    // Load Overpass Bold as default (good for CAD text - clear and readable)
    return await loadFont('/static/fonts/Overpass-Bold.ttf', '/fonts/Overpass-Bold.ttf');
}

/**
 * Initialize the CAD library with an OpenCascade instance
 * Works in both main thread (sets window globals) and web worker (just sets oc)
 */
function initCAD(openCascadeInstance) {
    oc = openCascadeInstance;
    // Only set window globals if we're in a browser main thread
    if (typeof window !== 'undefined') {
        window.Workplane = Workplane;
        window.Assembly = Assembly;
        window.Profiler = Profiler;
        window.loadFont = loadFont;
        window.CAD = { oc, Workplane, Assembly, Profiler, loadFont, getLastError, clearLastError };
    }
}

/**
 * Helper class for generating Bambu-compatible 3MF files
 */
class ThreeMFExporter {
    /**
     * Generate 3MF file from parts array using Bambu template
     * @param {Array} parts - Array of {mesh, color, name, modifiers} objects
     * @returns {Promise<Blob>} - The 3MF file as a Blob
     */
    static async generate(parts) {
        // Load the Bambu template
        const response = await fetch('/static/template.3mf');
        const templateData = await response.arrayBuffer();
        const zip = await JSZip.loadAsync(templateData);

        // Build the object structure
        // Group parts with their modifiers into objects
        const objects = this._buildObjects(parts);

        // Generate all the 3MF components
        const modelData = this._model(objects);
        const objectsModelData = this._objectsModel(objects);

        // Use DEFLATE compression for significantly smaller files
        const compressionOpts = { compression: 'DEFLATE', compressionOptions: { level: 6 } };

        zip.file('3D/3dmodel.model', modelData, compressionOpts);
        zip.file('3D/Objects/objects.model', objectsModelData, compressionOpts);
        zip.file('3D/_rels/3dmodel.model.rels', this._modelRels(), compressionOpts);
        zip.file('Metadata/model_settings.config', this._modelSettings(objects), compressionOpts);
        zip.file('Metadata/slice_info.config', this._sliceInfo(objects), compressionOpts);

        // Update filament colors and infill settings in project_settings.config
        const projectSettingsStr = await zip.file('Metadata/project_settings.config').async('string');
        const projectSettings = JSON.parse(projectSettingsStr);

        // Collect all unique colors from parts and modifiers
        const allColors = [];
        for (const obj of objects) {
            for (const vol of obj.volumes) {
                allColors.push(vol.color || '#808080');
            }
        }

        // Set filament colors
        for (let i = 0; i < allColors.length && i < (projectSettings.filament_colour?.length || 0); i++) {
            const color = allColors[i];
            const hexColor = color.startsWith('#') ? color.toUpperCase() : `#${color.toUpperCase()}`;
            projectSettings.filament_colour[i] = hexColor;
        }

        // Set infill settings from first object's metadata (as project defaults)
        // Also track which settings differ from system defaults
        const differentSettings = [];
        if (objects.length > 0 && objects[0].volumes[0]?.meta) {
            const meta = objects[0].volumes[0].meta;
            if (meta.infillDensity !== undefined) {
                projectSettings.sparse_infill_density = `${meta.infillDensity}%`;
                differentSettings.push('sparse_infill_density');
                console.log(`[3MF] Setting infill density to ${meta.infillDensity}%`);
            }
            if (meta.infillPattern !== undefined) {
                projectSettings.sparse_infill_pattern = meta.infillPattern;
                differentSettings.push('sparse_infill_pattern');
                console.log(`[3MF] Setting infill pattern to ${meta.infillPattern}`);
            }
        }

        // Add different_settings_to_system if we have overrides
        // This tells BambuStudio which settings are intentionally different from defaults
        if (differentSettings.length > 0) {
            // Array entries correspond to: [print, printer, filament1, filament2, ...]
            const settingsStr = differentSettings.join(';');
            projectSettings.different_settings_to_system = [
                settingsStr, // print settings
                '',          // printer settings
                '',          // filament 1
                '',          // filament 2
                '',          // filament 3
                '',          // filament 4
                '',          // filament 5
                ''           // filament 6
            ];
        }

        zip.file('Metadata/project_settings.config', JSON.stringify(projectSettings, null, 4), compressionOpts);

        return await zip.generateAsync({ type: 'blob' });
    }

    /**
     * Build object structure from parts array
     * Groups main parts with their modifiers
     */
    static _buildObjects(parts) {
        const objects = [];

        for (let i = 0; i < parts.length; i++) {
            const part = parts[i];
            const volumes = [];

            // Main part
            volumes.push({
                mesh: this._weldMesh(part.mesh),
                subtype: 'normal_part',
                color: part.color || '#808080',
                name: part.name || `Part_${i + 1}`,
                meta: part.meta || {}
            });

            // Modifiers attached to this part
            if (part.modifiers && part.modifiers.length > 0) {
                for (let m = 0; m < part.modifiers.length; m++) {
                    const mod = part.modifiers[m];
                    volumes.push({
                        mesh: this._weldMesh(mod.mesh),
                        subtype: 'modifier_part',
                        color: mod.color || '#FFFFFF',
                        name: mod.name || `Modifier_${m + 1}`,
                        meta: mod.meta || {}
                    });
                }
            }

            objects.push({
                name: part.name || `Object_${i + 1}`,
                volumes,
                meta: part.meta || {}
            });
        }

        return objects;
    }

    // Weld vertices to create manifold mesh (merge duplicate vertices)
    static _weldMesh(mesh, tolerance = 1e-5) {
        const vertices = mesh.vertices;
        const indices = mesh.indices;

        const vertexMap = new Map();
        const uniqueVertices = [];
        const indexRemap = [];

        const roundCoord = (v) => Math.round(v / tolerance) * tolerance;
        const makeKey = (x, y, z) => `${roundCoord(x)},${roundCoord(y)},${roundCoord(z)}`;

        for (let i = 0; i < vertices.length; i += 3) {
            const x = vertices[i];
            const y = vertices[i + 1];
            const z = vertices[i + 2];
            const key = makeKey(x, y, z);
            const oldIndex = i / 3;

            if (vertexMap.has(key)) {
                indexRemap[oldIndex] = vertexMap.get(key);
            } else {
                const newIndex = uniqueVertices.length / 3;
                vertexMap.set(key, newIndex);
                indexRemap[oldIndex] = newIndex;
                uniqueVertices.push(x, y, z);
            }
        }

        const newIndices = [];
        for (let i = 0; i < indices.length; i++) {
            newIndices.push(indexRemap[indices[i]]);
        }

        return {
            vertices: new Float32Array(uniqueVertices),
            indices: new Uint32Array(newIndices),
            color: mesh.color
        };
    }

    /**
     * Generate main 3dmodel.model with component references
     * Objects with modifiers use components pointing to separate object file
     */
    static _model(objects) {
        const now = new Date();
        const dateStr = now.toISOString().split('T')[0];

        // Calculate global bounding box for positioning
        let globalMinX = Infinity, globalMinY = Infinity, globalMinZ = Infinity;
        let globalMaxX = -Infinity, globalMaxY = -Infinity, globalMaxZ = -Infinity;

        for (const obj of objects) {
            for (const vol of obj.volumes) {
                for (let v = 0; v < vol.mesh.vertices.length; v += 3) {
                    globalMinX = Math.min(globalMinX, vol.mesh.vertices[v]);
                    globalMinY = Math.min(globalMinY, vol.mesh.vertices[v + 1]);
                    globalMinZ = Math.min(globalMinZ, vol.mesh.vertices[v + 2]);
                    globalMaxX = Math.max(globalMaxX, vol.mesh.vertices[v]);
                    globalMaxY = Math.max(globalMaxY, vol.mesh.vertices[v + 1]);
                    globalMaxZ = Math.max(globalMaxZ, vol.mesh.vertices[v + 2]);
                }
            }
        }

        const plateCenter = 128;
        const offsetX = plateCenter - (globalMinX + globalMaxX) / 2;
        const offsetY = plateCenter - (globalMinY + globalMaxY) / 2;
        const offsetZ = -globalMinZ;

        // Build resources - parent objects with components
        let resources = '';
        let buildItems = '';
        let volumeId = 1;

        for (let objIdx = 0; objIdx < objects.length; objIdx++) {
            const obj = objects[objIdx];
            const parentId = objIdx + 1000; // Parent object IDs start at 1000

            // Build component references for each volume
            let components = '';
            for (let volIdx = 0; volIdx < obj.volumes.length; volIdx++) {
                const vol = obj.volumes[volIdx];
                // Store volume ID for model_settings.config
                vol.volumeId = volumeId;
                components += `    <component p:path="/3D/Objects/objects.model" objectid="${volumeId}" transform="1 0 0 0 1 0 0 0 1 0 0 0"/>\n`;
                volumeId++;
            }

            resources += `  <object id="${parentId}" type="model">
   <components>
${components}   </components>
  </object>\n`;

            // Build item with transform
            const transform = `1 0 0 0 1 0 0 0 1 ${offsetX.toFixed(6)} ${offsetY.toFixed(6)} ${offsetZ.toFixed(6)}`;
            buildItems += `  <item objectid="${parentId}" transform="${transform}" printable="1"/>\n`;
        }

        return `<?xml version="1.0" encoding="UTF-8"?>
<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" requiredextensions="p">
 <metadata name="Application">BambuStudio-02.04.00.70</metadata>
 <metadata name="BambuStudio:3mfVersion">1</metadata>
 <metadata name="Copyright"></metadata>
 <metadata name="CreationDate">${dateStr}</metadata>
 <metadata name="Description"></metadata>
 <metadata name="Designer"></metadata>
 <metadata name="DesignerCover"></metadata>
 <metadata name="DesignerUserId"></metadata>
 <metadata name="License"></metadata>
 <metadata name="ModificationDate">${dateStr}</metadata>
 <metadata name="Origin"></metadata>
 <metadata name="ProfileCover"></metadata>
 <metadata name="ProfileDescription"></metadata>
 <metadata name="ProfileTitle"></metadata>
 <metadata name="Title"></metadata>
 <resources>
${resources} </resources>
 <build>
${buildItems} </build>
</model>`;
    }

    /**
     * Generate 3D/Objects/objects.model with actual mesh data
     */
    static _objectsModel(objects) {
        let resources = '';
        let volumeId = 1;

        for (const obj of objects) {
            for (const vol of obj.volumes) {
                const mesh = vol.mesh;

                let verticesXml = '';
                for (let v = 0; v < mesh.vertices.length; v += 3) {
                    verticesXml += `     <vertex x="${mesh.vertices[v].toFixed(6)}" y="${mesh.vertices[v + 1].toFixed(6)}" z="${mesh.vertices[v + 2].toFixed(6)}"/>\n`;
                }

                let trianglesXml = '';
                for (let t = 0; t < mesh.indices.length; t += 3) {
                    trianglesXml += `     <triangle v1="${mesh.indices[t]}" v2="${mesh.indices[t + 1]}" v3="${mesh.indices[t + 2]}"/>\n`;
                }

                resources += `  <object id="${volumeId}" type="model">
   <mesh>
    <vertices>
${verticesXml}    </vertices>
    <triangles>
${trianglesXml}    </triangles>
   </mesh>
  </object>\n`;
                volumeId++;
            }
        }

        return `<?xml version="1.0" encoding="UTF-8"?>
<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" requiredextensions="p">
 <metadata name="BambuStudio:3mfVersion">1</metadata>
 <resources>
${resources} </resources>
</model>`;
    }

    /**
     * Generate relationship file for 3D/_rels/3dmodel.model.rels
     */
    static _modelRels() {
        return `<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 <Relationship Target="/3D/Objects/objects.model" Id="rel-1" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>
</Relationships>`;
    }

    /**
     * Generate model_settings.config with part types
     */
    static _modelSettings(objects) {
        let objectsXml = '';
        let extruder = 1;

        for (let objIdx = 0; objIdx < objects.length; objIdx++) {
            const obj = objects[objIdx];
            const parentId = objIdx + 1000;

            let partsXml = '';
            for (let volIdx = 0; volIdx < obj.volumes.length; volIdx++) {
                const vol = obj.volumes[volIdx];

                // Build custom metadata from vol.meta
                let customMeta = '';
                if (vol.meta) {
                    if (vol.meta.infillDensity !== undefined) {
                        customMeta += `      <metadata key="sparse_infill_density" value="${vol.meta.infillDensity}%"/>\n`;
                    }
                    if (vol.meta.infillPattern !== undefined) {
                        customMeta += `      <metadata key="sparse_infill_pattern" value="${vol.meta.infillPattern}"/>\n`;
                    }
                }

                partsXml += `    <part id="${vol.volumeId}" subtype="${vol.subtype}">
      <metadata key="name" value="${vol.name}"/>
      <metadata key="matrix" value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>
      <metadata key="source_file" value=""/>
      <metadata key="source_object_id" value="0"/>
      <metadata key="source_volume_id" value="0"/>
      <metadata key="source_offset_x" value="0"/>
      <metadata key="source_offset_y" value="0"/>
      <metadata key="source_offset_z" value="0"/>
      <metadata key="extruder" value="${extruder}"/>
${customMeta}    </part>\n`;
                extruder++;
            }

            objectsXml += `  <object id="${parentId}">
    <metadata key="name" value="${obj.name}"/>
    <metadata key="extruder" value="1"/>
${partsXml}  </object>\n`;
        }

        return `<?xml version="1.0" encoding="UTF-8"?>
<config>
  <plate>
    <metadata key="plater_id" value="1"/>
    <metadata key="plater_name" value=""/>
    <metadata key="locked" value="false"/>
  </plate>
${objectsXml}  <assemble>
  </assemble>
</config>`;
    }

    /**
     * Generate slice_info.config with filament colors
     */
    static _sliceInfo(objects) {
        let filaments = '';
        let filamentId = 1;

        for (const obj of objects) {
            for (const vol of obj.volumes) {
                const color = vol.color || '#808080';
                const hexColor = color.startsWith('#') ? color.toUpperCase() : `#${color.toUpperCase()}`;
                filaments += `  <filament id="${filamentId}">
   <metadata key="type" value="PLA"/>
   <metadata key="color" value="${hexColor}"/>
  </filament>\n`;
                filamentId++;
            }
        }

        return `<?xml version="1.0" encoding="UTF-8"?>
<config>
  <header>
    <header_item key="X-BBL-Client-Type" value="slicer"/>
    <header_item key="X-BBL-Client-Version" value="02.04.00.70"/>
  </header>
${filaments}</config>`;
    }
}

/**
 * Workplane - The main entry point for creating CAD geometry
 * Similar to CadQuery's Workplane class
 */
class Workplane {
    constructor(plane = "XY") {
        this._shape = null;
        this._plane = plane;
        this._selectedFaces = [];
        this._selectedEdges = [];
        this._selectionMode = null; // 'faces', 'edges', or null
        this._color = null; // hex color string like "#ff0000"
        this._isModifier = false; // true if this is a modifier volume (for 3MF export)
        this._modifiers = null; // array of modifier Workplanes
        this._meta = {}; // generic metadata (infillDensity, infillPattern, partName, etc.)
    }

    /**
     * Clone all properties from source to this Workplane
     * Used by operations to preserve properties across transformations
     * @private
     */
    _cloneProperties(source) {
        this._plane = source._plane;
        this._selectedFaces = source._selectedFaces;
        this._selectedEdges = source._selectedEdges;
        this._selectionMode = source._selectionMode;
        this._color = source._color;
        this._isModifier = source._isModifier;
        this._modifiers = source._modifiers ? [...source._modifiers] : null;
        this._meta = { ...source._meta };
        return this;
    }

    /**
     * Merge properties from another Workplane into this one
     * Used by boolean operations - this object's values win on conflicts
     * @private
     */
    _mergeProperties(other) {
        // Merge metadata: other's values first, then this's values override
        if (other && other._meta) {
            this._meta = { ...other._meta, ...this._meta };
        }
        return this;
    }

    /**
     * Set the color of this workplane object
     * @param {string} hexColor - CSS hex color like "#ff0000" or "red"
     */
    color(hexColor) {
        const result = new Workplane(this._plane);
        result._shape = this._shape;
        result._cloneProperties(this);
        result._color = hexColor;
        return result;
    }

    /**
     * Mark this workplane object as a modifier volume
     * Modifier volumes don't add geometry in 3MF, they just change settings/color
     * in the region where they overlap another part
     */
    asModifier() {
        const result = new Workplane(this._plane);
        result._shape = this._shape;
        result._cloneProperties(this);
        result._isModifier = true;
        return result;
    }

    /**
     * Add a modifier volume to this part
     * In 3MF export, the modifier will be combined with this part as a single object
     * with multiple volumes (the modifier colors/changes settings in overlap region)
     * @param {Workplane} modifier - The modifier volume to add
     * @returns {Workplane} A new Workplane with the modifier attached
     */
    withModifier(modifier) {
        const result = new Workplane(this._plane);
        result._shape = this._shape;
        result._cloneProperties(this);
        // Store modifiers as an array
        result._modifiers = [...(this._modifiers || []), modifier];
        return result;
    }

    /**
     * Get or set generic metadata on this object
     * Metadata is preserved through operations and used by exporters
     * @param {string} key - Metadata key (e.g., 'infillDensity', 'infillPattern', 'partName')
     * @param {*} [value] - If provided, sets the value and returns new Workplane. If omitted, returns current value.
     * @returns {Workplane|*} New Workplane with metadata set, or current value if getting
     */
    meta(key, value) {
        if (value === undefined) {
            return this._meta[key];
        }
        const result = new Workplane(this._plane);
        result._shape = this._shape;
        result._cloneProperties(this);
        result._meta = { ...this._meta, [key]: value };
        return result;
    }

    /**
     * Set infill density for this object (used in 3MF export)
     * @param {number} percent - Infill density percentage (e.g., 5, 15, 20)
     * @returns {Workplane} New Workplane with infill density set
     */
    infillDensity(percent) {
        return this.meta('infillDensity', percent);
    }

    /**
     * Set infill pattern for this object (used in 3MF export)
     * @param {string} pattern - Infill pattern ('grid', 'gyroid', 'honeycomb', 'triangles', 'cubic', 'line', 'concentric')
     * @returns {Workplane} New Workplane with infill pattern set
     */
    infillPattern(pattern) {
        return this.meta('infillPattern', pattern);
    }

    /**
     * Set the part name for this object (used in 3MF export)
     * @param {string} name - Part name
     * @returns {Workplane} New Workplane with part name set
     */
    partName(name) {
        return this.meta('partName', name);
    }

    /**
     * Create a box - centered on XY plane, sitting on Z=0 by default (for 3D printing)
     * @param {boolean} centered - if true, center on XY but bottom at Z=0; if false, corner at origin
     */
    box(length, width, height, centered = true) {
        const result = new Workplane(this._plane);

        // Validate inputs
        if (typeof length !== 'number' || length <= 0) {
            cadError('box', `Invalid length: ${length} (must be positive number)`);
            return result;
        }
        if (typeof width !== 'number' || width <= 0) {
            cadError('box', `Invalid width: ${width} (must be positive number)`);
            return result;
        }
        if (typeof height !== 'number' || height <= 0) {
            cadError('box', `Invalid height: ${height} (must be positive number)`);
            return result;
        }

        try {
            if (centered) {
                // center on X/Y, but bottom at Z=0 (good for 3D printing)
                const box = new oc.BRepPrimAPI_MakeBox_3(
                    new oc.gp_Pnt_3(-length/2, -width/2, 0),
                    length, width, height
                );
                result._shape = box.Shape();
                box.delete();
            } else {
                // corner at origin
                const box = new oc.BRepPrimAPI_MakeBox_2(length, width, height);
                result._shape = box.Shape();
                box.delete();
            }

            if (!result._shape || result._shape.IsNull()) {
                cadError('box', 'Failed to create box shape (result is null)');
            }
        } catch (e) {
            cadError('box', 'Exception creating box', e);
        }

        return result;
    }

    /**
     * Create a cylinder - centered on XY, sitting on Z=0 by default
     * Supports two signatures:
     *   cylinder(radius, height) - specify radius
     *   cylinder({ height, diameter }) - specify diameter (more intuitive)
     */
    cylinder(arg1, arg2) {
        const result = new Workplane(this._plane);

        let radius, height;

        // Check if first argument is an options object
        if (typeof arg1 === 'object' && arg1 !== null) {
            const opts = arg1;
            height = opts.height;
            if (opts.diameter !== undefined) {
                radius = opts.diameter / 2;
            } else if (opts.radius !== undefined) {
                radius = opts.radius;
            } else {
                cadError('cylinder', 'Object argument must have either diameter or radius');
                return result;
            }
        } else {
            // Traditional signature: cylinder(radius, height)
            radius = arg1;
            height = arg2;
        }

        // Validate inputs
        if (typeof radius !== 'number' || radius <= 0) {
            cadError('cylinder', `Invalid radius: ${radius} (must be positive number)`);
            return result;
        }
        if (typeof height !== 'number' || height <= 0) {
            cadError('cylinder', `Invalid height: ${height} (must be positive number)`);
            return result;
        }

        try {
            // Use simple constructor - creates cylinder at origin along Z axis
            const cyl = new oc.BRepPrimAPI_MakeCylinder_1(radius, height);
            result._shape = cyl.Shape();
            cyl.delete();

            if (!result._shape || result._shape.IsNull()) {
                cadError('cylinder', 'Failed to create cylinder shape (result is null)');
            }
        } catch (e) {
            cadError('cylinder', 'Exception creating cylinder', e);
        }

        return result;
    }

    /**
     * Create a sphere
     */
    sphere(radius) {
        const result = new Workplane(this._plane);

        // Validate inputs
        if (typeof radius !== 'number' || radius <= 0) {
            cadError('sphere', `Invalid radius: ${radius} (must be positive number)`);
            return result;
        }

        try {
            const sphere = new oc.BRepPrimAPI_MakeSphere_1(radius);
            result._shape = sphere.Shape();
            sphere.delete();

            if (!result._shape || result._shape.IsNull()) {
                cadError('sphere', 'Failed to create sphere shape (result is null)');
            }
        } catch (e) {
            cadError('sphere', 'Exception creating sphere', e);
        }

        return result;
    }

    /**
     * Create 3D text using opentype.js for font parsing
     * @param {string} textString - The text to render
     * @param {number} fontSize - Height of the text (font size in model units)
     * @param {number} [depth=null] - Depth to extrude (if null, defaults to fontSize/5)
     * @param {string} [fontName=null] - Font name (uses default Overpass Bold if null)
     * @returns {Workplane} - New Workplane with text shape
     */
    text(textString, fontSize, depth = null, fontName = null) {
        const result = new Workplane(this._plane);

        // Get the font
        const font = fontName ? getFont(fontName) : getFont(defaultFontPath);
        if (!font) {
            cadError('text', `Font not loaded: ${fontName || defaultFontPath}. Call loadFont() first.`);
            return result;
        }

        // Default depth
        if (depth === null) {
            depth = fontSize / 5;
        }

        try {
            // Get path commands from opentype.js (font units are typically 1000 or 2048 per em)
            const unitsPerEm = font.unitsPerEm || 1000;
            const scale = fontSize / unitsPerEm;

            // Get the path at origin
            const path = font.getPath(textString, 0, 0, unitsPerEm);

            // Parse path commands into contours
            const contours = [];
            let currentContour = [];

            for (const cmd of path.commands) {
                if (cmd.type === 'M') {
                    // Start new contour
                    if (currentContour.length > 0) {
                        contours.push(currentContour);
                    }
                    currentContour = [{ type: 'M', x: cmd.x * scale, y: cmd.y * scale }];
                } else if (cmd.type === 'L') {
                    currentContour.push({ type: 'L', x: cmd.x * scale, y: cmd.y * scale });
                } else if (cmd.type === 'Q') {
                    currentContour.push({
                        type: 'Q',
                        x1: cmd.x1 * scale, y1: cmd.y1 * scale,
                        x: cmd.x * scale, y: cmd.y * scale
                    });
                } else if (cmd.type === 'C') {
                    currentContour.push({
                        type: 'C',
                        x1: cmd.x1 * scale, y1: cmd.y1 * scale,
                        x2: cmd.x2 * scale, y2: cmd.y2 * scale,
                        x: cmd.x * scale, y: cmd.y * scale
                    });
                } else if (cmd.type === 'Z') {
                    currentContour.push({ type: 'Z' });
                    contours.push(currentContour);
                    currentContour = [];
                }
            }
            if (currentContour.length > 0) {
                contours.push(currentContour);
            }

            if (contours.length === 0) {
                cadError('text', 'No contours found in text path');
                return result;
            }

            // Convert contours to OpenCascade wires
            const wires = [];
            for (const contour of contours) {
                const wire = this._contourToWire(contour);
                if (wire) {
                    wires.push(wire);
                }
            }

            if (wires.length === 0) {
                cadError('text', 'Failed to create wires from text path');
                return result;
            }

            // Build faces from wires (outer contours with holes)
            // Determine which wires are outer contours vs holes by checking orientation
            const faces = this._wiresToFaces(wires);

            if (faces.length === 0) {
                cadError('text', 'Failed to create faces from wires');
                return result;
            }

            // Extrude all faces and fuse them together
            const extrusionVec = new oc.gp_Vec_4(0, 0, depth);
            let combinedShape = null;

            for (const face of faces) {
                const prism = new oc.BRepPrimAPI_MakePrism_1(face, extrusionVec, false, true);
                prism.Build(new oc.Message_ProgressRange_1());

                if (prism.IsDone()) {
                    const solidShape = prism.Shape();
                    if (combinedShape === null) {
                        combinedShape = solidShape;
                    } else {
                        // Fuse with existing shape
                        const fuse = new oc.BRepAlgoAPI_Fuse_3(combinedShape, solidShape, new oc.Message_ProgressRange_1());
                        if (fuse.IsDone()) {
                            combinedShape = fuse.Shape();
                        }
                    }
                }
            }

            if (combinedShape) {
                // Center text in X/Y but place bottom at Z=0
                const bbox = new oc.Bnd_Box_1();
                oc.BRepBndLib.Add(combinedShape, bbox, false);
                const xMin = { current: 0 }, yMin = { current: 0 }, zMin = { current: 0 };
                const xMax = { current: 0 }, yMax = { current: 0 }, zMax = { current: 0 };
                bbox.Get(xMin, yMin, zMin, xMax, yMax, zMax);

                // Center in X and Y, but move bottom to Z=0 (text sits on the plane)
                const centerX = (xMin.current + xMax.current) / 2;
                const centerY = (yMin.current + yMax.current) / 2;
                const offsetZ = zMin.current; // Move bottom to Z=0

                // Translate
                const trsf = new oc.gp_Trsf_1();
                trsf.SetTranslation_1(new oc.gp_Vec_4(-centerX, -centerY, -offsetZ));
                const transform = new oc.BRepBuilderAPI_Transform_2(combinedShape, trsf, true);
                transform.Build(new oc.Message_ProgressRange_1());

                if (transform.IsDone()) {
                    result._shape = transform.Shape();
                } else {
                    result._shape = combinedShape;
                }
            } else {
                cadError('text', 'Failed to extrude text');
            }

        } catch (e) {
            cadError('text', 'Exception creating text', e);
        }

        return result;
    }

    /**
     * Convert a contour (array of path commands) to an OpenCascade wire
     * @private
     */
    _contourToWire(contour) {
        if (contour.length < 2) return null;

        try {
            const wireBuilder = new oc.BRepBuilderAPI_MakeWire_1();
            let startX = 0, startY = 0;
            let currentX = 0, currentY = 0;

            for (let i = 0; i < contour.length; i++) {
                const cmd = contour[i];

                if (cmd.type === 'M') {
                    startX = cmd.x;
                    startY = cmd.y;
                    currentX = cmd.x;
                    currentY = cmd.y;
                } else if (cmd.type === 'L') {
                    const p1 = new oc.gp_Pnt_3(currentX, currentY, 0);
                    const p2 = new oc.gp_Pnt_3(cmd.x, cmd.y, 0);
                    const edge = new oc.BRepBuilderAPI_MakeEdge_3(p1, p2);
                    if (edge.IsDone()) {
                        wireBuilder.Add_1(edge.Edge());
                    }
                    currentX = cmd.x;
                    currentY = cmd.y;
                } else if (cmd.type === 'Q') {
                    // Quadratic bezier - convert to cubic for OpenCascade
                    // Cubic control points from quadratic: P0, P0 + 2/3*(P1-P0), P2 + 2/3*(P1-P2), P2
                    const p0x = currentX, p0y = currentY;
                    const p1x = cmd.x1, p1y = cmd.y1;
                    const p2x = cmd.x, p2y = cmd.y;

                    const cp1x = p0x + 2/3 * (p1x - p0x);
                    const cp1y = p0y + 2/3 * (p1y - p0y);
                    const cp2x = p2x + 2/3 * (p1x - p2x);
                    const cp2y = p2y + 2/3 * (p1y - p2y);

                    const edge = this._makeBezierEdge(p0x, p0y, cp1x, cp1y, cp2x, cp2y, p2x, p2y);
                    if (edge) {
                        wireBuilder.Add_1(edge);
                    }
                    currentX = cmd.x;
                    currentY = cmd.y;
                } else if (cmd.type === 'C') {
                    // Cubic bezier
                    const edge = this._makeBezierEdge(
                        currentX, currentY,
                        cmd.x1, cmd.y1,
                        cmd.x2, cmd.y2,
                        cmd.x, cmd.y
                    );
                    if (edge) {
                        wireBuilder.Add_1(edge);
                    }
                    currentX = cmd.x;
                    currentY = cmd.y;
                } else if (cmd.type === 'Z') {
                    // Close path - add edge back to start if needed
                    if (Math.abs(currentX - startX) > 1e-6 || Math.abs(currentY - startY) > 1e-6) {
                        const p1 = new oc.gp_Pnt_3(currentX, currentY, 0);
                        const p2 = new oc.gp_Pnt_3(startX, startY, 0);
                        const edge = new oc.BRepBuilderAPI_MakeEdge_3(p1, p2);
                        if (edge.IsDone()) {
                            wireBuilder.Add_1(edge.Edge());
                        }
                    }
                }
            }

            if (wireBuilder.IsDone()) {
                return wireBuilder.Wire();
            }
        } catch (e) {
            console.warn('[CAD] Failed to create wire from contour:', e);
        }

        return null;
    }

    /**
     * Create a cubic bezier edge
     * @private
     */
    _makeBezierEdge(x0, y0, x1, y1, x2, y2, x3, y3) {
        try {
            // Create control points array
            const poles = new oc.TColgp_Array1OfPnt_2(1, 4);
            poles.SetValue(1, new oc.gp_Pnt_3(x0, y0, 0));
            poles.SetValue(2, new oc.gp_Pnt_3(x1, y1, 0));
            poles.SetValue(3, new oc.gp_Pnt_3(x2, y2, 0));
            poles.SetValue(4, new oc.gp_Pnt_3(x3, y3, 0));

            // Create bezier curve
            const bezier = new oc.Geom_BezierCurve_1(poles);
            const handleBezier = new oc.Handle_Geom_Curve_2(bezier);

            // Create edge from curve
            const edgeMaker = new oc.BRepBuilderAPI_MakeEdge_24(handleBezier);
            if (edgeMaker.IsDone()) {
                return edgeMaker.Edge();
            }
        } catch (e) {
            console.warn('[CAD] Failed to create bezier edge:', e);
        }
        return null;
    }

    /**
     * Calculate signed area of a wire (positive = CCW, negative = CW)
     * @private
     */
    _wireSignedArea(wire) {
        // Get vertices from the wire edges
        const points = [];
        const explorer = new oc.TopExp_Explorer_2(wire, oc.TopAbs_ShapeEnum.TopAbs_EDGE, oc.TopAbs_ShapeEnum.TopAbs_SHAPE);

        while (explorer.More()) {
            const edge = oc.TopoDS.Edge_1(explorer.Current());
            const curve = oc.BRep_Tool.Curve_2(edge, { current: 0 }, { current: 0 });
            if (curve && !curve.IsNull()) {
                // Sample start point of each edge
                const startParam = curve.get().FirstParameter();
                const pt = curve.get().Value(startParam);
                points.push({ x: pt.X(), y: pt.Y() });
            }
            explorer.Next();
        }

        if (points.length < 3) return 0;

        // Shoelace formula for signed area
        let area = 0;
        for (let i = 0; i < points.length; i++) {
            const j = (i + 1) % points.length;
            area += points[i].x * points[j].y;
            area -= points[j].x * points[i].y;
        }
        return area / 2;
    }

    /**
     * Get bounding box of a wire
     * @private
     */
    _wireBoundingBox(wire) {
        const bbox = new oc.Bnd_Box_1();
        oc.BRepBndLib.Add(wire, bbox, false);
        const xMin = { current: 0 }, yMin = { current: 0 }, zMin = { current: 0 };
        const xMax = { current: 0 }, yMax = { current: 0 }, zMax = { current: 0 };
        bbox.Get(xMin, yMin, zMin, xMax, yMax, zMax);
        return {
            minX: xMin.current, minY: yMin.current,
            maxX: xMax.current, maxY: yMax.current,
            width: xMax.current - xMin.current,
            height: yMax.current - yMin.current
        };
    }

    /**
     * Check if bbox1 is inside bbox2
     * @private
     */
    _bboxInside(inner, outer) {
        return inner.minX >= outer.minX && inner.maxX <= outer.maxX &&
               inner.minY >= outer.minY && inner.maxY <= outer.maxY;
    }

    /**
     * Convert wires to faces, handling outer contours and holes
     * Uses signed area to determine winding and bounding boxes to match holes to outers
     * @private
     */
    _wiresToFaces(wires) {
        if (wires.length === 0) return [];

        // Calculate properties for each wire
        const wireData = wires.map((wire, idx) => ({
            wire,
            idx,
            area: this._wireSignedArea(wire),
            bbox: this._wireBoundingBox(wire)
        }));

        // Separate into outer contours (positive area) and holes (negative area)
        // Note: convention may vary, so we use absolute area to find outer contours
        // Outer contours typically have larger absolute area
        const sortedByArea = [...wireData].sort((a, b) => Math.abs(b.area) - Math.abs(a.area));

        // Group wires: outer contours contain holes
        const groups = []; // Each group: { outer: wireData, holes: [wireData] }
        const assigned = new Set();

        for (const wd of sortedByArea) {
            if (assigned.has(wd.idx)) continue;

            // Check if this wire is inside any existing outer
            let foundOuter = null;
            for (const group of groups) {
                if (this._bboxInside(wd.bbox, group.outer.bbox)) {
                    // Sign should be opposite for hole
                    if ((wd.area > 0) !== (group.outer.area > 0)) {
                        foundOuter = group;
                        break;
                    }
                }
            }

            if (foundOuter) {
                // This is a hole inside an existing outer
                foundOuter.holes.push(wd);
                assigned.add(wd.idx);
            } else {
                // This is a new outer contour
                groups.push({ outer: wd, holes: [] });
                assigned.add(wd.idx);
            }
        }

        // Create faces with holes
        const faces = [];
        for (const group of groups) {
            try {
                // Create face from outer wire
                const faceMaker = new oc.BRepBuilderAPI_MakeFace_15(group.outer.wire, true);
                if (!faceMaker.IsDone()) continue;

                let face = faceMaker.Face();

                // Add holes
                for (const hole of group.holes) {
                    const faceWithHole = new oc.BRepBuilderAPI_MakeFace_22(face, hole.wire);
                    if (faceWithHole.IsDone()) {
                        face = faceWithHole.Face();
                    }
                }

                faces.push(face);
            } catch (e) {
                console.warn('[CAD] Failed to create face from wire:', e);
            }
        }

        return faces;
    }

    /**
     * Create a regular polygon prism (extruded polygon)
     * @param sides - number of sides (3, 4, 5, 6, etc.)
     * @param flatToFlat - flat-to-flat distance (diameter of inscribed circle)
     * @param height - height of the prism
     */
    polygonPrism(sides, flatToFlat, height) {
        const result = new Workplane(this._plane);

        // Validate inputs
        if (typeof sides !== 'number' || sides < 3) {
            cadError('polygonPrism', `Invalid sides: ${sides} (must be >= 3)`);
            return result;
        }
        if (typeof flatToFlat !== 'number' || flatToFlat <= 0) {
            cadError('polygonPrism', `Invalid flatToFlat: ${flatToFlat} (must be positive)`);
            return result;
        }
        if (typeof height !== 'number' || height <= 0) {
            cadError('polygonPrism', `Invalid height: ${height} (must be positive)`);
            return result;
        }

        try {
            const r = flatToFlat / 2; // apothem (inradius)
            const R = r / Math.cos(Math.PI / sides); // circumradius

            // Create polygon wire - offset angle to make flat-topped
            const angleOffset = Math.PI / 2 + Math.PI / sides;
            const wireBuilder = new oc.BRepBuilderAPI_MakeWire_1();

            for (let i = 0; i < sides; i++) {
                const angle1 = (2 * Math.PI * i / sides) + angleOffset;
                const angle2 = (2 * Math.PI * ((i + 1) % sides) / sides) + angleOffset;

                const x1 = R * Math.cos(angle1);
                const y1 = R * Math.sin(angle1);
                const x2 = R * Math.cos(angle2);
                const y2 = R * Math.sin(angle2);

                const p1 = new oc.gp_Pnt_3(x1, y1, 0);
                const p2 = new oc.gp_Pnt_3(x2, y2, 0);

                const edgeMaker = new oc.BRepBuilderAPI_MakeEdge_3(p1, p2);
                wireBuilder.Add_1(edgeMaker.Edge());
                edgeMaker.delete();
            }

            const wire = wireBuilder.Wire();
            wireBuilder.delete();

            // Create face from wire
            const faceMaker = new oc.BRepBuilderAPI_MakeFace_15(wire, true);
            const face = faceMaker.Face();
            faceMaker.delete();

            // Extrude along Z axis
            const vec = new oc.gp_Vec_4(0, 0, height);
            const prism = new oc.BRepPrimAPI_MakePrism_1(face, vec, false, true);
            result._shape = prism.Shape();
            prism.delete();
            vec.delete();

            if (!result._shape || result._shape.IsNull()) {
                cadError('polygonPrism', 'Failed to create polygon prism (result is null)');
            }
        } catch (e) {
            cadError('polygonPrism', 'Exception creating polygon prism', e);
        }

        return result;
    }

    /**
     * Generate a regular pattern of polygons as a single shape (union of all prisms)
     * Use this when you want the pattern itself, not to cut it from something
     * @param options - Configuration object:
     *   - type: "grid"/"square", "hexagon"/"hex", or "triangle" (alternative to sides)
     *   - sides: 3 (triangle), 4 (square), or 6 (hexagon) - default 6
     *   - wallThickness: thickness between shapes in mm - default 0.6
     *   - border: solid border width around edges - default 2
     *   - depth: prism height - default shape thickness + 2
     *   - patternZ: Z position for bottom of pattern (null = zMin - 1)
     */
    pattern(options = {}) {
        // Map type names to sides if provided
        const typeToSides = {
            'grid': 4,
            'square': 4,
            'hexagon': 6,
            'hex': 6,
            'triangle': 3
        };

        let sidesValue = options.sides ?? 6;
        if (options.type) {
            const mapped = typeToSides[options.type.toLowerCase()];
            if (mapped) {
                sidesValue = mapped;
            } else {
                cadError('pattern', `Unknown type: ${options.type}. Use grid, square, hexagon, hex, or triangle`);
                return this;
            }
        }

        const {
            wallThickness = 0.6,
            border = 2,
            depth = null,
            size = null,  // Polygon size (flat-to-flat). null = auto-calculate
            patternZ = null  // Z position for bottom of pattern (null = zMin - 1)
        } = options;
        const sides = sidesValue;

        if (!this._shape) {
            cadError('pattern', 'Cannot create pattern: no shape exists to base dimensions on');
            return this;
        }

        // Validate sides
        if (![3, 4, 6].includes(sides)) {
            cadError('pattern', 'Only 3 (triangle), 4 (square), or 6 (hexagon) sides supported for tiling');
            return this;
        }

        const result = new Workplane(this._plane);
        result._cloneProperties(this);

        try {
            // Get bounding box
            const bbox = new oc.Bnd_Box_1();
            oc.BRepBndLib.Add(this._shape, bbox, false);
            const xMin = { current: 0 }, yMin = { current: 0 }, zMin = { current: 0 };
            const xMax = { current: 0 }, yMax = { current: 0 }, zMax = { current: 0 };
            bbox.Get(xMin, yMin, zMin, xMax, yMax, zMax);
            bbox.delete();

            const length = xMax.current - xMin.current;
            const width = yMax.current - yMin.current;
            const thickness = zMax.current - zMin.current;

            const centerX = (xMin.current + xMax.current) / 2;
            const centerY = (yMin.current + yMax.current) / 2;

            const innerLength = length - 2 * border;
            const innerWidth = width - 2 * border;

            if (innerLength <= 0 || innerWidth <= 0) {
                result._shape = null;
                return result;
            }

            // Calculate polygon size from wall thickness
            const sqrt3 = Math.sqrt(3);

            let polySize, d, h, rowOffset;
            const autoSize = Math.min(innerLength, innerWidth) / 6;
            polySize = size || autoSize;

            if (sides === 6) {
                const r = polySize / 2;
                const R = r / Math.cos(Math.PI / 6);
                d = 2 * R + wallThickness;
                h = d * sqrt3 / 2;
                rowOffset = d / 2;
            } else if (sides === 4) {
                const r = polySize / 2;
                d = 2 * r + wallThickness;
                h = d;
                rowOffset = 0;
            } else {
                const r = polySize / 2;
                const R = r / Math.cos(Math.PI / 3);
                d = 2 * r + wallThickness;
                h = d * sqrt3 / 2;
                rowOffset = d / 2;
            }

            // Calculate polygon circumradius
            let circumRadius;
            if (sides === 6) {
                circumRadius = (polySize / 2) / Math.cos(Math.PI / 6);
            } else if (sides === 4) {
                circumRadius = (polySize / 2) * Math.sqrt(2);
            } else {
                circumRadius = (polySize / 2) / Math.cos(Math.PI / 3);
            }

            // Calculate grid
            const nRows = Math.max(1, Math.ceil(innerWidth / h));
            const nCols = Math.max(1, Math.ceil(innerLength / d));

            const totalSpanX = (nCols - 1) * d;
            const totalSpanY = (nRows - 1) * h;
            const xStart = centerX - totalSpanX / 2;
            const yStart = centerY - totalSpanY / 2;

            const prismDepth = depth || (thickness + 2);
            const zBottom = patternZ !== null ? patternZ : (zMin.current - 1);
            const effectiveBorder = border + circumRadius;

            // Create template prism at origin
            const templatePrism = this.polygonPrism(sides, polySize, prismDepth);
            if (!templatePrism._shape) {
                result._shape = null;
                return result;
            }

            const tileWidth = d;
            const tileHeight = 2 * h;
            const nTileRows = Math.ceil(nRows / 2);
            const nTileCols = nCols;

            // Collect all positioned prisms
            const allShapes = [];

            for (let tileRow = 0; tileRow < nTileRows; tileRow++) {
                for (let tileCol = 0; tileCol < nTileCols; tileCol++) {
                    const tileX = xStart + tileCol * tileWidth;
                    const tileY = yStart + tileRow * tileHeight;

                    // Even-row position
                    const y1 = tileY;
                    const x1 = tileX;
                    if (x1 >= xMin.current + effectiveBorder && x1 <= xMax.current - effectiveBorder &&
                        y1 >= yMin.current + effectiveBorder && y1 <= yMax.current - effectiveBorder) {
                        const t1 = new oc.gp_Trsf_1();
                        t1.SetTranslation_1(new oc.gp_Vec_4(x1, y1, zBottom));
                        const loc1 = new oc.TopLoc_Location_2(t1);
                        allShapes.push(templatePrism._shape.Moved(loc1, false));
                        t1.delete();
                    }

                    // Odd-row position
                    const y2 = tileY + h;
                    const x2 = tileX + rowOffset;
                    if (y2 <= yStart + (nRows - 1) * h + 0.001 &&
                        x2 >= xMin.current + effectiveBorder && x2 <= xMax.current - effectiveBorder &&
                        y2 >= yMin.current + effectiveBorder && y2 <= yMax.current - effectiveBorder) {
                        const t2 = new oc.gp_Trsf_1();
                        t2.SetTranslation_1(new oc.gp_Vec_4(x2, y2, zBottom));
                        const loc2 = new oc.TopLoc_Location_2(t2);
                        allShapes.push(templatePrism._shape.Moved(loc2, false));
                        t2.delete();
                    }
                }
            }

            if (allShapes.length > 0) {
                console.log(`[CAD] pattern: ${allShapes.length} shapes`);

                // Union all shapes using compound (faster than boolean union for this use case)
                const builder = new oc.BRep_Builder();
                const compound = new oc.TopoDS_Compound();
                builder.MakeCompound(compound);
                for (const shape of allShapes) {
                    builder.Add(compound, shape);
                }
                result._shape = compound;
            } else {
                result._shape = null;
            }
        } catch (e) {
            cadError('pattern', 'Exception creating pattern', e);
            result._shape = null;
        }

        return result;
    }

    /**
     * Cut a regular pattern of polygons through the shape
     * Creates a grid of hexagons, squares, or triangles and cuts them out
     * @param options - Configuration object:
     *   - type: "grid"/"square", "hexagon"/"hex", or "triangle" (alternative to sides)
     *   - sides: 3 (triangle), 4 (square), or 6 (hexagon) - default 6
     *   - wallThickness: thickness between shapes in mm - default 0.6
     *   - border: solid border width around edges - default 2
     *   - depth: cut depth (null = through-cut) - default null
     *   - cutFromZ: Z position to cut from (null = auto from top) - for cutting base from below
     */
    cutPattern(options = {}) {
        // Map type names to sides if provided
        const typeToSides = {
            'grid': 4,
            'square': 4,
            'hexagon': 6,
            'hex': 6,
            'triangle': 3
        };

        let sidesValue = options.sides ?? 6;
        if (options.type) {
            const mapped = typeToSides[options.type.toLowerCase()];
            if (mapped) {
                sidesValue = mapped;
            } else {
                cadError('cutPattern', `Unknown type: ${options.type}. Use grid, square, hexagon, hex, or triangle`);
                return this;
            }
        }

        const {
            wallThickness = 0.6,
            border = 2,
            depth = null,
            size = null,
            cutFromZ = null
        } = options;
        const sides = sidesValue;

        if (!this._shape) {
            cadError('cutPattern', 'Cannot cut pattern: no shape exists');
            return this;
        }

        if (![3, 4, 6].includes(sides)) {
            cadError('cutPattern', 'Only 3 (triangle), 4 (square), or 6 (hexagon) sides supported for tiling');
            return this;
        }

        const result = new Workplane(this._plane);

        try {
            // Get bounding box
            const bbox = new oc.Bnd_Box_1();
            oc.BRepBndLib.Add(this._shape, bbox, false);
            const xMin = { current: 0 }, yMin = { current: 0 }, zMin = { current: 0 };
            const xMax = { current: 0 }, yMax = { current: 0 }, zMax = { current: 0 };
            bbox.Get(xMin, yMin, zMin, xMax, yMax, zMax);
            bbox.delete();

            const length = xMax.current - xMin.current;
            const width = yMax.current - yMin.current;
            const thickness = zMax.current - zMin.current;

            const centerX = (xMin.current + xMax.current) / 2;
            const centerY = (yMin.current + yMax.current) / 2;

            const innerLength = length - 2 * border;
            const innerWidth = width - 2 * border;

            if (innerLength <= 0 || innerWidth <= 0) {
                result._shape = this._shape;
                return result;
            }

            // Calculate polygon size from wall thickness
            const sqrt3 = Math.sqrt(3);

            let polySize, d, h, rowOffset;
            const autoSize = Math.min(innerLength, innerWidth) / 6;
            polySize = size || autoSize;

            if (sides === 6) {
                const r = polySize / 2;
                const R = r / Math.cos(Math.PI / 6);
                d = 2 * R + wallThickness;
                h = d * sqrt3 / 2;
                rowOffset = d / 2;
            } else if (sides === 4) {
                const r = polySize / 2;
                d = 2 * r + wallThickness;
                h = d;
                rowOffset = 0;
            } else {
                const r = polySize / 2;
                const R = r / Math.cos(Math.PI / 3);
                d = 2 * r + wallThickness;
                h = d * sqrt3 / 2;
                rowOffset = d / 2;
            }

            // Calculate polygon circumradius
            let circumRadius;
            if (sides === 6) {
                circumRadius = (polySize / 2) / Math.cos(Math.PI / 6);
            } else if (sides === 4) {
                circumRadius = (polySize / 2) * Math.sqrt(2);
            } else {
                circumRadius = (polySize / 2) / Math.cos(Math.PI / 3);
            }

            // Calculate grid
            const nRows = Math.max(1, Math.ceil(innerWidth / h));
            const nCols = Math.max(1, Math.ceil(innerLength / d));

            const totalSpanX = (nCols - 1) * d;
            const totalSpanY = (nRows - 1) * h;
            const xStart = centerX - totalSpanX / 2;
            const yStart = centerY - totalSpanY / 2;

            const cutDepth = depth || (thickness + 2);
            const cutZ = cutFromZ !== null ? cutFromZ : (zMax.current + 1);
            const effectiveBorder = border + circumRadius;

            // Create template prism at origin
            const templatePrism = this.polygonPrism(sides, polySize, cutDepth);
            if (!templatePrism._shape) {
                result._shape = this._shape;
                return result;
            }

            const tileWidth = d;
            const tileHeight = 2 * h;
            const nTileRows = Math.ceil(nRows / 2);
            const nTileCols = nCols;

            // Collect all positioned prisms
            const allShapes = [];

            for (let tileRow = 0; tileRow < nTileRows; tileRow++) {
                for (let tileCol = 0; tileCol < nTileCols; tileCol++) {
                    const tileX = xStart + tileCol * tileWidth;
                    const tileY = yStart + tileRow * tileHeight;

                    // Even-row position
                    const y1 = tileY;
                    const x1 = tileX;
                    if (x1 >= xMin.current + effectiveBorder && x1 <= xMax.current - effectiveBorder &&
                        y1 >= yMin.current + effectiveBorder && y1 <= yMax.current - effectiveBorder) {
                        const t1 = new oc.gp_Trsf_1();
                        t1.SetTranslation_1(new oc.gp_Vec_4(x1, y1, cutZ - cutDepth));
                        const loc1 = new oc.TopLoc_Location_2(t1);
                        allShapes.push(templatePrism._shape.Moved(loc1, false));
                        t1.delete();
                    }

                    // Odd-row position
                    const y2 = tileY + h;
                    const x2 = tileX + rowOffset;
                    if (y2 <= yStart + (nRows - 1) * h + 0.001 &&
                        x2 >= xMin.current + effectiveBorder && x2 <= xMax.current - effectiveBorder &&
                        y2 >= yMin.current + effectiveBorder && y2 <= yMax.current - effectiveBorder) {
                        const t2 = new oc.gp_Trsf_1();
                        t2.SetTranslation_1(new oc.gp_Vec_4(x2, y2, cutZ - cutDepth));
                        const loc2 = new oc.TopLoc_Location_2(t2);
                        allShapes.push(templatePrism._shape.Moved(loc2, false));
                        t2.delete();
                    }
                }
            }

            if (allShapes.length > 0) {
                console.log(`[CAD] cutPattern: ${allShapes.length} holes, using ListOfShape API`);

                const toolList = new oc.TopTools_ListOfShape_1();
                for (const shape of allShapes) {
                    toolList.Append_1(shape);
                }

                const argList = new oc.TopTools_ListOfShape_1();
                argList.Append_1(this._shape);

                const cut = new oc.BRepAlgoAPI_Cut_1();
                cut.SetArguments(argList);
                cut.SetTools(toolList);
                cut.Build(new oc.Message_ProgressRange_1());

                if (cut.IsDone()) {
                    result._shape = cut.Shape();
                } else {
                    cadError('cutPattern', 'Boolean cut failed');
                    result._shape = this._shape;
                }
                cut.delete();
            } else {
                result._shape = this._shape;
            }
        } catch (e) {
            cadError('cutPattern', 'Exception cutting pattern', e);
            result._shape = this._shape;
        }

        return result;
    }

    /**
     * Select faces matching a selector
     * Selectors: ">Z" (top), "<Z" (bottom), ">X", "<X", ">Y", "<Y", "|Z" (parallel to Z), etc.
     * Preserves all properties
     */
    faces(selector = null) {
        const result = new Workplane(this._plane);
        result._cloneProperties(this);
        result._shape = this._shape;
        result._selectionMode = 'faces';
        result._selectedFaces = [];

        if (!this._shape) return result;

        const explorer = new oc.TopExp_Explorer_2(
            this._shape,
            oc.TopAbs_ShapeEnum.TopAbs_FACE,
            oc.TopAbs_ShapeEnum.TopAbs_SHAPE
        );

        const faces = [];
        while (explorer.More()) {
            const face = oc.TopoDS.Face_1(explorer.Current());
            faces.push(face);
            explorer.Next();
        }
        explorer.delete();

        if (selector) {
            result._selectedFaces = this._filterFaces(faces, selector);
        } else {
            result._selectedFaces = faces;
        }

        return result;
    }

    /**
     * Filter faces based on selector
     */
    _filterFaces(faces, selector) {
        const direction = selector[0]; // '>' or '<' or '|'
        const axis = selector[1].toUpperCase(); // 'X', 'Y', or 'Z'

        const getAxisIndex = (a) => ({ 'X': 0, 'Y': 1, 'Z': 2 }[a]);
        const axisIdx = getAxisIndex(axis);

        // Get face centers and filter
        const facesWithCenter = faces.map(face => {
            const props = new oc.GProp_GProps_1();
            oc.BRepGProp.SurfaceProperties_1(face, props, false, false);
            const center = props.CentreOfMass();
            const coords = [center.X(), center.Y(), center.Z()];
            props.delete();
            return { face, center: coords[axisIdx] };
        });

        if (direction === '>') {
            // Select face(s) with maximum value on axis
            const maxVal = Math.max(...facesWithCenter.map(f => f.center));
            return facesWithCenter.filter(f => Math.abs(f.center - maxVal) < 0.001).map(f => f.face);
        } else if (direction === '<') {
            // Select face(s) with minimum value on axis
            const minVal = Math.min(...facesWithCenter.map(f => f.center));
            return facesWithCenter.filter(f => Math.abs(f.center - minVal) < 0.001).map(f => f.face);
        } else if (direction === '|') {
            // Select faces parallel to axis (normal perpendicular to axis)
            return faces.filter(face => {
                const surface = oc.BRep_Tool.Surface_2(face);
                // For now, return all faces if parallel selector used
                return true;
            });
        }

        return faces;
    }

    /**
     * Select faces NOT matching a selector (set subtraction)
     * facesNot(">Z") returns all faces except those with max Z
     * Preserves all properties
     */
    facesNot(selector) {
        const result = new Workplane(this._plane);
        result._cloneProperties(this);
        result._shape = this._shape;
        result._selectionMode = 'faces';
        result._selectedFaces = [];

        if (!this._shape || !selector) return result;

        // Get all faces
        const explorer = new oc.TopExp_Explorer_2(
            this._shape,
            oc.TopAbs_ShapeEnum.TopAbs_FACE,
            oc.TopAbs_ShapeEnum.TopAbs_SHAPE
        );

        const allFaces = [];
        while (explorer.More()) {
            const face = oc.TopoDS.Face_1(explorer.Current());
            allFaces.push(face);
            explorer.Next();
        }
        explorer.delete();

        // Get faces matching selector
        const matchingFaces = this._filterFaces(allFaces, selector);

        // Build hash set of matching faces
        const matchingHashes = new Set(matchingFaces.map(f => f.HashCode(1000000)));

        // Return faces NOT in the matching set
        result._selectedFaces = allFaces.filter(f => !matchingHashes.has(f.HashCode(1000000)));

        return result;
    }

    /**
     * Select edges
     * If faces are selected, select edges of those faces
     * Otherwise, select all edges
     * Selector can be:
     *   "|X", "|Y", "|Z" - edges parallel to axis
     *   ">X", ">Y", ">Z" - edge with max position on axis
     *   "<X", "<Y", "<Z" - edge with min position on axis
     * Preserves all properties
     */
    edges(selector = null) {
        const result = new Workplane(this._plane);
        result._cloneProperties(this);
        result._shape = this._shape;
        result._selectionMode = 'edges';
        result._selectedEdges = [];

        if (!this._shape) return result;

        const edgeSet = new Set();
        let edges = [];

        if (this._selectionMode === 'faces' && this._selectedFaces.length > 0) {
            // Get edges from selected faces
            for (const face of this._selectedFaces) {
                const explorer = new oc.TopExp_Explorer_2(
                    face,
                    oc.TopAbs_ShapeEnum.TopAbs_EDGE,
                    oc.TopAbs_ShapeEnum.TopAbs_SHAPE
                );
                while (explorer.More()) {
                    const edge = oc.TopoDS.Edge_1(explorer.Current());
                    const hash = edge.HashCode(1000000);
                    if (!edgeSet.has(hash)) {
                        edgeSet.add(hash);
                        edges.push(edge);
                    }
                    explorer.Next();
                }
                explorer.delete();
            }
        } else {
            // Get all edges from shape (with deduplication)
            const explorer = new oc.TopExp_Explorer_2(
                this._shape,
                oc.TopAbs_ShapeEnum.TopAbs_EDGE,
                oc.TopAbs_ShapeEnum.TopAbs_SHAPE
            );
            while (explorer.More()) {
                const edge = oc.TopoDS.Edge_1(explorer.Current());
                const hash = edge.HashCode(1000000);
                if (!edgeSet.has(hash)) {
                    edgeSet.add(hash);
                    edges.push(edge);
                }
                explorer.Next();
            }
            explorer.delete();
        }

        // Apply selector filter if provided
        if (selector && edges.length > 0) {
            edges = this._filterEdges(edges, selector);
        }

        result._selectedEdges = edges;
        return result;
    }

    /**
     * Filter edges based on selector
     * "|X", "|Y", "|Z" - parallel to axis
     * ">X", ">Y", ">Z" - max position on axis
     * "<X", "<Y", "<Z" - min position on axis
     */
    _filterEdges(edges, selector) {
        const match = selector.match(/^([|><])([XYZ])$/i);
        if (!match) {
            console.warn(`[CAD] Unknown edge selector: ${selector}`);
            return edges;
        }

        const op = match[1];
        const axis = match[2].toUpperCase();
        const axisIndex = { 'X': 0, 'Y': 1, 'Z': 2 }[axis];

        // Helper to get edge direction and midpoint
        const getEdgeInfo = (edge) => {
            try {
                const curve = new oc.BRepAdaptor_Curve_2(edge);
                const first = curve.FirstParameter();
                const last = curve.LastParameter();

                // Get start and end points
                const p1 = curve.Value(first);
                const p2 = curve.Value(last);

                // Direction vector
                const dx = p2.X() - p1.X();
                const dy = p2.Y() - p1.Y();
                const dz = p2.Z() - p1.Z();
                const len = Math.sqrt(dx*dx + dy*dy + dz*dz);

                // Midpoint for position-based selection
                const mid = curve.Value((first + last) / 2);
                const midCoord = [mid.X(), mid.Y(), mid.Z()][axisIndex];

                // Normalized direction
                const dir = len > 1e-6 ? [dx/len, dy/len, dz/len] : [0, 0, 0];

                curve.delete();
                p1.delete();
                p2.delete();
                mid.delete();

                return { dir, midCoord };
            } catch (e) {
                return null;
            }
        };

        if (op === '|') {
            // Parallel to axis - direction should be mostly along that axis
            const tolerance = 0.1; // Allow small deviation
            return edges.filter(edge => {
                const info = getEdgeInfo(edge);
                if (!info) return false;
                const { dir } = info;
                // Check if edge is parallel to axis (direction component ~1 or ~-1)
                const axisComponent = Math.abs(dir[axisIndex]);
                return axisComponent > (1 - tolerance);
            });
        } else if (op === '>' || op === '<') {
            // Max or min position on axis
            let bestEdges = [];
            let bestValue = op === '>' ? -Infinity : Infinity;

            for (const edge of edges) {
                const info = getEdgeInfo(edge);
                if (!info) continue;
                const { midCoord } = info;

                if (op === '>') {
                    if (midCoord > bestValue + 1e-6) {
                        bestValue = midCoord;
                        bestEdges = [edge];
                    } else if (Math.abs(midCoord - bestValue) < 1e-6) {
                        bestEdges.push(edge);
                    }
                } else {
                    if (midCoord < bestValue - 1e-6) {
                        bestValue = midCoord;
                        bestEdges = [edge];
                    } else if (Math.abs(midCoord - bestValue) < 1e-6) {
                        bestEdges.push(edge);
                    }
                }
            }
            return bestEdges;
        }

        return edges;
    }

    /**
     * Select edges NOT matching a selector (set subtraction)
     * edgesNot("|Z") returns all edges except those parallel to Z
     * Preserves all properties
     */
    edgesNot(selector) {
        const result = new Workplane(this._plane);
        result._cloneProperties(this);
        result._shape = this._shape;
        result._selectionMode = 'edges';
        result._selectedEdges = [];

        if (!this._shape || !selector) return result;

        const edgeSet = new Set();
        let allEdges = [];

        if (this._selectionMode === 'faces' && this._selectedFaces.length > 0) {
            // Get edges from selected faces
            for (const face of this._selectedFaces) {
                const explorer = new oc.TopExp_Explorer_2(
                    face,
                    oc.TopAbs_ShapeEnum.TopAbs_EDGE,
                    oc.TopAbs_ShapeEnum.TopAbs_SHAPE
                );
                while (explorer.More()) {
                    const edge = oc.TopoDS.Edge_1(explorer.Current());
                    const hash = edge.HashCode(1000000);
                    if (!edgeSet.has(hash)) {
                        edgeSet.add(hash);
                        allEdges.push(edge);
                    }
                    explorer.Next();
                }
                explorer.delete();
            }
        } else {
            // Get all edges from shape (with deduplication)
            const explorer = new oc.TopExp_Explorer_2(
                this._shape,
                oc.TopAbs_ShapeEnum.TopAbs_EDGE,
                oc.TopAbs_ShapeEnum.TopAbs_SHAPE
            );
            while (explorer.More()) {
                const edge = oc.TopoDS.Edge_1(explorer.Current());
                const hash = edge.HashCode(1000000);
                if (!edgeSet.has(hash)) {
                    edgeSet.add(hash);
                    allEdges.push(edge);
                }
                explorer.Next();
            }
            explorer.delete();
        }

        // Get edges matching selector
        const matchingEdges = this._filterEdges(allEdges, selector);

        // Build hash set of matching edges
        const matchingHashes = new Set(matchingEdges.map(e => e.HashCode(1000000)));

        // Return edges NOT in the matching set
        result._selectedEdges = allEdges.filter(e => !matchingHashes.has(e.HashCode(1000000)));

        return result;
    }

    /**
     * Get the Z range (min/max) of an edge
     */
    _getEdgeZRange(edge) {
        try {
            const curve = new oc.BRepAdaptor_Curve_2(edge);
            const first = curve.FirstParameter();
            const last = curve.LastParameter();
            const p1 = curve.Value(first);
            const p2 = curve.Value(last);
            const z1 = p1.Z();
            const z2 = p2.Z();
            p1.delete();
            p2.delete();
            curve.delete();
            return { zMin: Math.min(z1, z2), zMax: Math.max(z1, z2) };
        } catch (e) {
            return null;
        }
    }

    /**
     * Filter selected edges using a predicate function
     * The predicate receives an object with edge info: { zMin, zMax, edge }
     * Example: .filterEdges(e => e.zMin > 0)
     * Preserves all properties
     */
    filterEdges(predicate) {
        const result = new Workplane(this._plane);
        result._cloneProperties(this);
        result._shape = this._shape;
        result._selectionMode = 'edges';
        result._selectedEdges = [];

        if (!this._selectedEdges || this._selectedEdges.length === 0) {
            return result;
        }

        result._selectedEdges = this._selectedEdges.filter(edge => {
            const zRange = this._getEdgeZRange(edge);
            if (!zRange) return false;
            return predicate({ zMin: zRange.zMin, zMax: zRange.zMax, edge });
        });

        return result;
    }

    /**
     * Filter out edges at the bottom (zMin of the shape)
     * Useful after boolean operations to exclude bottom edges from filleting
     */
    filterOutBottom() {
        if (!this._selectedEdges || this._selectedEdges.length === 0 || !this._shape) {
            return this;
        }

        // Get shape's bounding box to find zMin
        const bbox = new oc.Bnd_Box_1();
        oc.BRepBndLib.Add(this._shape, bbox, false);
        const zMinRef = { current: 0 }, yMin = { current: 0 }, zMinShape = { current: 0 };
        const xMax = { current: 0 }, yMax = { current: 0 }, zMax = { current: 0 };
        bbox.Get(zMinRef, yMin, zMinShape, xMax, yMax, zMax);
        bbox.delete();

        const shapeZMin = zMinShape.current;
        const tolerance = 0.01;

        // Filter out edges that are at zMin
        return this.filterEdges(e => e.zMin > shapeZMin + tolerance || e.zMax > shapeZMin + tolerance);
    }

    /**
     * Filter out edges at the top (zMax of the shape)
     * Useful to exclude top edges from filleting
     */
    filterOutTop() {
        if (!this._selectedEdges || this._selectedEdges.length === 0 || !this._shape) {
            return this;
        }

        // Get shape's bounding box to find zMax
        const bbox = new oc.Bnd_Box_1();
        oc.BRepBndLib.Add(this._shape, bbox, false);
        const xMin = { current: 0 }, yMin = { current: 0 }, zMin = { current: 0 };
        const xMax = { current: 0 }, yMax = { current: 0 }, zMaxRef = { current: 0 };
        bbox.Get(xMin, yMin, zMin, xMax, yMax, zMaxRef);
        bbox.delete();

        const shapeZMax = zMaxRef.current;
        const tolerance = 0.01;

        // Filter out edges that are at zMax
        return this.filterEdges(e => e.zMin < shapeZMax - tolerance || e.zMax < shapeZMax - tolerance);
    }

    /**
     * Create a hole through the shape along Z axis at XY center
     * Preserves all properties
     */
    hole(diameter, depth = null) {
        if (!this._shape) {
            cadError('hole', 'Cannot create hole: no shape exists');
            return this;
        }

        const result = new Workplane(this._plane);
        result._cloneProperties(this);

        // Validate inputs
        if (typeof diameter !== 'number' || diameter <= 0) {
            cadError('hole', `Invalid diameter: ${diameter} (must be positive number)`);
            result._shape = this._shape;
            return result;
        }

        const radius = diameter / 2;

        try {
            // Get bounding box to determine hole depth
            const bbox = new oc.Bnd_Box_1();
            oc.BRepBndLib.Add(this._shape, bbox, false);
            const xMin = { current: 0 }, yMin = { current: 0 }, zMin = { current: 0 };
            const xMax = { current: 0 }, yMax = { current: 0 }, zMax = { current: 0 };
            bbox.Get(xMin, yMin, zMin, xMax, yMax, zMax);
            bbox.delete();

            const zHeight = (zMax.current - zMin.current) + 2;  // slightly taller than shape

            // Create cylinder at origin using simple constructor
            const cylinder = new oc.BRepPrimAPI_MakeCylinder_1(radius, zHeight);
            let cylShape = cylinder.Shape();
            cylinder.delete();

            // Translate cylinder to correct position (center XY, start below zMin)
            const centerX = (xMin.current + xMax.current) / 2;
            const centerY = (yMin.current + yMax.current) / 2;
            const zBottom = zMin.current - 1;

            const transform = new oc.gp_Trsf_1();
            transform.SetTranslation_1(new oc.gp_Vec_4(centerX, centerY, zBottom));
            const transformer = new oc.BRepBuilderAPI_Transform_2(cylShape, transform, true);
            cylShape = transformer.Shape();
            transformer.delete();
            transform.delete();

            // Boolean cut
            const cut = new oc.BRepAlgoAPI_Cut_3(this._shape, cylShape, new oc.Message_ProgressRange_1());
            cut.Build(new oc.Message_ProgressRange_1());

            if (cut.IsDone()) {
                result._shape = cut.Shape();
                if (!result._shape || result._shape.IsNull()) {
                    cadError('hole', 'Boolean cut succeeded but result shape is null');
                    result._shape = this._shape;
                }
            } else {
                cadError('hole', 'Boolean cut operation failed (IsDone=false)');
                result._shape = this._shape;
            }
            cut.delete();
        } catch (e) {
            cadError('hole', 'Exception creating hole', e);
            result._shape = this._shape;
        }

        return result;
    }

    /**
     * Apply chamfer to selected edges
     * Uses BRepFilletAPI_MakeChamfer
     * Preserves all properties
     */
    chamfer(distance) {
        if (!this._shape) {
            cadError('chamfer', 'Cannot chamfer: no shape exists');
            return this;
        }

        // Validate inputs
        if (typeof distance !== 'number' || distance <= 0) {
            cadError('chamfer', `Invalid distance: ${distance} (must be positive number)`);
            return this;
        }

        const result = new Workplane(this._plane);
        result._cloneProperties(this);

        // Try different constructor patterns
        let chamferBuilder = null;
        const constructors = ['BRepFilletAPI_MakeChamfer_1', 'BRepFilletAPI_MakeChamfer'];

        for (const ctorName of constructors) {
            if (typeof oc[ctorName] === 'function') {
                try {
                    chamferBuilder = new oc[ctorName](this._shape);
                    break;
                } catch (e) {
                    console.warn(`Chamfer constructor ${ctorName} failed:`, e.message);
                }
            }
        }

        if (!chamferBuilder) {
            cadError('chamfer', 'No working chamfer constructor found, falling back to fillet');
            return this.fillet(distance);
        }

        // Find the Add method
        let addMethod = null;
        for (const methodName of ['Add_2', 'Add_1', 'Add']) {
            if (typeof chamferBuilder[methodName] === 'function') {
                addMethod = methodName;
                break;
            }
        }

        if (!addMethod) {
            cadError('chamfer', 'No Add method found on chamfer builder');
            chamferBuilder.delete();
            result._shape = this._shape;
            return result;
        }

        let edges = this._selectedEdges;
        let edgesAdded = 0;

        try {
            if (edges.length === 0) {
                // Chamfer all edges
                const explorer = new oc.TopExp_Explorer_2(
                    this._shape,
                    oc.TopAbs_ShapeEnum.TopAbs_EDGE,
                    oc.TopAbs_ShapeEnum.TopAbs_SHAPE
                );
                while (explorer.More()) {
                    const edge = oc.TopoDS.Edge_1(explorer.Current());
                    try {
                        chamferBuilder[addMethod](distance, edge);
                        edgesAdded++;
                    } catch (e) {
                        // Some edges may not be chamferable
                    }
                    explorer.Next();
                }
                explorer.delete();
            } else {
                for (const edge of edges) {
                    try {
                        chamferBuilder[addMethod](distance, edge);
                        edgesAdded++;
                    } catch (e) {
                        // Some edges may not be chamferable
                    }
                }
            }

            if (edgesAdded === 0) {
                cadError('chamfer', 'No edges were added to chamfer builder');
                chamferBuilder.delete();
                result._shape = this._shape;
                return result;
            }

            chamferBuilder.Build(new oc.Message_ProgressRange_1());
            if (chamferBuilder.IsDone()) {
                result._shape = chamferBuilder.Shape();
                if (!result._shape || result._shape.IsNull()) {
                    cadError('chamfer', 'Chamfer succeeded but result shape is null');
                    result._shape = this._shape;
                }
            } else {
                cadError('chamfer', 'Chamfer build failed (IsDone=false)');
                result._shape = this._shape;
            }
        } catch (e) {
            cadError('chamfer', 'Exception during chamfer', e);
            result._shape = this._shape;
        }

        chamferBuilder.delete();
        return result;
    }

    /**
     * Apply fillet to selected edges
     * Preserves all properties
     */
    fillet(radius) {
        if (!this._shape) {
            cadError('fillet', 'Cannot fillet: no shape exists');
            return this;
        }

        // Validate inputs
        if (typeof radius !== 'number' || radius <= 0) {
            cadError('fillet', `Invalid radius: ${radius} (must be positive number)`);
            return this;
        }

        const result = new Workplane(this._plane);
        result._cloneProperties(this);

        // Try different constructor patterns for BRepFilletAPI_MakeFillet
        // The constructor requires (shape, ChFi3d_FilletShape) - both parameters
        let filletBuilder = null;

        // Get the fillet shape enum - default to Rational which is the most common
        const filletShape = oc.ChFi3d_FilletShape?.ChFi3d_Rational;

        // Try constructors in order of preference
        const constructors = [
            'BRepFilletAPI_MakeFillet_1',  // requires 2 params: (shape, filletShape)
            'BRepFilletAPI_MakeFillet_2',
            'BRepFilletAPI_MakeFillet'
        ];

        for (const ctorName of constructors) {
            if (typeof oc[ctorName] === 'function') {
                try {
                    // Always try with both parameters since that's what OpenCascade.js expects
                    if (filletShape !== undefined) {
                        filletBuilder = new oc[ctorName](this._shape, filletShape);
                    } else {
                        // Fallback to trying with just shape (might not work)
                        filletBuilder = new oc[ctorName](this._shape);
                    }
                    break;
                } catch (e) {
                    console.warn(`Fillet constructor ${ctorName} failed:`, e.message);
                }
            }
        }

        if (!filletBuilder) {
            cadError('fillet', 'No working fillet constructor found. Available: ' +
                Object.keys(oc).filter(k => k.includes('MakeFillet')).join(', '));
            result._shape = this._shape;
            return result;
        }

        // Find the Add method - try different variants
        let addMethod = null;
        const addMethodNames = ['Add_2', 'Add_1', 'Add'];
        for (const methodName of addMethodNames) {
            if (typeof filletBuilder[methodName] === 'function') {
                addMethod = methodName;
                break;
            }
        }

        if (!addMethod) {
            cadError('fillet', 'No Add method found on fillet builder');
            filletBuilder.delete();
            result._shape = this._shape;
            return result;
        }

        let edges = this._selectedEdges;
        let edgesAdded = 0;

        if (edges.length === 0) {
            // Fillet all edges
            const explorer = new oc.TopExp_Explorer_2(
                this._shape,
                oc.TopAbs_ShapeEnum.TopAbs_EDGE,
                oc.TopAbs_ShapeEnum.TopAbs_SHAPE
            );
            while (explorer.More()) {
                const edge = oc.TopoDS.Edge_1(explorer.Current());
                try {
                    filletBuilder[addMethod](radius, edge);
                    edgesAdded++;
                } catch (e) {
                    // Some edges may not be fillettable - that's ok
                }
                explorer.Next();
            }
            explorer.delete();
        } else {
            for (const edge of edges) {
                try {
                    filletBuilder[addMethod](radius, edge);
                    edgesAdded++;
                } catch (e) {
                    // Skip edges that can't be filleted
                }
            }
        }

        if (edgesAdded === 0) {
            cadError('fillet', 'No edges were added to fillet builder');
            filletBuilder.delete();
            result._shape = this._shape;
            return result;
        }

        try {
            filletBuilder.Build(new oc.Message_ProgressRange_1());
            if (filletBuilder.IsDone()) {
                result._shape = filletBuilder.Shape();
                if (!result._shape || result._shape.IsNull()) {
                    cadError('fillet', 'Fillet succeeded but result shape is null');
                    result._shape = this._shape;
                }
            } else {
                cadError('fillet', 'Fillet build failed (IsDone=false)');
                result._shape = this._shape;
            }
        } catch (e) {
            cadError('fillet', 'Exception during fillet', e);
            result._shape = this._shape;
        }
        filletBuilder.delete();

        return result;
    }

    /**
     * Boolean union with another shape
     * Preserves metadata from both shapes (this wins on conflicts)
     */
    union(other) {
        if (!this._shape) {
            cadError('union', 'Cannot union: this shape is null');
            return this;
        }
        if (!other || !other._shape) {
            cadError('union', 'Cannot union: other shape is null');
            return this;
        }

        const result = new Workplane(this._plane);
        result._cloneProperties(this);
        result._mergeProperties(other);

        try {
            const fuse = new oc.BRepAlgoAPI_Fuse_3(
                this._shape,
                other._shape,
                new oc.Message_ProgressRange_1()
            );
            fuse.Build(new oc.Message_ProgressRange_1());

            if (fuse.IsDone()) {
                let fusedShape = fuse.Shape();
                if (!fusedShape || fusedShape.IsNull()) {
                    cadError('union', 'Fuse succeeded but result shape is null');
                    result._shape = this._shape;
                } else {
                    // Unify same-domain faces/edges to remove internal seams
                    // This is essential for chamfer/fillet to work on unioned shapes
                    try {
                        const unify = new oc.ShapeUpgrade_UnifySameDomain_2(fusedShape, true, true, false);
                        unify.Build();
                        const unifiedShape = unify.Shape();
                        if (unifiedShape && !unifiedShape.IsNull()) {
                            result._shape = unifiedShape;
                            console.log('[CAD] UnifySameDomain succeeded');
                        } else {
                            console.log('[CAD] UnifySameDomain returned null shape, using fused shape');
                            result._shape = fusedShape;
                        }
                        unify.delete();
                    } catch (unifyErr) {
                        // If unify fails, use the fused shape as-is
                        console.log('[CAD] UnifySameDomain failed:', unifyErr.message || unifyErr);
                        result._shape = fusedShape;
                    }
                }
            } else {
                cadError('union', 'Fuse operation failed (IsDone=false)');
                result._shape = this._shape;
            }
            fuse.delete();
        } catch (e) {
            cadError('union', 'Exception during union', e);
            result._shape = this._shape;
        }

        return result;
    }

    /**
     * Boolean cut (subtract another shape)
     * Preserves metadata from both shapes (this wins on conflicts)
     */
    cut(other) {
        if (!this._shape) {
            cadError('cut', 'Cannot cut: this shape is null');
            return this;
        }
        if (!other || !other._shape) {
            cadError('cut', 'Cannot cut: other shape is null');
            return this;
        }

        const result = new Workplane(this._plane);
        result._cloneProperties(this);
        result._mergeProperties(other);

        try {
            const cut = new oc.BRepAlgoAPI_Cut_3(
                this._shape,
                other._shape,
                new oc.Message_ProgressRange_1()
            );
            cut.Build(new oc.Message_ProgressRange_1());

            if (cut.IsDone()) {
                result._shape = cut.Shape();
                if (!result._shape || result._shape.IsNull()) {
                    cadError('cut', 'Cut succeeded but result shape is null');
                    result._shape = this._shape;
                }
            } else {
                cadError('cut', 'Cut operation failed (IsDone=false)');
                result._shape = this._shape;
            }
            cut.delete();
        } catch (e) {
            cadError('cut', 'Exception during cut', e);
            result._shape = this._shape;
        }

        return result;
    }

    /**
     * Boolean intersection
     * Preserves metadata from both shapes (this wins on conflicts)
     */
    intersect(other) {
        if (!this._shape) {
            cadError('intersect', 'Cannot intersect: this shape is null');
            return this;
        }
        if (!other || !other._shape) {
            cadError('intersect', 'Cannot intersect: other shape is null');
            return this;
        }

        const result = new Workplane(this._plane);
        result._cloneProperties(this);
        result._mergeProperties(other);

        try {
            const common = new oc.BRepAlgoAPI_Common_3(
                this._shape,
                other._shape,
                new oc.Message_ProgressRange_1()
            );
            common.Build(new oc.Message_ProgressRange_1());

            if (common.IsDone()) {
                result._shape = common.Shape();
                if (!result._shape || result._shape.IsNull()) {
                    cadError('intersect', 'Intersection succeeded but result shape is null');
                    result._shape = this._shape;
                }
            } else {
                cadError('intersect', 'Intersection operation failed (IsDone=false)');
                result._shape = this._shape;
            }
            common.delete();
        } catch (e) {
            cadError('intersect', 'Exception during intersection', e);
            result._shape = this._shape;
        }

        return result;
    }

    /**
     * Translate the shape
     * Preserves all properties
     */
    translate(x, y, z) {
        if (!this._shape) {
            cadError('translate', 'Cannot translate: no shape exists');
            return this;
        }

        // Validate inputs
        if (typeof x !== 'number' || typeof y !== 'number' || typeof z !== 'number') {
            cadError('translate', `Invalid translation values: (${x}, ${y}, ${z})`);
            return this;
        }

        const result = new Workplane(this._plane);
        result._cloneProperties(this);

        try {
            const transform = new oc.gp_Trsf_1();
            transform.SetTranslation_1(new oc.gp_Vec_4(x, y, z));

            const builder = new oc.BRepBuilderAPI_Transform_2(this._shape, transform, true);
            result._shape = builder.Shape();

            if (!result._shape || result._shape.IsNull()) {
                cadError('translate', 'Transform succeeded but result shape is null');
                result._shape = this._shape;
            }

            builder.delete();
            transform.delete();
        } catch (e) {
            cadError('translate', 'Exception during translation', e);
            result._shape = this._shape;
        }

        return result;
    }

    /**
     * Rotate the shape around an axis
     * Preserves all properties
     */
    rotate(axisX, axisY, axisZ, angleDegrees) {
        if (!this._shape) {
            cadError('rotate', 'Cannot rotate: no shape exists');
            return this;
        }

        // Validate inputs
        if (typeof axisX !== 'number' || typeof axisY !== 'number' || typeof axisZ !== 'number') {
            cadError('rotate', `Invalid axis values: (${axisX}, ${axisY}, ${axisZ})`);
            return this;
        }
        if (typeof angleDegrees !== 'number') {
            cadError('rotate', `Invalid angle: ${angleDegrees}`);
            return this;
        }

        // Check for zero-length axis
        const axisLength = Math.sqrt(axisX*axisX + axisY*axisY + axisZ*axisZ);
        if (axisLength < 1e-10) {
            cadError('rotate', 'Axis cannot be zero-length');
            return this;
        }

        const result = new Workplane(this._plane);
        result._cloneProperties(this);

        try {
            const axis = new oc.gp_Ax1_2(
                new oc.gp_Pnt_1(),
                new oc.gp_Dir_4(axisX, axisY, axisZ)
            );
            const transform = new oc.gp_Trsf_1();
            transform.SetRotation_1(axis, angleDegrees * Math.PI / 180);

            const builder = new oc.BRepBuilderAPI_Transform_2(this._shape, transform, true);
            result._shape = builder.Shape();

            if (!result._shape || result._shape.IsNull()) {
                cadError('rotate', 'Transform succeeded but result shape is null');
                result._shape = this._shape;
            }

            builder.delete();
            transform.delete();
            axis.delete();
        } catch (e) {
            cadError('rotate', 'Exception during rotation', e);
            result._shape = this._shape;
        }

        return result;
    }

    /**
     * Get extent of shape along all axes
     */
    _getShapeExtent() {
        if (!this._shape) return 0;

        const bbox = new oc.Bnd_Box_1();
        oc.BRepBndLib.Add(this._shape, bbox, false);

        const xMin = { current: 0 }, yMin = { current: 0 }, zMin = { current: 0 };
        const xMax = { current: 0 }, yMax = { current: 0 }, zMax = { current: 0 };
        bbox.Get(xMin, yMin, zMin, xMax, yMax, zMax);
        bbox.delete();

        const dx = xMax.current - xMin.current;
        const dy = yMax.current - yMin.current;
        const dz = zMax.current - zMin.current;

        return Math.max(dx, dy, dz);
    }

    /**
     * Get the underlying OpenCascade shape
     */
    val() {
        return this._shape;
    }

    /**
     * Convert a shape to mesh data (internal helper)
     */
    _shapeToMeshData(shape, color, isModifier, linearDeflection, angularDeflection) {
        // Mesh the shape
        new oc.BRepMesh_IncrementalMesh_2(
            shape,
            linearDeflection,
            false,
            angularDeflection,
            false
        );

        const vertices = [];
        const indices = [];

        let indexOffset = 0;

        // Iterate over faces
        const faceExplorer = new oc.TopExp_Explorer_2(
            shape,
            oc.TopAbs_ShapeEnum.TopAbs_FACE,
            oc.TopAbs_ShapeEnum.TopAbs_SHAPE
        );

        while (faceExplorer.More()) {
            const face = oc.TopoDS.Face_1(faceExplorer.Current());
            const location = new oc.TopLoc_Location_1();

            const triangulation = oc.BRep_Tool.Triangulation(face, location, 0);

            if (triangulation && !triangulation.IsNull()) {
                const tri = triangulation.get();
                const transform = location.Transformation();
                const nbNodes = tri.NbNodes();
                const nbTriangles = tri.NbTriangles();

                for (let i = 1; i <= nbNodes; i++) {
                    const node = tri.Node(i);
                    const transformed = node.Transformed(transform);
                    vertices.push(transformed.X(), transformed.Y(), transformed.Z());
                }

                for (let i = 1; i <= nbTriangles; i++) {
                    const triangle = tri.Triangle(i);
                    let n1 = triangle.Value(1) - 1 + indexOffset;
                    let n2 = triangle.Value(2) - 1 + indexOffset;
                    let n3 = triangle.Value(3) - 1 + indexOffset;

                    if (face.Orientation_1() === oc.TopAbs_Orientation.TopAbs_REVERSED) {
                        [n2, n3] = [n3, n2];
                    }

                    indices.push(n1, n2, n3);
                }

                indexOffset += nbNodes;
            }

            location.delete();
            faceExplorer.Next();
        }

        faceExplorer.delete();

        return {
            vertices: new Float32Array(vertices),
            indices: new Uint32Array(indices),
            color: color,
            isModifier: isModifier
        };
    }

    /**
     * Convert shape to mesh for Three.js rendering
     * If this part has modifiers, returns an array of meshes:
     * - The main part with modifier volumes subtracted (for visibility)
     * - Each modifier as a separate mesh
     */
    toMesh(linearDeflection = 0.1, angularDeflection = 0.5) {
        if (!this._shape) return null;

        // If no modifiers, just return the simple mesh
        if (!this._modifiers || this._modifiers.length === 0) {
            return this._shapeToMeshData(this._shape, this._color, this._isModifier, linearDeflection, angularDeflection);
        }

        // We have modifiers - need to:
        // 1. Subtract modifier volumes from main shape for display
        // 2. Also render modifier volumes separately

        const meshes = [];

        // Create a cut shape: main minus all modifiers
        let displayShape = this._shape;
        for (const modifier of this._modifiers) {
            if (modifier._shape) {
                const cutOp = new oc.BRepAlgoAPI_Cut_3(displayShape, modifier._shape, new oc.Message_ProgressRange_1());
                cutOp.Build(new oc.Message_ProgressRange_1());
                if (cutOp.IsDone()) {
                    displayShape = cutOp.Shape();
                }
            }
        }

        // Mesh the cut main shape
        const mainMesh = this._shapeToMeshData(displayShape, this._color, false, linearDeflection, angularDeflection);
        if (mainMesh && mainMesh.vertices.length > 0) {
            meshes.push(mainMesh);
        }

        // Mesh each modifier separately
        for (const modifier of this._modifiers) {
            if (modifier._shape) {
                const modMesh = this._shapeToMeshData(
                    modifier._shape,
                    modifier._color || '#FFFFFF',
                    true,
                    linearDeflection,
                    angularDeflection
                );
                if (modMesh && modMesh.vertices.length > 0) {
                    meshes.push(modMesh);
                }
            }
        }

        return meshes;
    }

    /**
     * Export shape to STL format (binary)
     * Returns a Blob containing the STL file
     */
    toSTL(linearDeflection = 0.1, angularDeflection = 0.5) {
        if (!this._shape) return null;

        // Mesh the shape first
        new oc.BRepMesh_IncrementalMesh_2(
            this._shape,
            linearDeflection,
            false,
            angularDeflection,
            false
        );

        // Use StlAPI_Writer to write ASCII STL to virtual file
        const filename = '/output.stl';
        const writer = new oc.StlAPI_Writer();

        // Write ASCII STL (more compatible)
        writer.ASCIIMode = true;

        const success = writer.Write(this._shape, filename, new oc.Message_ProgressRange_1());
        writer.delete();

        if (!success) {
            console.error('Failed to write STL');
            return null;
        }

        // Read the file from Emscripten's virtual filesystem
        const stlContent = oc.FS.readFile(filename, { encoding: 'utf8' });

        // Clean up virtual file
        oc.FS.unlink(filename);

        // Return as Blob
        return new Blob([stlContent], { type: 'application/sla' });
    }

    /**
     * Export shape to Bambu-compatible 3MF format
     * Returns a Promise<Blob> containing the 3MF file
     */
    async to3MF(linearDeflection = 0.1, angularDeflection = 0.5) {
        if (!this._shape) return null;

        // For 3MF export, we need the ORIGINAL shape mesh (not with modifiers cut out)
        // Use the internal _shapeToMeshData method to get the original shape
        const mainMesh = this._shapeToMeshData(this._shape, this._color, false, linearDeflection, angularDeflection);
        if (!mainMesh || !mainMesh.vertices || mainMesh.vertices.length === 0) return null;

        const partData = {
            mesh: mainMesh,
            color: this._color || '#FF1493',
            name: this._meta.partName || 'Part_1',
            meta: { ...this._meta }
        };

        // Add modifiers if present
        if (this._modifiers && this._modifiers.length > 0) {
            partData.modifiers = [];
            for (let idx = 0; idx < this._modifiers.length; idx++) {
                const mod = this._modifiers[idx];
                if (mod._shape) {
                    const modMesh = this._shapeToMeshData(mod._shape, mod._color, true, linearDeflection, angularDeflection);
                    if (modMesh && modMesh.vertices && modMesh.vertices.length > 0) {
                        partData.modifiers.push({
                            mesh: modMesh,
                            color: mod._color || '#FFFFFF',
                            name: mod._meta?.partName || `Modifier_${idx + 1}`,
                            meta: { ...mod._meta }
                        });
                    }
                }
            }
        }

        return await ThreeMFExporter.generate([partData]);
    }
}

/**
 * Assembly - A collection of Workplane objects with individual colors
 * Used to display multiple parts in different colors
 */
class Assembly {
    constructor() {
        this._parts = [];
    }

    /**
     * Add a part to the assembly
     * @param {Workplane} part - A Workplane object (optionally with color set)
     */
    add(part) {
        if (part && part._shape) {
            this._parts.push(part);
        }
        return this;
    }

    /**
     * Convert all parts to mesh data for rendering
     * Returns array of mesh objects with vertices, indices, and color
     * Flattens arrays when parts have modifiers (which return multiple meshes)
     */
    toMesh(linearDeflection = 0.1, angularDeflection = 0.5) {
        const result = [];
        for (const part of this._parts) {
            const mesh = part.toMesh(linearDeflection, angularDeflection);
            if (Array.isArray(mesh)) {
                // Part has modifiers - flatten the array
                result.push(...mesh.filter(m => m != null));
            } else if (mesh) {
                result.push(mesh);
            }
        }
        return result;
    }

    /**
     * Check if this is an assembly (for type checking in editor)
     */
    get isAssembly() {
        return true;
    }

    /**
     * Export assembly to STL format
     * Combines all parts into a single compound shape for export
     * Returns a Blob containing the STL file
     */
    toSTL(linearDeflection = 0.1, angularDeflection = 0.5) {
        if (this._parts.length === 0) return null;

        // Create a compound of all shapes
        const builder = new oc.BRep_Builder();
        const compound = new oc.TopoDS_Compound();
        builder.MakeCompound(compound);

        for (const part of this._parts) {
            if (part._shape) {
                builder.Add(compound, part._shape);
            }
        }

        // Mesh the compound
        new oc.BRepMesh_IncrementalMesh_2(
            compound,
            linearDeflection,
            false,
            angularDeflection,
            false
        );

        // Use StlAPI_Writer to write ASCII STL to virtual file
        const filename = '/output.stl';
        const writer = new oc.StlAPI_Writer();
        writer.ASCIIMode = true;

        const success = writer.Write(compound, filename, new oc.Message_ProgressRange_1());
        writer.delete();

        if (!success) {
            console.error('Failed to write STL');
            return null;
        }

        // Read the file from Emscripten's virtual filesystem
        const stlContent = oc.FS.readFile(filename, { encoding: 'utf8' });

        // Clean up virtual file
        oc.FS.unlink(filename);

        // Return as Blob
        return new Blob([stlContent], { type: 'application/sla' });
    }

    /**
     * Export assembly to Bambu-compatible 3MF format
     * Each part gets its own filament slot with its assigned color
     * Parts with modifiers are grouped together in the 3MF
     * Returns a Promise<Blob> containing the 3MF file
     */
    async to3MF(linearDeflection = 0.1, angularDeflection = 0.5) {
        if (this._parts.length === 0) return null;

        const parts = [];
        for (let i = 0; i < this._parts.length; i++) {
            const part = this._parts[i];
            if (!part._shape) continue;

            // Get the ORIGINAL shape mesh (not with modifiers cut out)
            const mainMesh = part._shapeToMeshData(part._shape, part._color, false, linearDeflection, angularDeflection);
            if (!mainMesh || !mainMesh.vertices || mainMesh.vertices.length === 0) continue;

            const partData = {
                mesh: mainMesh,
                color: part._color || '#808080',
                name: part._meta?.partName || `Part_${i + 1}`,
                meta: { ...part._meta }
            };

            // Add modifiers if present
            if (part._modifiers && part._modifiers.length > 0) {
                partData.modifiers = [];
                for (let idx = 0; idx < part._modifiers.length; idx++) {
                    const mod = part._modifiers[idx];
                    if (mod._shape) {
                        const modMesh = part._shapeToMeshData(mod._shape, mod._color, true, linearDeflection, angularDeflection);
                        if (modMesh && modMesh.vertices && modMesh.vertices.length > 0) {
                            partData.modifiers.push({
                                mesh: modMesh,
                                color: mod._color || '#FFFFFF',
                                name: mod._meta?.partName || `Modifier_${idx + 1}`,
                                meta: { ...mod._meta }
                            });
                        }
                    }
                }
            }

            parts.push(partData);
        }

        if (parts.length === 0) return null;

        return await ThreeMFExporter.generate(parts);
    }
}

/**
 * Get the OpenCascade instance (for use by extension modules)
 */
function getOC() {
    return oc;
}

export { initCAD, Workplane, Assembly, Profiler, loadFont, getDefaultFont, getOC };
