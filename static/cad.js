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

// Ensure OpenCascade is loaded
let oc = null;

// Error tracking for the current operation
let lastError = null;

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
        window.CAD = { oc, Workplane, Assembly, getLastError, clearLastError };
    }
}

/**
 * Helper class for generating Bambu-compatible 3MF files
 */
class ThreeMFExporter {
    /**
     * Generate 3MF file from parts array using Bambu template
     * @param {Array} parts - Array of {mesh, color, name} objects
     * @returns {Promise<Blob>} - The 3MF file as a Blob
     */
    static async generate(parts) {
        // Load the Bambu template
        const response = await fetch('/static/template.3mf');
        const templateData = await response.arrayBuffer();
        const zip = await JSZip.loadAsync(templateData);

        // Update the files we need to change:
        // 1. 3D/3dmodel.model - inject our geometry
        // 2. Metadata/model_settings.config - add our objects with extruder assignments
        // 3. Metadata/slice_info.config - add filaments with our colors
        // 4. Metadata/project_settings.config - update filament colors

        zip.file('3D/3dmodel.model', this._model(parts));
        zip.file('Metadata/model_settings.config', this._modelSettings(parts));
        zip.file('Metadata/slice_info.config', this._sliceInfo(parts));

        // Update filament colors in project_settings.config
        const projectSettingsStr = await zip.file('Metadata/project_settings.config').async('string');
        const projectSettings = JSON.parse(projectSettingsStr);

        // Set filament colors for our parts (slots 1, 2, 3, etc.)
        for (let i = 0; i < parts.length; i++) {
            const color = parts[i].color || '#808080';
            const hexColor = color.startsWith('#') ? color.toUpperCase() : `#${color.toUpperCase()}`;
            if (projectSettings.filament_colour && i < projectSettings.filament_colour.length) {
                projectSettings.filament_colour[i] = hexColor;
            }
        }

        zip.file('Metadata/project_settings.config', JSON.stringify(projectSettings, null, 4));

        return await zip.generateAsync({ type: 'blob' });
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

    static _model(parts) {
        let resources = '';
        let buildItems = '';

        // First pass: weld meshes and calculate global assembly bounding box
        const weldedMeshes = [];
        let globalMinX = Infinity, globalMinY = Infinity, globalMinZ = Infinity;
        let globalMaxX = -Infinity, globalMaxY = -Infinity, globalMaxZ = -Infinity;

        for (let i = 0; i < parts.length; i++) {
            const mesh = this._weldMesh(parts[i].mesh);
            weldedMeshes.push(mesh);

            for (let v = 0; v < mesh.vertices.length; v += 3) {
                const x = mesh.vertices[v];
                const y = mesh.vertices[v + 1];
                const z = mesh.vertices[v + 2];
                globalMinX = Math.min(globalMinX, x);
                globalMinY = Math.min(globalMinY, y);
                globalMinZ = Math.min(globalMinZ, z);
                globalMaxX = Math.max(globalMaxX, x);
                globalMaxY = Math.max(globalMaxY, y);
                globalMaxZ = Math.max(globalMaxZ, z);
            }
        }

        // Calculate transform to center assembly on plate (128, 128) and put bottom at Z=0
        const assemblyCenterX = (globalMinX + globalMaxX) / 2;
        const assemblyCenterY = (globalMinY + globalMaxY) / 2;
        const plateCenter = 128; // Bambu plate center

        const offsetX = plateCenter - assemblyCenterX;
        const offsetY = plateCenter - assemblyCenterY;
        const offsetZ = -globalMinZ; // Move bottom to Z=0

        // Second pass: generate XML with transforms
        for (let i = 0; i < parts.length; i++) {
            const id = i + 1;
            const mesh = weldedMeshes[i];

            let verticesXml = '';
            for (let v = 0; v < mesh.vertices.length; v += 3) {
                verticesXml += `   <vertex x="${mesh.vertices[v].toFixed(6)}" y="${mesh.vertices[v + 1].toFixed(6)}" z="${mesh.vertices[v + 2].toFixed(6)}"/>\n`;
            }

            let trianglesXml = '';
            for (let t = 0; t < mesh.indices.length; t += 3) {
                trianglesXml += `   <triangle v1="${mesh.indices[t]}" v2="${mesh.indices[t + 1]}" v3="${mesh.indices[t + 2]}"/>\n`;
            }

            resources += `  <object id="${id}" type="model">
   <mesh>
    <vertices>
${verticesXml}    </vertices>
    <triangles>
${trianglesXml}    </triangles>
   </mesh>
  </object>\n`;

            // Add transform to center on plate: identity rotation + translation
            const transform = `1 0 0 0 1 0 0 0 1 ${offsetX.toFixed(6)} ${offsetY.toFixed(6)} ${offsetZ.toFixed(6)}`;
            buildItems += `  <item objectid="${id}" transform="${transform}"/>\n`;
        }

        const now = new Date();
        const dateStr = now.toISOString().split('T')[0];

        // Use exact format from template, just inject geometry
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

    static _modelSettings(parts) {
        // Build objects list for extruder assignment
        let objects = '';
        for (let i = 0; i < parts.length; i++) {
            const id = i + 1;
            const extruder = i + 1;
            const name = parts[i].name || `Part_${id}`;
            objects += `  <object id="${id}">
   <metadata key="name" value="${name}"/>
   <metadata key="extruder" value="${extruder}"/>
  </object>\n`;
        }

        // Keep plate structure from template, add our objects
        return `<?xml version="1.0" encoding="UTF-8"?>
<config>
  <plate>
    <metadata key="plater_id" value="1"/>
    <metadata key="plater_name" value=""/>
    <metadata key="locked" value="false"/>
  </plate>
${objects}  <assemble>
  </assemble>
</config>`;
    }

    static _sliceInfo(parts) {
        // Build filament definitions with colors
        let filaments = '';
        for (let i = 0; i < parts.length; i++) {
            const id = i + 1;
            const color = parts[i].color || '#808080';
            const hexColor = color.startsWith('#') ? color.toUpperCase() : `#${color.toUpperCase()}`;
            filaments += `  <filament id="${id}">
   <metadata key="type" value="PLA"/>
   <metadata key="color" value="${hexColor}"/>
  </filament>\n`;
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
    }

    /**
     * Set the color of this workplane object
     * @param {string} hexColor - CSS hex color like "#ff0000" or "red"
     */
    color(hexColor) {
        const result = new Workplane(this._plane);
        result._shape = this._shape;
        result._selectedFaces = this._selectedFaces;
        result._selectedEdges = this._selectedEdges;
        result._selectionMode = this._selectionMode;
        result._color = hexColor;
        return result;
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
     */
    cylinder(radius, height, centered = true) {
        const result = new Workplane(this._plane);

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
     * Cut a regular pattern of polygons through the shape
     * Creates a grid of hexagons, squares, or triangles and cuts them out
     * @param options - Configuration object:
     *   - sides: 3 (triangle), 4 (square), or 6 (hexagon) - default 6
     *   - wallThickness: thickness between shapes in mm - default 0.6
     *   - border: solid border width around edges - default 2
     *   - depth: cut depth (null = through-cut) - default null
     */
    cutPattern(options = {}) {
        const {
            sides = 6,
            wallThickness = 0.6,
            border = 2,
            depth = null,
            size = null  // Polygon size (flat-to-flat). null = auto-calculate
        } = options;

        if (!this._shape) {
            cadError('cutPattern', 'Cannot cut pattern: no shape exists');
            return this;
        }

        // Validate sides
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
            // For hexagons: we want the wall thickness to be the gap between shapes
            // poly_size (flat-to-flat) is calculated to give desired wall thickness
            const sqrt3 = Math.sqrt(3);

            let polySize, d, h, rowOffset;
            // Use provided size or auto-calculate
            const autoSize = Math.min(innerLength, innerWidth) / 6;
            polySize = size || autoSize;

            if (sides === 6) {
                // For hexagons: wall_thick = d - 2*R where d is center spacing
                // R = r / cos(30) = r * 2/sqrt(3), and r = polySize/2
                // So R = polySize / sqrt(3)
                // d = 2*R + wall_thick = 2*polySize/sqrt(3) + wall_thick
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
            } else { // sides === 3
                const r = polySize / 2;
                const R = r / Math.cos(Math.PI / 3);
                d = 2 * r + wallThickness;
                h = d * sqrt3 / 2;
                rowOffset = d / 2;
            }

            // Calculate polygon circumradius (distance from center to vertex)
            // This determines how far the polygon extends from its center
            let circumRadius;
            if (sides === 6) {
                // Hexagon: R = r / cos(30°) where r = polySize/2
                circumRadius = (polySize / 2) / Math.cos(Math.PI / 6);
            } else if (sides === 4) {
                // Square: R = r * sqrt(2) where r = polySize/2
                circumRadius = (polySize / 2) * Math.sqrt(2);
            } else {
                // Triangle: R = r / cos(60°) where r = polySize/2
                circumRadius = (polySize / 2) / Math.cos(Math.PI / 3);
            }

            // Calculate grid
            const nRows = Math.max(1, Math.ceil(innerWidth / h));
            const nCols = Math.max(1, Math.ceil(innerLength / d));

            const totalSpanX = (nCols - 1) * d;
            const totalSpanY = (nRows - 1) * h;
            const xStart = centerX - totalSpanX / 2;
            const yStart = centerY - totalSpanY / 2;

            // Cut depth
            const cutDepth = depth || (thickness + 2);
            const cutZ = zMax.current + 1;

            // Effective border: the polygon edge must stay within the border
            // So the center must be at least (border + circumRadius) from the edge
            const effectiveBorder = border + circumRadius;

            // FASTEST APPROACH: ListOfShape API with SetArguments/SetTools
            // Benchmarked at 1913ms vs 4027ms for compound approach (2.1x faster)
            const toolList = new oc.TopTools_ListOfShape_1();

            let holeCount = 0;

            for (let row = 0; row < nRows; row++) {
                const y = yStart + row * h;
                const xOffset = (row % 2 === 1) ? rowOffset : 0;

                for (let col = 0; col < nCols; col++) {
                    const x = xStart + col * d + xOffset;

                    // Check if polygon EDGE (not center) is within the border
                    if (x < xMin.current + effectiveBorder || x > xMax.current - effectiveBorder ||
                        y < yMin.current + effectiveBorder || y > yMax.current - effectiveBorder) {
                        continue;
                    }

                    // Create polygon prism and translate to position
                    const prism = this.polygonPrism(sides, polySize, cutDepth);
                    if (!prism._shape) continue;

                    const transform = new oc.gp_Trsf_1();
                    transform.SetTranslation_1(new oc.gp_Vec_4(x, y, cutZ - cutDepth));
                    const loc = new oc.TopLoc_Location_2(transform);
                    const movedPrism = prism._shape.Moved(loc, false);
                    transform.delete();

                    // Add to tool list
                    toolList.Append_1(movedPrism);
                    holeCount++;
                }
            }

            if (holeCount > 0) {
                // Use ListOfShape API - fastest boolean approach
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
     */
    faces(selector = null) {
        const result = new Workplane(this._plane);
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
     * Select edges
     * If faces are selected, select edges of those faces
     * Otherwise, select all edges
     */
    edges(selector = null) {
        const result = new Workplane(this._plane);
        result._shape = this._shape;
        result._selectionMode = 'edges';
        result._selectedEdges = [];

        if (!this._shape) return result;

        const edgeSet = new Set();
        const edges = [];

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
            // Get all edges from shape
            const explorer = new oc.TopExp_Explorer_2(
                this._shape,
                oc.TopAbs_ShapeEnum.TopAbs_EDGE,
                oc.TopAbs_ShapeEnum.TopAbs_SHAPE
            );
            while (explorer.More()) {
                const edge = oc.TopoDS.Edge_1(explorer.Current());
                edges.push(edge);
                explorer.Next();
            }
            explorer.delete();
        }

        result._selectedEdges = edges;
        return result;
    }

    /**
     * Create a hole through the shape along Z axis at XY center
     */
    hole(diameter, depth = null) {
        if (!this._shape) {
            cadError('hole', 'Cannot create hole: no shape exists');
            return this;
        }

        const result = new Workplane(this._plane);

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
     * Convert shape to mesh for Three.js rendering
     */
    toMesh(linearDeflection = 0.1, angularDeflection = 0.5) {
        if (!this._shape) return null;

        // Mesh the shape
        new oc.BRepMesh_IncrementalMesh_2(
            this._shape,
            linearDeflection,
            false,
            angularDeflection,
            false
        );

        const vertices = [];
        const indices = [];
        const normals = [];

        let indexOffset = 0;

        // Iterate over faces
        const faceExplorer = new oc.TopExp_Explorer_2(
            this._shape,
            oc.TopAbs_ShapeEnum.TopAbs_FACE,
            oc.TopAbs_ShapeEnum.TopAbs_SHAPE
        );

        while (faceExplorer.More()) {
            const face = oc.TopoDS.Face_1(faceExplorer.Current());
            const location = new oc.TopLoc_Location_1();

            // Get triangulation - BRep_Tool.Triangulation takes (face, location, meshPurpose)
            // Third arg is Poly_MeshPurpose, use 0 for default (Poly_MeshPurpose_NONE)
            const triangulation = oc.BRep_Tool.Triangulation(face, location, 0);

            if (triangulation && !triangulation.IsNull()) {
                const tri = triangulation.get();
                const transform = location.Transformation();
                const nbNodes = tri.NbNodes();
                const nbTriangles = tri.NbTriangles();

                // Get vertices
                for (let i = 1; i <= nbNodes; i++) {
                    const node = tri.Node(i);
                    const transformed = node.Transformed(transform);
                    vertices.push(transformed.X(), transformed.Y(), transformed.Z());
                }

                // Get triangles
                for (let i = 1; i <= nbTriangles; i++) {
                    const triangle = tri.Triangle(i);
                    let n1 = triangle.Value(1) - 1 + indexOffset;
                    let n2 = triangle.Value(2) - 1 + indexOffset;
                    let n3 = triangle.Value(3) - 1 + indexOffset;

                    // Check face orientation
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
            color: this._color
        };
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

        const mesh = this.toMesh(linearDeflection, angularDeflection);
        if (!mesh) return null;

        const parts = [{
            mesh: mesh,
            color: this._color || '#FF1493', // default pink
            name: 'Part_1'
        }];

        return await ThreeMFExporter.generate(parts);
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
     */
    toMesh(linearDeflection = 0.1, angularDeflection = 0.5) {
        return this._parts.map(part => part.toMesh(linearDeflection, angularDeflection));
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
     * Returns a Promise<Blob> containing the 3MF file
     */
    async to3MF(linearDeflection = 0.1, angularDeflection = 0.5) {
        if (this._parts.length === 0) return null;

        const parts = [];
        for (let i = 0; i < this._parts.length; i++) {
            const part = this._parts[i];
            const mesh = part.toMesh(linearDeflection, angularDeflection);
            if (mesh) {
                parts.push({
                    mesh: mesh,
                    color: part._color || '#808080', // default grey
                    name: `Part_${i + 1}`
                });
            }
        }

        if (parts.length === 0) return null;

        return await ThreeMFExporter.generate(parts);
    }
}

export { initCAD, Workplane, Assembly };
