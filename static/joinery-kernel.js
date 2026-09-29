/** Shared OpenCascade primitives for cut-plane joinery family modules. */

const EPS = 1e-5;
const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const cross = (a, b) => [
  a[1] * b[2] - a[2] * b[1],
  a[2] * b[0] - a[0] * b[2],
  a[0] * b[1] - a[1] * b[0],
];
const length = (vector) => Math.sqrt(dot(vector, vector));
const mul = (vector, scalar) => vector.map((value) => value * scalar);
const add = (a, b) => a.map((value, index) => value + b[index]);

function bounds(oc, shape) {
  const box = new oc.Bnd_Box_1();
  oc.BRepBndLib.Add(shape, box, false);
  const xmin = { current: 0 },
    ymin = { current: 0 },
    zmin = { current: 0 };
  const xmax = { current: 0 },
    ymax = { current: 0 },
    zmax = { current: 0 };
  box.Get(xmin, ymin, zmin, xmax, ymax, zmax);
  box.delete();
  return [
    xmin.current,
    ymin.current,
    zmin.current,
    xmax.current,
    ymax.current,
    zmax.current,
  ];
}

function volume(oc, shape) {
  if (!shape || shape.IsNull()) return 0;
  const properties = new oc.GProp_GProps_1();
  oc.BRepGProp.VolumeProperties_1(shape, properties, false, false, false);
  const result = properties.Mass();
  properties.delete();
  return result;
}

function solidCount(oc, shape) {
  const explorer = new oc.TopExp_Explorer_2(
    shape,
    oc.TopAbs_ShapeEnum.TopAbs_SOLID,
    oc.TopAbs_ShapeEnum.TopAbs_SHAPE,
  );
  let count = 0;
  while (explorer.More()) {
    count++;
    explorer.Next();
  }
  explorer.delete();
  return count;
}

/** Fail closed: every generated result must be one valid OpenCascade solid. */
function valid(oc, shape) {
  if (!shape || shape.IsNull()) return false;
  const mass = volume(oc, shape);
  if (!Number.isFinite(mass) || mass <= EPS || solidCount(oc, shape) !== 1) return false;
  if (typeof oc.BRepCheck_Analyzer !== "function") return false;
  const checker = new oc.BRepCheck_Analyzer(shape, true, false);
  const result = checker.IsValid_1(shape);
  checker.delete();
  return result;
}

function rotateVector(vector, axis, angle) {
  const cosine = Math.cos(angle),
    sine = Math.sin(angle);
  return add(
    add(mul(vector, cosine), mul(cross(axis, vector), sine)),
    mul(axis, dot(axis, vector) * (1 - cosine)),
  );
}

function applyRotation(oc, shape, axis, angle) {
  if (Math.abs(angle) < EPS) return shape;
  const transform = new oc.gp_Trsf_1();
  transform.SetRotation_1(
    new oc.gp_Ax1_2(new oc.gp_Pnt_1(), new oc.gp_Dir_4(...axis)),
    angle,
  );
  const builder = new oc.BRepBuilderAPI_Transform_2(shape, transform, true);
  const result = builder.Shape();
  builder.delete();
  transform.delete();
  return result;
}

/** Map local x/y/z exactly to the supplied u/v/n frame, including frame roll. */
function transformShape(oc, shape, frame) {
  let current = shape;
  const z = [0, 0, 1];
  const firstCross = cross(z, frame.n);
  const firstLength = length(firstCross);
  const cosine = Math.max(-1, Math.min(1, frame.n[2]));
  let firstAxis = [1, 0, 0];
  let firstAngle = 0;
  if (firstLength > EPS) {
    firstAxis = mul(firstCross, 1 / firstLength);
    firstAngle = Math.acos(cosine);
    current = applyRotation(oc, current, firstAxis, firstAngle);
  } else if (cosine < 0) {
    firstAngle = Math.PI;
    current = applyRotation(oc, current, firstAxis, firstAngle);
  }
  const mappedX = rotateVector([1, 0, 0], firstAxis, firstAngle);
  const roll = Math.atan2(
    dot(cross(mappedX, frame.u), frame.n),
    dot(mappedX, frame.u),
  );
  current = applyRotation(oc, current, frame.n, roll);

  const translation = new oc.gp_Trsf_1();
  translation.SetTranslation_1(new oc.gp_Vec_4(...frame.origin));
  const builder = new oc.BRepBuilderAPI_Transform_2(current, translation, true);
  current = builder.Shape();
  builder.delete();
  translation.delete();
  if (!current || current.IsNull())
    throw new Error("splitAndJoin: transform produced null geometry");
  return current;
}

