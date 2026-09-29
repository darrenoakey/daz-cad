/** Plane split, placement and presentation framework for the joinery families. */
import { Workplane, Assembly, getOC } from "/static/cad.js";
import {
  localBox,
  bounds,
  volume,
  valid,
  common,
} from "/static/joinery-kernel.js";
import {
  makeDovetail,
  makeJigsaw,
  makeScarfWedge,
} from "/static/joinery-families-sliding.js";
import {
  makeSnapKey,
  makeCantilever,
  makeSnapDowel,
} from "/static/joinery-families-snaps.js";
import {
  makeButterfly,
  makeCrossKey,
  makeBayonet,
  makeBridgeClip,
} from "/static/joinery-families-locks.js";

const METHODS = [
  [
    "snap-key",
    "Double-ended snap key",
    "Replaceable flexible bridge key in paired roofed sockets.",
  ],
  [
    "butterfly-key",
    "Butterfly key",
    "Surface-accessible bow-tie spline locks both cut halves.",
  ],
  [
    "dovetail",
    "Sliding dovetail",
    "Integral dovetail rail with an open insertion corridor.",
  ],
  [
    "jigsaw",
    "Jigsaw rail",
    "Skewed interlocking rail with a rigid slide path.",
  ],
  [
    "cantilever-snap",
    "Cantilever snap",
    "Integral hook, compliant relief and rigid locating tongue.",
  ],
  [
    "snap-dowel",
    "Split snap dowel",
    "Separate split barbed locating pins in relieved bores.",
  ],
  [
    "cross-key",
    "Cross-keyed tongue",
    "Integral tongue and transverse removable locking key.",
  ],
  [
    "scarf-wedge",
    "Scarf wedge",
    "Overlapping stepped lap drawn closed by a tapered wedge.",
  ],
  [
    "bayonet",
    "Bayonet lock",
    "Spigot, entry keyways and quarter-turn retaining tracks.",
  ],
  [
    "bridge-clip",
    "Bridge clip",
    "Replaceable external clip seated in accessible opposed rails.",
  ],
].map(([id, label, description]) => ({ id, label, description }));
const EPS = 1e-5,
  finite3 = (value) =>
    Array.isArray(value) && value.length === 3 && value.every(Number.isFinite);
const add = (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]],
  mul = (a, s) => [a[0] * s, a[1] * s, a[2] * s],
  dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2],
  cross = (a, b) => [
    a[1] * b[2] - a[2] * b[1],
    a[2] * b[0] - a[0] * b[2],
    a[0] * b[1] - a[1] * b[0],
  ],
  length = (a) => Math.sqrt(dot(a, a));
