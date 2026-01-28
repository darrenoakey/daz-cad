// Border Demo - Test polygon offset algorithm on various shapes
// Creates a 4x4 grid of different shapes with their centers cut out

const BORDER = 3;  // Change this value to test different border widths

// Helper: Create a shape and cut out its center, leaving just a border
function cutBorder(shape, borderWidth) {
    // Get the top face and create an inset version
    const topFace = shape.faces(">Z");

    // Create a smaller version by scaling inward
    // We'll use a boolean cut with an offset shape
    const oc = getOC();

    // Get face info for offset calculation
    const faceShape = topFace._selectedFaces[0];
    const bounds = shape.getBounds();
    const height = bounds.zMax - bounds.zMin;

    // Create the inner shape by offsetting the boundary
    const outerWire = oc.BRepTools.OuterWire(faceShape);

    // Get vertices in order using WireExplorer
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

    if (vertices.length < 3) {
        // Probably a circle - handle separately
        const edgeExp = new oc.TopExp_Explorer_2(outerWire, oc.TopAbs_ShapeEnum.TopAbs_EDGE, oc.TopAbs_ShapeEnum.TopAbs_SHAPE);
        if (edgeExp.More()) {
            const edge = oc.TopoDS.Edge_1(edgeExp.Current());
            const curve = new oc.BRepAdaptor_Curve_2(edge);
            if (curve.GetType() === oc.GeomAbs_CurveType.GeomAbs_Circle) {
                const circle = curve.Circle();
                const radius = circle.Radius();
                const innerRadius = radius - borderWidth;
                if (innerRadius > 0.1) {
                    const innerCyl = new Workplane("XY").cylinder(innerRadius, height + 2).translate(0, 0, -1);
                    return shape.cut(innerCyl);
                }
            }
            curve.delete();
        }
        edgeExp.delete();
        return shape; // Can't offset, return original
    }

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

    // Build inner polygon as a cutter
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

    if (!wireBuilder.IsDone()) {
        return shape;
    }

    const innerWire = wireBuilder.Wire();
    const innerFace = new oc.BRepBuilderAPI_MakeFace_15(innerWire, true);
    if (!innerFace.IsDone()) {
        return shape;
    }

    // Extrude to create cutter
    const prism = new oc.BRepPrimAPI_MakePrism_1(
        innerFace.Face(),
        new oc.gp_Vec_4(0, 0, height + 2),
        false, true
    );

    const cutterShape = prism.Shape();
    const trsf = new oc.gp_Trsf_1();
    trsf.SetTranslation_1(new oc.gp_Vec_4(0, 0, -1));
    const movedCutter = cutterShape.Moved(new oc.TopLoc_Location_2(trsf), false);

    // Cut
    const cutOp = new oc.BRepAlgoAPI_Cut_3(shape._shape, movedCutter, new oc.Message_ProgressRange_1());
    if (!cutOp.IsDone()) {
        return shape;
    }

    const result = new Workplane("XY");
    result._shape = cutOp.Shape();
    return result;
}

// Create 16 different shapes
const shapes = [];
const SIZE = 20;  // Base size for shapes
const HEIGHT = 4;
const SPACING = 30;

// Row 1: Basic polygons
shapes.push({ name: "Circle", shape: new Workplane("XY").cylinder(SIZE/2, HEIGHT) });
shapes.push({ name: "Square", shape: new Workplane("XY").box(SIZE, SIZE, HEIGHT) });
shapes.push({ name: "Hexagon", shape: new Workplane("XY").polygonPrism(6, SIZE, HEIGHT) });
shapes.push({ name: "Triangle", shape: new Workplane("XY").polygonPrism(3, SIZE, HEIGHT) });

// Row 2: More polygons
shapes.push({ name: "Pentagon", shape: new Workplane("XY").polygonPrism(5, SIZE, HEIGHT) });
shapes.push({ name: "Octagon", shape: new Workplane("XY").polygonPrism(8, SIZE, HEIGHT) });
shapes.push({ name: "Rectangle", shape: new Workplane("XY").box(SIZE * 1.5, SIZE * 0.7, HEIGHT) });
shapes.push({ name: "Diamond", shape: new Workplane("XY").polygonPrism(4, SIZE, HEIGHT).rotate(0, 0, 1, 45) });

// Row 3: More variations
shapes.push({ name: "Heptagon", shape: new Workplane("XY").polygonPrism(7, SIZE, HEIGHT) });
shapes.push({ name: "Nonagon", shape: new Workplane("XY").polygonPrism(9, SIZE, HEIGHT) });
shapes.push({ name: "Decagon", shape: new Workplane("XY").polygonPrism(10, SIZE, HEIGHT) });
shapes.push({ name: "Dodecagon", shape: new Workplane("XY").polygonPrism(12, SIZE, HEIGHT) });

// Row 4: Wide/tall rectangles and ellipse-like
shapes.push({ name: "Wide Rect", shape: new Workplane("XY").box(SIZE * 1.8, SIZE * 0.5, HEIGHT) });
shapes.push({ name: "Tall Rect", shape: new Workplane("XY").box(SIZE * 0.5, SIZE * 1.8, HEIGHT) });
shapes.push({ name: "Large Hex", shape: new Workplane("XY").polygonPrism(6, SIZE * 1.2, HEIGHT) });
shapes.push({ name: "Small Circle", shape: new Workplane("XY").cylinder(SIZE * 0.4, HEIGHT) });

// Apply border cut and arrange in grid
const assembly = new Assembly();
const colors = [
    "#e74c3c", "#3498db", "#2ecc71", "#f39c12",
    "#9b59b6", "#1abc9c", "#e67e22", "#34495e",
    "#c0392b", "#2980b9", "#27ae60", "#d35400",
    "#8e44ad", "#16a085", "#f1c40f", "#7f8c8d"
];

for (let i = 0; i < shapes.length; i++) {
    const row = Math.floor(i / 4);
    const col = i % 4;
    const x = (col - 1.5) * SPACING;
    const y = (1.5 - row) * SPACING;

    try {
        const bordered = cutBorder(shapes[i].shape, BORDER);
        const positioned = bordered.translate(x, y, 0).color(colors[i]);
        assembly.add(positioned);
    } catch (e) {
        // If border cut fails, just show original
        const positioned = shapes[i].shape.translate(x, y, 0).color(colors[i]);
        assembly.add(positioned);
    }
}

const result = assembly;
result;
