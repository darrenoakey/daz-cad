# Connector demonstration projects

Ten separate projects, one interesting object per connector. Open the **model selector** at the top left of daz-cad and choose a `joinery_01_…` through `joinery_10_…` project.

Every project is self-contained, uses the real `splitAndJoin` library, and begins in **exploded view** so the mating features and loose keys are easier to inspect. The two halves have contrasting colors; separate keys and clips are gold.

## The ten projects

| Project in the model selector | Object | Connector | What it demonstrates |
|---|---|---|---|
| `joinery_01_robot_chest.js` | Robot-faced storage chest | Double-ended snap key | A detachable panel on a hollow object, with the connector placed in solid wall material rather than empty storage space. |
| `joinery_02_mountain_sculpture.js` | Three-peak mountain desk sculpture | Butterfly key | A vertical seam through a sculpted profile and a separate bow-tie key inserted from its exposed face. |
| `joinery_03_cable_comb.js` | Multi-channel desk cable organizer | Sliding dovetail | An uninterrupted sliding spine beside functional cable channels, with an integral anti-backslide detent. |
| `joinery_04_arch_bridge.js` | Arched desktop bridge | Jigsaw rail | A profiled keystone joint dividing a curved arch into two printable sides. |
| `joinery_05_hex_lantern.js` | Ventilated hexagonal LED lantern housing | Cantilever snap | An integral spring connection in a thick wall of a hollow, vented object. LED-only; never use a candle. |
| `joinery_06_rocket_pencil_pot.js` | Finned rocket pencil pot | Split snap dowel | A compact replaceable pin in a reinforced sidewall, preserving the open pencil storage cavity. |
| `joinery_07_toolbox_handle.js` | Toolbox-handle prototype | Cross-keyed tongue | A transverse locking key through the bridge of a U-shaped handle. This demonstration is not load-rated. |
| `joinery_08_bridge_girder.js` | I-section bridge-girder model | Scarf wedge | A long beam split through its central web, with a tapered removable locking key. Not a structural/load-rated component. |
| `joinery_09_twist_canister.js` | Twist-lock cable/earbud canister | Bayonet | Coaxial quarter-turn assembly, annular storage, a central winding post, and unobstructed rotation. Not pressure-rated. |
| `joinery_10_picture_frame.js` | Split picture frame | External bridge clips | Two clips on opposite frame borders, instead of one clip that leaves the frame free to twist. |

## Change the view

Use the **VIEW** number in the Properties panel, or edit the `VIEW` constant in the project:

- **0 — assembled:** inspect the finished object.
- **1 — exploded:** inspect both halves and any separate keys.
- **2 — print:** obtain the library's separated print layout.

Select **VIEW = 2 before exporting a printing layout**. Exporting an exploded view intentionally exports that exploded arrangement. Use 3MF to preserve individual component names and colors; these are presentation colors, not a requirement to use multiple filaments.

`CLEARANCE` is also exposed as an editable parameter. Read the project header and Worker Console for its insertion direction, assembly sequence and print guidance. The samples deliberately keep connector material around their cut plane; moving a plane into a window or hollow region can correctly cause generation to reject the placement.

## Printing and use

These are demonstration designs, not physically certified products. Check the sliced orientation and support preview, calibrate fit with a small coupon, and choose material appropriate for flexures before printing a large object. Overall-object support requirements still depend on the chosen orientation, even when the connector itself is designed to avoid additional supports.

The lantern is for a cool LED light only. The handle and girder are display/fit prototypes, not safety-critical or load-bearing designs. The canister is not a pressure vessel or a certified food container.

## Development checks

`src/joinery_examples_test.py` compiles the exact checked-in scripts using real OpenCascade, verifies solid components, renders their meshes, checks separated bed layouts, and opens their named 3MF exports. The full UI-only acceptance test chooses and exports every project through the actual file picker. Bounded release checks still compile/render/export all ten, check that all ten are listed, and exercise the shared picker/export flow with contrasting rocket and picture-frame projects; the full walkthrough remains in `check-full` and is run before publishing this gallery. Standalone packaging is checked against the same ten source files.

Run cold browser suites detached with durable logs and an exit-status file; park the agent conversation while WASM loads and geometric checks execute. Do not hold a tool open waiting for the entire gallery.