const unit = (a, name) => {
  const l = length(a);
  if (!Number.isFinite(l) || l < EPS)
    throw new Error(`splitAndJoin: ${name} must be a non-zero finite vector`);
  return mul(a, 1 / l);
};
function frameFor(plane) {
  if (
    !plane ||
    !finite3(plane.origin) ||
    !finite3(plane.normal) ||
    (plane.up !== undefined && !finite3(plane.up))
  )
    throw new Error(
      "splitAndJoin: plane requires finite origin, normal, and up vectors",
    );
  const n = unit(plane.normal, "plane normal"),
    up = unit(plane.up ?? (Math.abs(n[2]) < 0.9 ? [0, 0, 1] : [0, 1, 0]), "plane up"),
    v = unit(
      add(up, mul(n, -dot(up, n))),
      "plane up (it cannot be parallel to normal)",
    ),
    u = unit(cross(v, n), "plane frame");
  return { origin: [...plane.origin], n, u, v };
}
function sourceLocalBounds(oc, source, frame) {
  const b = bounds(oc, source._shape),
    values = [[], [], []];
  for (const x of [b[0], b[3]])
    for (const y of [b[1], b[4]])
      for (const z of [b[2], b[5]]) {
        const d = [
          x - frame.origin[0],
          y - frame.origin[1],
          z - frame.origin[2],
        ];
        values[0].push(dot(d, frame.u));
        values[1].push(dot(d, frame.v));
        values[2].push(dot(d, frame.n));
      }
  return [
    Math.min(...values[0]),
    Math.min(...values[1]),
    Math.min(...values[2]),
    Math.max(...values[0]),
    Math.max(...values[1]),
    Math.max(...values[2]),
  ];
}
function verifyPlacement(oc, source, split, o) {
  for (const [u, v] of o.positions) {
    const probe = localBox(
      oc,
      o.frame,
      [u, v, 0],
      [
        o.size + 2 * o.wall,
        o.size + 2 * o.wall,
        Math.min(o.extent, o.depth * 2 + 2 * o.wall),
      ],
    );
    let total, lower, upper;
    try {
      total = common(oc, source._shape, probe);
      lower = common(oc, split.lower, probe);
      upper = common(oc, split.upper, probe);
    } catch (_) {
      throw new Error("splitAndJoin: connector placement misses material");
    }
    const expected = volume(oc, probe);
    if (
      volume(oc, total) < expected * (1 - 1e-6) ||
      volume(oc, lower) < expected * 0.025 ||
      volume(oc, upper) < expected * 0.025
    )
      throw new Error(
        "splitAndJoin: connector placement lacks anchored material on both cut halves",
      );
  }
}
function verifySeatedAssembly(oc, shapes) {
  for (let i = 0; i < shapes.length; i++) {
    for (const other of shapes.slice(i + 1)) {
      const progress = new oc.Message_ProgressRange_1();
      const operation = new oc.BRepAlgoAPI_Common_3(shapes[i], other, progress);
      try {
        // The two-shape constructor already performed the intersection.
        if (!operation.IsDone()) throw new Error('splitAndJoin: assembled collision check failed');
        const intersection = operation.Shape();
        const overlap = Math.abs(volume(oc, intersection));
        intersection.delete();
        if (overlap > 0.001) {
          throw new Error('splitAndJoin: assembled components intersect; reduce connector size or change placement');
        }
      } finally { operation.delete(); progress.delete(); }
    }
  }
}