function localBox(oc, frame, center, dimensions) {
  const [x, y, z] = center;
  const [dx, dy, dz] = dimensions;
  if (dx <= EPS || dy <= EPS || dz <= EPS)
    throw new Error("splitAndJoin: connector dimensions are too small");
  const maker = new oc.BRepPrimAPI_MakeBox_3(
    new oc.gp_Pnt_3(x - dx / 2, y - dy / 2, z - dz / 2),
    dx,
    dy,
    dz,
  );
  const raw = maker.Shape();
  maker.delete();
  return transformShape(oc, raw, frame);
}

function localCylinder(oc, frame, center, radius, height) {
  if (radius <= EPS || height <= EPS)
    throw new Error("splitAndJoin: connector dimensions are too small");
  const maker = new oc.BRepPrimAPI_MakeCylinder_1(radius, height);
  let raw = maker.Shape();
  maker.delete();
  const translation = new oc.gp_Trsf_1();
  translation.SetTranslation_1(
    new oc.gp_Vec_4(center[0], center[1], center[2] - height / 2),
  );
  const builder = new oc.BRepBuilderAPI_Transform_2(raw, translation, true);
  raw = builder.Shape();
  builder.delete();
  translation.delete();
  return transformShape(oc, raw, frame);
}

/** Extrude a local polygon along axis: v:[u,n], n:[u,v], u:[v,n]. */
function localPrism(oc, frame, polygon, start, end, axis = "v") {
  if (
    !Array.isArray(polygon) ||
    polygon.length < 3 ||
    !Number.isFinite(start) ||
    !Number.isFinite(end) ||
    Math.abs(end - start) <= EPS
  )
    throw new Error("splitAndJoin: invalid prism");
  const point = ([a, b]) =>
    axis === "v" ? [a, start, b] : axis === "n" ? [a, b, start] : [start, a, b];
  const vector =
    axis === "v"
      ? [0, end - start, 0]
      : axis === "n"
        ? [0, 0, end - start]
        : [end - start, 0, 0];
  const wire = new oc.BRepBuilderAPI_MakeWire_1();
  for (let index = 0; index < polygon.length; index++) {
    const edge = new oc.BRepBuilderAPI_MakeEdge_3(
      new oc.gp_Pnt_3(...point(polygon[index])),
      new oc.gp_Pnt_3(...point(polygon[(index + 1) % polygon.length])),
    );
    wire.Add_1(edge.Edge());
    edge.delete();
  }
  const madeWire = wire.Wire();
  wire.delete();
  const faceMaker = new oc.BRepBuilderAPI_MakeFace_15(madeWire, true);
  if (!faceMaker.IsDone()) {
    faceMaker.delete();
    throw new Error("splitAndJoin: prism face failed");
  }
  const face = faceMaker.Face();
  faceMaker.delete();
  const prism = new oc.BRepPrimAPI_MakePrism_1(
    face,
    new oc.gp_Vec_4(...vector),
    false,
    true,
  );
  const raw = prism.Shape();
  prism.delete();
  return transformShape(oc, raw, frame);
}

function boolean(oc, operation, first, second) {
  const Builder =
    operation === "fuse"
      ? oc.BRepAlgoAPI_Fuse_3
      : operation === "cut"
        ? oc.BRepAlgoAPI_Cut_3
        : oc.BRepAlgoAPI_Common_3;
  // OCCT's two-shape constructors perform Build themselves. Rebuilding here
  // doubles the expensive boolean without adding validation or correctness.
  const progress = new oc.Message_ProgressRange_1();
  let operationBuilder;
  let result;
  try {
    operationBuilder = new Builder(first, second, progress);
    result = operationBuilder.IsDone() ? operationBuilder.Shape() : null;
  } finally {
    if (operationBuilder) operationBuilder.delete();
    progress.delete();
  }
  if (!valid(oc, result))
    throw new Error(`splitAndJoin: ${operation} boolean failed validation`);
  return result;
}

const fuse = (oc, first, second) => boolean(oc, "fuse", first, second);
const cut = (oc, first, second) => boolean(oc, "cut", first, second);
const common = (oc, first, second) => boolean(oc, "common", first, second);

function combine(oc, shapes) {
  if (!shapes.length) throw new Error("splitAndJoin: empty connector geometry");
  return shapes
    .slice(1)
    .reduce((current, shape) => fuse(oc, current, shape), shapes[0]);
}

export {
  EPS,
  add,
  mul,
  bounds,
  volume,
  solidCount,
  valid,
  transformShape,
  localBox,
  localCylinder,
  localPrism,
  boolean,
  fuse,
  cut,
  common,
  combine,
};
