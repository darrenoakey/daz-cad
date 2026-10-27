---
name: daz-cad-printability
description: Review and improve parametric daz-cad models for FDM printing. Use for printability, fillets, elephant foot, support-free geometry, snap fits, tolerances, part orientation, or printable joinery. Prefer the deterministic optimizeForPrinting API for unambiguous edge work and preserve functional mating edges.
---

# FDM printability for daz-cad

Apply this skill to the **parametric source**, not merely its exported mesh. Preserve function and design intent before chasing a universal set of dimensions. A slicer preview and a printed coupon remain necessary: printer, nozzle, material, layer height, orientation, cooling, and calibration change the answer.

## Workflow

1. Read the current model and identify bed orientation, mating/datum edges, load direction, moving fits, cosmetic faces, minimum walls, holes, overhangs, bridges, and assembly access.
2. For a single `Workplane`, use **Print for FDM** or call `optimizeForPrinting`. Keep the original source inside the generated block and read `result.printReport`.
3. List mating selectors in `preserveEdges`; never infer that every sharp edge is unwanted. A vertical edge may be a butt-joint datum, and a bed-contact chamfer may alter a required footprint.
4. Use `splitAndJoin` for oversized or support-heavy models that should become multiple parts. Choose the joint from assembly motion, available insertion/twist space, layer-direction loads, and whether a replaceable spring is preferable.
5. Make larger design changes explicitly in named, commented functions. Keep parameters near the top of the source. Explain why every changed feature exists.
6. Re-render and check a valid solid, console warnings, assembly collisions, and exported print layout. Inspect the actual slicer layer preview. Test critical fits and compliant parts with coupons.

## Deterministic API

```js
const result = body.optimizeForPrinting({
    verticalFillet: 1.0,       // mm; 0 disables this rule
    baseChamfer: 0.4,         // mm; 0 disables this rule
    preserveEdges: ['<X and <Y'] // vertical mating edges stay square
});
for (const change of result.printReport.changes) console.log(change);
for (const warning of result.printReport.warnings) console.warn(warning);
```

The operation chamfers edges at the model's minimum Z, then fillets non-preserved Z-parallel straight edges. It requires one valid solid and fails instead of silently returning the original when a requested geometric operation fails. It does **not** detect or repair every printable-design problem. Do not apply it blindly to an `Assembly`; optimize the intended solid before constructing the assembly.

## Design rule summary

### Edges, strength, and first layers

- FDM nozzles cannot make perfectly sharp internal corners. Use deliberate radii where fit or stress matters. Exterior vertical corners usually print acceptably; fillets are for stress, handling, and robust geometry, not a universal repair.
- Add a small 45-degree chamfer or radius at bed-contact perimeter edges to reduce elephant-foot interference and ease removal. Preserve a required flat footprint or datum when necessary.
- Fillet pin roots, snap roots, ribs, and internal load-bearing corners. Very large radii can fail on small adjacent faces; reduce the parameter rather than weakening validity checks.
- Avoid thick-to-thin abrupt transitions. Ribs and gussets often add stiffness with less material and less warping than thick solid bosses.

### Orientation and support-free shapes

- Choose orientation for **both** surface/support needs and mechanical loads. FDM is anisotropic; avoid bending compliant arms or critical hooks across layer boundaries.
- About 45 degrees from vertical is a starting overhang guideline, not a guarantee. Replace flat roofs with chamfers, arches, diamonds, or teardrop profiles where function permits.
- Rotate horizontal holes vertical when possible. For a horizontal hole that must remain, use a teardrop/diamond roof instead of a flat circular crown.
- Short bridges can work, but cooling, material, speed, and span matter. Split long roofs, add intermediate anchors, or redesign the underside. A cited approximately 5 mm span is conservative guidance, not a hard machine limit.
- Split complex parts to orient each region well. Provide alignment and retention; do not assume a tilted cut alone removes support.
- Keep supported cosmetic and mating surfaces accessible for removal. Inspect internal roofs and capture shoulders, not only the outside silhouette.

### Fits, holes, and assembly

- Never promise a universal clearance. Start from a measured printer/material/nozzle/profile coupon and record whether a value is per side or diametral. Existing daz-cad joinery defaults are starting values only.
- Vertical holes often print undersized. For precision, print undersize and drill/ream, or use a purchased pin/insert. Model lead-in chamfers for alignment and deburring.
- Use long engagement, tapers, lead-ins, slotted adjustment, compliant keys, or floating/fastened components to reduce sensitivity to small dimensional errors.
- Sliding dovetails need a clear insertion corridor; bayonets need twist room; snap hooks need deflection space and tool/access room. Check the entire assembly path, not just the final seated position.
- For snap fits, prefer a longer, tapered cantilever with a generous root radius and modest deflection. Keep strain mainly within layers and consider a replaceable ductile key. Material strain limits, creep, cycle count, and insertion force require testing.

### Walls, beds, and warping

- Choose wall thickness from nozzle/extrusion width and required perimeters, then verify the slicer does not leave gaps or thin extrusions. Avoid isolated thin walls and tiny pins where a standard insert is stronger.
- Large flat shrink-prone parts may need a brim, smaller contact-area strategy, ribs, relieved corners, material/temperature changes, or splitting. A base chamfer addresses flare; it does not by itself cure warping.
- Confirm every component and loose key fits the bed in print layout. Assembled touching parts are not a printable plate layout.

## Required explanation for generated source

Use names such as `addFirstLayerRelief`, `roundNonMatingVerticalEdges`, `makeTeardropHole`, or `addCompliantSnap`. Before each function, state the manufacturing problem and preserved constraint. Emit the parameter values and the number of affected edges/features. Do not hide a failed kernel operation behind an unchanged result.

## Sources reviewed

- Protolabs Network/Hubs, [How to design parts for FDM 3D printing](https://www.hubs.com/knowledge-base/how-design-parts-fdm-3d-printing/): overhangs, bridges, vertical holes/pins, elephant foot, base chamfers, orientation, splitting, anisotropy.
- Formlabs, [Designing 3D printed snap-fit enclosures](https://formlabs.com/blog/designing-3d-printed-snap-fit-enclosures/): snap families, material/strain, anisotropy, tapered hooks, curves, clearance and iteration.
- Prusa, [Elephant foot compensation](https://help.prusa3d.com/article/elephant-foot-compensation_114487): first-layer compensation and the caution against excessive values.
- PrusaSlicer, [Cut tool](https://help.prusa3d.com/article/cut-tool_1779), [BOSL2 partitions](https://github.com/BelfrySCAD/BOSL2/blob/master/partitions.scad), and [BOSL2 joiners](https://github.com/BelfrySCAD/BOSL2/blob/master/joiners.scad): splitting and connector prior art.

These sources inform design heuristics; they are not evidence that any generated model has passed physical fit, strength, or print certification.
