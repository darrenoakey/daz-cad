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

/**
 * Initialize the CAD library with an OpenCascade instance
 */
function initCAD(openCascadeInstance) {
    oc = openCascadeInstance;
    window.Workplane = Workplane;
    window.Assembly = Assembly;
    window.CAD = { oc, Workplane, Assembly };
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

        return result;
    }

    /**
     * Create a cylinder - centered on XY, sitting on Z=0 by default
     */
    cylinder(radius, height, centered = true) {
        const result = new Workplane(this._plane);

        // Use simple constructor - creates cylinder at origin along Z axis
        const cyl = new oc.BRepPrimAPI_MakeCylinder_1(radius, height);
        result._shape = cyl.Shape();
        cyl.delete();

        return result;
    }

    /**
     * Create a sphere
     */
    sphere(radius) {
        const result = new Workplane(this._plane);
        const sphere = new oc.BRepPrimAPI_MakeSphere_1(radius);
        result._shape = sphere.Shape();
        sphere.delete();
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
        if (!this._shape) return this;

        const result = new Workplane(this._plane);
        const radius = diameter / 2;

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
        } else {
            result._shape = this._shape;
        }
        cut.delete();

        return result;
    }

    /**
     * Apply chamfer to selected edges
     * Uses BRepFilletAPI_MakeChamfer
     */
    chamfer(distance) {
        if (!this._shape) return this;

        const result = new Workplane(this._plane);

        // Try different constructor patterns
        let chamferBuilder;
        if (typeof oc.BRepFilletAPI_MakeChamfer === 'function') {
            chamferBuilder = new oc.BRepFilletAPI_MakeChamfer(this._shape);
        } else if (typeof oc.BRepFilletAPI_MakeChamfer_1 === 'function') {
            chamferBuilder = new oc.BRepFilletAPI_MakeChamfer_1(this._shape);
        } else {
            // Fallback to fillet if chamfer not available
            console.warn('Chamfer not available, using fillet instead');
            return this.fillet(distance);
        }

        let edges = this._selectedEdges;
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
                    if (typeof chamferBuilder.Add_2 === 'function') {
                        chamferBuilder.Add_2(distance, edge);
                    } else if (typeof chamferBuilder.Add === 'function') {
                        chamferBuilder.Add(distance, edge);
                    }
                } catch (e) {
                    // Skip edges that can't be chamfered
                }
                explorer.Next();
            }
            explorer.delete();
        } else {
            for (const edge of edges) {
                try {
                    if (typeof chamferBuilder.Add_2 === 'function') {
                        chamferBuilder.Add_2(distance, edge);
                    } else if (typeof chamferBuilder.Add === 'function') {
                        chamferBuilder.Add(distance, edge);
                    }
                } catch (e) {
                    // Skip edges that can't be chamfered
                }
            }
        }

        try {
            chamferBuilder.Build(new oc.Message_ProgressRange_1());
            if (chamferBuilder.IsDone()) {
                result._shape = chamferBuilder.Shape();
            } else {
                result._shape = this._shape;
            }
        } catch (e) {
            result._shape = this._shape;
        }
        chamferBuilder.delete();

        return result;
    }

    /**
     * Apply fillet to selected edges
     */
    fillet(radius) {
        if (!this._shape) return this;

        const result = new Workplane(this._plane);

        // Try different constructor patterns
        let filletBuilder;
        try {
            if (typeof oc.BRepFilletAPI_MakeFillet === 'function') {
                filletBuilder = new oc.BRepFilletAPI_MakeFillet(this._shape);
            } else if (typeof oc.BRepFilletAPI_MakeFillet_1 === 'function') {
                // Try with just shape first
                filletBuilder = new oc.BRepFilletAPI_MakeFillet_1(this._shape);
            } else if (typeof oc.BRepFilletAPI_MakeFillet_2 === 'function') {
                filletBuilder = new oc.BRepFilletAPI_MakeFillet_2(
                    this._shape,
                    oc.ChFi3d_FilletShape.ChFi3d_Rational
                );
            }
        } catch (e) {
            // If construction fails, return unchanged shape
            result._shape = this._shape;
            return result;
        }

        if (!filletBuilder) {
            result._shape = this._shape;
            return result;
        }

        let edges = this._selectedEdges;
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
                    if (typeof filletBuilder.Add_2 === 'function') {
                        filletBuilder.Add_2(radius, edge);
                    } else if (typeof filletBuilder.Add === 'function') {
                        filletBuilder.Add(radius, edge);
                    }
                } catch (e) {
                    // Skip edges that can't be filleted
                }
                explorer.Next();
            }
            explorer.delete();
        } else {
            for (const edge of edges) {
                try {
                    if (typeof filletBuilder.Add_2 === 'function') {
                        filletBuilder.Add_2(radius, edge);
                    } else if (typeof filletBuilder.Add === 'function') {
                        filletBuilder.Add(radius, edge);
                    }
                } catch (e) {
                    // Skip edges that can't be filleted
                }
            }
        }

        try {
            filletBuilder.Build(new oc.Message_ProgressRange_1());
            if (filletBuilder.IsDone()) {
                result._shape = filletBuilder.Shape();
            } else {
                result._shape = this._shape;
            }
        } catch (e) {
            result._shape = this._shape;
        }
        filletBuilder.delete();

        return result;
    }

    /**
     * Boolean union with another shape
     */
    union(other) {
        if (!this._shape || !other._shape) return this;

        const result = new Workplane(this._plane);
        const fuse = new oc.BRepAlgoAPI_Fuse_3(
            this._shape,
            other._shape,
            new oc.Message_ProgressRange_1()
        );
        fuse.Build(new oc.Message_ProgressRange_1());
        result._shape = fuse.Shape();
        fuse.delete();
        return result;
    }

    /**
     * Boolean cut (subtract another shape)
     */
    cut(other) {
        if (!this._shape || !other._shape) return this;

        const result = new Workplane(this._plane);
        const cut = new oc.BRepAlgoAPI_Cut_3(
            this._shape,
            other._shape,
            new oc.Message_ProgressRange_1()
        );
        cut.Build(new oc.Message_ProgressRange_1());
        result._shape = cut.Shape();
        cut.delete();
        return result;
    }

    /**
     * Boolean intersection
     */
    intersect(other) {
        if (!this._shape || !other._shape) return this;

        const result = new Workplane(this._plane);
        const common = new oc.BRepAlgoAPI_Common_3(
            this._shape,
            other._shape,
            new oc.Message_ProgressRange_1()
        );
        common.Build(new oc.Message_ProgressRange_1());
        result._shape = common.Shape();
        common.delete();
        return result;
    }

    /**
     * Translate the shape
     */
    translate(x, y, z) {
        if (!this._shape) return this;

        const result = new Workplane(this._plane);
        const transform = new oc.gp_Trsf_1();
        transform.SetTranslation_1(new oc.gp_Vec_4(x, y, z));

        const builder = new oc.BRepBuilderAPI_Transform_2(this._shape, transform, true);
        result._shape = builder.Shape();

        builder.delete();
        transform.delete();
        return result;
    }

    /**
     * Rotate the shape around an axis
     */
    rotate(axisX, axisY, axisZ, angleDegrees) {
        if (!this._shape) return this;

        const result = new Workplane(this._plane);
        const axis = new oc.gp_Ax1_2(
            new oc.gp_Pnt_1(),
            new oc.gp_Dir_4(axisX, axisY, axisZ)
        );
        const transform = new oc.gp_Trsf_1();
        transform.SetRotation_1(axis, angleDegrees * Math.PI / 180);

        const builder = new oc.BRepBuilderAPI_Transform_2(this._shape, transform, true);
        result._shape = builder.Shape();

        builder.delete();
        transform.delete();
        axis.delete();
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
