# Cut-plane joinery

Split a solid into mating printable parts with one operation. Both sides and any loose keys are generated from the same parameters, so no manual matching of holes and connectors is required.

## Quick start

Open **demo_joinery.js** from the model selector. Change `METHOD` from 0 through 9 to see every family; `VIEW` chooses `assembled`, `exploded`, or `print`.

For your own model, start with one `Workplane` result, open **Cut & Join**, position the displayed plane, choose the connector and fit dimensions, choose a view, then apply. The editor retains the original model inside a lexical wrapper and adds a parametric `splitAndJoin` call. The generated script can be saved, reopened, edited, and exported using the normal controls. An entire `Assembly` is not implicitly fused or split: select/build the intended solid first.

```js
const body = new Workplane('XY').box(60, 40, 24);
const joint = body.splitAndJoin({
    plane: {
        origin: [0, 0, 12],
        normal: [0, 0, 1],
        up: [0, 1, 0]
    },
    method: 'snap-key',
    size: 8,
    depth: 6,
    clearance: 0.2,
    wall: 1.2,
    count: 1
});
console.log(joint.instructions.join('\n'));
console.warn(joint.warnings.join('\n'));
const result = joint.toAssembly({ mode: 'print', gap: 15 });
result;
```

## Connector catalogue

| Method ID | Mechanism | Assembly/access consideration |
|---|---|---|
| `snap-key` | Separate double-ended snap bridge | Push the halves onto a replaceable key |
| `butterfly-key` | Bow-tie spline spanning the seam | Insert from an accessible edge/surface |
| `dovetail` | Mating sliding rail and channel | Leave room along the slide direction |
| `jigsaw` | Complementary interlocking profile | Slide along the profile extrusion direction |
| `cantilever-snap` | Integral compliant hooks and capture pockets | Push together; avoid layer-normal flexure stress |
| `snap-dowel` | Separate split retention pins | Push assembly; allow material around sockets |
| `cross-key` | Tongue/mortise with transverse lock | Join the body, then insert a separate locking key |
| `scarf-wedge` | Overlapping scarf with wedge retention | Engage overlap before seating the wedge |
| `bayonet` | Lug-and-track twist lock | Insert and rotate; attached bodies need rotational room |
| `bridge-clip` | Separate clip bridging both halves | Requires accessible outer edge/rebate |

`Joinery.methods` exposes the catalogue to scripts and the editor. Read the generated joint's `instructions` and `warnings` for its assembly and print requirements.

## Plane and fit

- All distances are millimetres.
- `origin` and `normal` are required three-component vectors; the normal must be nonzero. Optional `up` controls in-plane roll and must not be parallel to the normal. When omitted, a stable nonparallel world-axis reference is selected.
- The plane must pass through material, not merely touch the outside.
- `positions`, when supplied, contains connector centers as `[u, v]` in the plane's local coordinates. Automatic placement is used when positions are omitted.
- `size`, `depth`, and `wall` govern connector dimensions and surrounding material requirements. Some methods need edge access and cannot be placed like blind internal pins.
- Sliding dovetail/jigsaw joints include a spring detent by default; `detent: false` removes it when free sliding is intended.
- `wedgePreload` defaults to zero; physically calibrate any adjustment and keep the generated assembly collision-free.
- `clearance` is the mating allowance; do not confuse it with an outer seam gap or spring deflection.
- Begin with a small coupon of the same geometry, material, and print orientation. A nominal 0.2 mm clearance is a starting value, not a measured printer profile.

## Result and exports

The returned `JointResult` is an `Assembly`. It exposes `parts`, `keys`, `method`, `plane`, `connectors`, `instructions`, and `warnings`.

Use `toAssembly({mode, gap})` to choose the layout:

- `assembled`: mating components at their assembled coordinates.
- `exploded`: separated presentation for examining the connection.
- `print`: separated manufacturing layout, including loose keys.

Use the print layout for a multi-part 3MF rather than exporting touching assembled bodies. Confirm every body and key fits your bed and inspect the sliced result; this feature does not promise automatic multi-plate nesting.

## Support-free printing and strength

Connector geometry and print orientation must be considered together. An angled cutting plane alone is not proof of support-free printing. Inspect roofs, capture shoulders, hooks, track ceilings, and clip lips—not just the socket entrance.

Keep compliant elements' bending loads mainly within layers. Replaceable keys let you use a ductile material for the spring while keeping the main body stiff. Check insertion force, pull-out/shear strength, repeated use, temperature, and creep on coupons before relying on a large assembly. No physical strength certification or universal printer tolerance is implied by a valid CAD solid.

## Development verification

Run the focused real-browser suite with `./run test src/joinery_test.py` and `./run test src/joinery_ui_test.py`; the release gate includes both. Tests use real OpenCascade solids and UI-driven controls, not mock geometry.

A fresh `./run install` can spend several minutes downloading the CAD assistant SDK dependencies. Start cold installation detached with a durable log and exit-status file, then park the agent conversation until it completes; do not hold a tool or turn open waiting for the large download. The same applies to unusually long full browser suites. Release gates retain their own bounded end-to-end deadline.

## Design references

The connector families use the principles reviewed in [BOSL2 partitions](https://github.com/BelfrySCAD/BOSL2/blob/master/partitions.scad), [BOSL2 joiners](https://github.com/BelfrySCAD/BOSL2/blob/master/joiners.scad), [PrusaSlicer's Cut tool](https://help.prusa3d.com/article/cut-tool_1779), and [FDM snap-fit guidance](https://formlabs.com/blog/designing-3d-printed-snap-fit-enclosures/). These are prior art and design guidance, not a claim that a printer-specific fit or strength was physically tested.