function wrapped(source, shape, name, color) {
  const result = new Workplane(source._plane);
  result._cloneProperties(source);
  result._shape = shape;
  result._meta = { ...source._meta, partName: name };
  result._color = color || source._color;
  return result;
}
function localPosition(frame, u, v, z = 0) {
  return add(
    frame.origin,
    add(mul(frame.u, u), add(mul(frame.v, v), mul(frame.n, z))),
  );
}
function splitBody(oc, source, frame) {
  if (!source || !source._shape || !valid(oc, source._shape))
    throw new Error("splitAndJoin: source must be a valid solid Workplane");
  const b = bounds(oc, source._shape),
    diagonal = Math.hypot(b[3] - b[0], b[4] - b[1], b[5] - b[2]);
  if (diagonal < EPS) throw new Error("splitAndJoin: source bounds are empty");
  const extent = diagonal * 3 + 20;
  const negative = localBox(
      oc,
      frame,
      [0, 0, -extent / 2],
      [extent * 2, extent * 2, extent],
    ),
    positive = localBox(
      oc,
      frame,
      [0, 0, extent / 2],
      [extent * 2, extent * 2, extent],
    );
  let lower, upper;
  try {
    lower = common(oc, source._shape, negative);
    upper = common(oc, source._shape, positive);
  } catch (_) {
    throw new Error(
      "splitAndJoin: plane does not cut the source into two valid solids",
    );
  }
  const original = volume(oc, source._shape),
    total = volume(oc, lower) + volume(oc, upper);
  if (
    volume(oc, lower) < EPS ||
    volume(oc, upper) < EPS ||
    Math.abs(total - original) > Math.max(0.05, original * 1e-5)
  )
    throw new Error(
      "splitAndJoin: plane must pass through the source, not merely touch it",
    );
  return { lower, upper, extent };
}
function parseOptions(options) {
  if (!options || typeof options !== "object")
    throw new Error("splitAndJoin: options object is required");
  const method = options.method;
  if (!METHODS.some((item) => item.id === method))
    throw new Error(`splitAndJoin: unknown method '${method}'`);
  const size = options.size ?? 8,
    depth = options.depth ?? 6,
    clearance = options.clearance ?? 0.2,
    wall = options.wall ?? 1.2;
  for (const [name, value, minimum] of [
    ["size", size, 2],
    ["depth", depth, 1],
    ["clearance", clearance, 0],
    ["wall", wall, 0.5],
  ])
    if (!Number.isFinite(value) || value < minimum)
      throw new Error(
        `splitAndJoin: ${name} must be a finite number at least ${minimum}`,
      );
  if (clearance >= size / 3 || depth < wall * 1.1 || size < wall * 2.5)
    throw new Error(
      "splitAndJoin: connector size/depth/clearance leaves insufficient material for a reliable joint",
    );
  const count =
    options.count ??
    (Array.isArray(options.positions) ? options.positions.length : 1);
  if (!Number.isInteger(count) || count < 1 || count > 4)
    throw new Error("splitAndJoin: count must be an integer from 1 to 4");
  const autoPlacement = options.positions === undefined;
  let positions;
  if (options.positions !== undefined) {
    if (
      !Array.isArray(options.positions) ||
      options.positions.length !== count ||
      !options.positions.every(
        (p) => Array.isArray(p) && p.length === 2 && p.every(Number.isFinite),
      )
    )
      throw new Error(
        "splitAndJoin: positions must be count finite [u, v] coordinates",
      );
    positions = options.positions.map((p) => [...p]);
  } else
    positions = Array.from({ length: count }, (_, i) => [
      (i - (count - 1) / 2) * Math.max(size * 1.7, size + 2 * wall + clearance),
      0,
    ]);
  const seen = new Set();
  for (const [u, v] of positions) {
    const key = `${Math.round(u * 1000)},${Math.round(v * 1000)}`;
    if (seen.has(key))
      throw new Error("splitAndJoin: connector positions overlap");
    seen.add(key);
  }
  for (let i = 0; i < positions.length; i++) {
    for (const other of positions.slice(i + 1)) {
      const separation = Math.hypot(positions[i][0] - other[0], positions[i][1] - other[1]);
      if (separation < size + 2 * wall) {
        throw new Error("splitAndJoin: connector footprints overlap; increase their separation");
      }
    }
  }
  return {
    method,
    size,
    depth,
    clearance,
    wall,
    count,
    detent: options.detent ?? true,
    wedgePreload: options.wedgePreload ?? 0,
    positions,
    autoPlacement,
    frame: frameFor(options.plane),
  };
}
class JointResult extends Assembly {
  constructor(source, options, split) {
    super();
    this.source = source;
    this.method = options.method;
    this.plane = {
      origin: options.frame.origin,
      normal: options.frame.n,
      up: options.frame.v,
    };
    this.parts = [];
    this.keys = [];
    this.connectors = [];
    this.instructions = [];
    this.warnings = [
      "Geometry screening only: calibrate fit and verify supports in the target slicer before production.",
    ];
    this._split = split;
    this._printAxes = { parts: ["n", "-n"], keys: ["v"] };
  }
  toAssembly({ mode = "assembled", gap = 20 } = {}) {
    if (!["assembled", "exploded", "print"].includes(mode))
      throw new Error(
        "splitAndJoin: assembly mode must be assembled, exploded, or print",
      );
    if (!Number.isFinite(gap) || gap <= 0)
      throw new Error("splitAndJoin: assembly gap must be positive");
    const assembly = new Assembly(),
      all = [...this.parts, ...this.keys];
    if (mode === "assembled") {
      all.forEach((part) => assembly.add(part));
      return assembly;
    }
    if (mode === "exploded") {
      this.parts.forEach((part, index) =>
        assembly.add(
          part.translate(...mul(this.plane.normal, (index ? 1 : -1) * gap)),
        ),
      );
      this.keys.forEach((key, index) =>
        assembly.add(
          key.translate(
            ...add(
              mul(this.plane.up, gap * (index + 1)),
              mul(this.plane.normal, gap * 1.5),
            ),
          ),
        ),
      );
      return assembly;
    }
    const axisVector = (axis) =>
      axis === "n"
        ? this.plane.normal
        : axis === "-n"
          ? mul(this.plane.normal, -1)
          : axis === "u"
            ? cross(this.plane.up, this.plane.normal)
            : axis === "-u"
              ? mul(cross(this.plane.up, this.plane.normal), -1)
              : axis === "v"
                ? this.plane.up
                : mul(this.plane.up, -1);
    const pose = (part, axis) => {
      const a = axisVector(axis),
        z = [0, 0, 1],
        r = cross(a, z),
        l = length(r),
        angle = Math.acos(Math.max(-1, Math.min(1, dot(a, z))));
      return l < EPS
        ? dot(a, z) < 0
          ? part.rotate(1, 0, 0, 180)
          : part
        : part.rotate(r[0] / l, r[1] / l, r[2] / l, (angle * 180) / Math.PI);
    };
    let cursor = 0;
    for (let i = 0; i < all.length; i++) {
      const part = all[i],
        axis =
          i < this.parts.length
            ? this._printAxes.parts[i % this._printAxes.parts.length]
            : this._printAxes.keys[
                (i - this.parts.length) % this._printAxes.keys.length
              ],
        posed = pose(part, axis),
        b = bounds(getOC(), posed._shape),
        width = b[3] - b[0];
      assembly.add(posed.translate(cursor - b[0], -b[1], -b[2]));
      cursor += width + gap;
    }
    return assembly;
  }
}
const GENERATORS = {
  "snap-key": makeSnapKey,
  "butterfly-key": makeButterfly,
  dovetail: makeDovetail,
  jigsaw: makeJigsaw,
  "cantilever-snap": makeCantilever,
  "snap-dowel": makeSnapDowel,
  "cross-key": makeCrossKey,
  "scarf-wedge": makeScarfWedge,
  bayonet: makeBayonet,
  "bridge-clip": makeBridgeClip,
};
Workplane.prototype.splitAndJoin = function (options = {}) {
  const oc = getOC();
  if (!oc) throw new Error("splitAndJoin: OpenCascade is not initialized");
  const o = parseOptions(options),
    split = splitBody(oc, this, o.frame);
  o.extent = split.extent;
  o.localBounds = sourceLocalBounds(oc, this, o.frame);
  verifyPlacement(oc, this, split, o);
  const result = new JointResult(this, o, split);
  let lower = split.lower,
    upper = split.upper;
  const keys = [];
  for (let i = 0; i < o.positions.length; i++) {
    const place = o.positions[i],
      generator = GENERATORS[o.method];
    if (typeof generator !== "function")
      throw new Error(`splitAndJoin: ${o.method} generator is unavailable`);
    const generated = generator(oc, o.frame, place, {
      ...o,
      base: { lower, upper },
    });
    if (
      !generated ||
      !generated.lower ||
      !generated.upper ||
      !Array.isArray(generated.keys) ||
      typeof generated.note !== "string"
    )
      throw new Error(
        `splitAndJoin: ${o.method} returned an invalid family result`,
      );
    lower = generated.lower;
    upper = generated.upper;
    keys.push(...generated.keys);
    result.connectors.push({
      id: `${o.method}-${i + 1}`,
      method: o.method,
      position: {
        u: place[0],
        v: place[1],
        world: localPosition(o.frame, place[0], place[1]),
      },
      size: o.size,
      depth: o.depth,
      clearance: o.clearance,
      retention: generated.retention || o.method,
      assembly: generated.note,
      print: generated.print || null,
      printGuidance: generated.printGuidance || generated.note,
    });
    if (generated.print && Array.isArray(generated.print.parts))
      result._printAxes.parts = generated.print.parts;
    if (generated.print && Array.isArray(generated.print.keys))
      result._printAxes.keys = generated.print.keys;
    result.instructions.push(generated.note);
    if (generated.printGuidance) result.instructions.push(generated.printGuidance);
  }
  if (
    !valid(oc, lower) ||
    !valid(oc, upper) ||
    !keys.every((key) => valid(oc, key))
  )
    throw new Error(
      "splitAndJoin: generated joint failed final solid validation",
    );
  verifySeatedAssembly(oc, [lower, upper, ...keys]);
  result.parts = [
    wrapped(this, lower, `${o.method}-lower`),
    wrapped(this, upper, `${o.method}-upper`),
  ];
  result.keys = keys.map((key, index) =>
    wrapped(this, key, `${o.method}-key-${index + 1}`),
  );
  result.parts.forEach((part) => result.add(part));
  result.keys.forEach((key) => result.add(key));
  return result;
};
const Joinery = { methods: METHODS, JointResult };
if (typeof window !== "undefined") window.Joinery = Joinery;
export { Joinery, JointResult };
