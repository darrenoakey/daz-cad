import json
from pathlib import Path
from uuid import uuid4

import pytest

EXPECTED_KEY_COUNTS = {
    "snap-key": 1,
    "butterfly-key": 1,
    "dovetail": 0,
    "jigsaw": 0,
    "cantilever-snap": 0,
    "snap-dowel": 1,
    "cross-key": 1,
    "scarf-wedge": 1,
    "bayonet": 0,
    "bridge-clip": 1,
}

@pytest.fixture(scope="session")
def joinery_page(init_page):
    # Geometry tests use the real kernel page, not three editor WASM runtimes;
    # dedicated UI tests independently exercise editor startup and controls.
    init_page.evaluate("""async () => {
        const cad = await import('/static/cad.js');
        cad.initCAD(window.oc);
        window.Workplane = cad.Workplane;
        window.Assembly = cad.Assembly;
        const {Joinery} = await import('/static/joinery.js');
        window.Joinery = Joinery;
    }""")
    return init_page


METHOD_IDS = [
    "snap-key",
    "butterfly-key",
    "dovetail",
    "jigsaw",
    "cantilever-snap",
    "snap-dowel",
    "cross-key",
    "scarf-wedge",
    "bayonet",
    "bridge-clip",
]


# ##################################################################
# test complete connector catalogue creates complementary solid joinery
# runs every public mechanism on actual OpenCascade solids and verifies solid
# validity, paired cut geometry, source immutability, and assembly modes.
def test_all_joinery_methods_create_valid_complementary_solids(joinery_page):
    result = joinery_page.evaluate(
        """(methodIds) => {
            const volume = (workplane) => {
                const props = new oc.GProp_GProps_1();
                oc.BRepGProp.VolumeProperties_1(workplane._shape, props, false, false, false);
                const mass = props.Mass();
                props.delete();
                return mass;
            };
            const validSolid = (workplane) => {
                const analyzer = new oc.BRepCheck_Analyzer(workplane._shape, true, false);
                const valid = !workplane._shape.IsNull() && analyzer.IsValid_2() && volume(workplane) > 0.001;
                analyzer.delete();
                return valid;
            };
            const overlapVolume = (first, second) => {
                const progress = new oc.Message_ProgressRange_1();
                const common = new oc.BRepAlgoAPI_Common_3(first._shape, second._shape, progress);
                    const shape = common.IsDone() ? common.Shape() : null;
                const overlap = !shape || shape.IsNull() ? 0 : volume({ _shape: shape });
                common.delete();
                progress.delete();
                return overlap;
            };
            const topology = (workplane) => {
                const count = (kind) => {
                    const explorer = new oc.TopExp_Explorer_2(workplane._shape, kind, oc.TopAbs_ShapeEnum.TopAbs_SHAPE);
                    let total = 0;
                    while (explorer.More()) { total += 1; explorer.Next(); }
                    explorer.delete();
                    return total;
                };
                return [
                    count(oc.TopAbs_ShapeEnum.TopAbs_SOLID),
                    count(oc.TopAbs_ShapeEnum.TopAbs_FACE),
                    count(oc.TopAbs_ShapeEnum.TopAbs_EDGE),
                ];
            };
            const bbox = (workplane) => {
                const box = new oc.Bnd_Box_1();
                oc.BRepBndLib.Add(workplane._shape, box, false);
                const xmin = { current: 0 }, ymin = { current: 0 }, zmin = { current: 0 };
                const xmax = { current: 0 }, ymax = { current: 0 }, zmax = { current: 0 };
                box.Get(xmin, ymin, zmin, xmax, ymax, zmax);
                box.delete();
                return [xmin.current, ymin.current, zmin.current, xmax.current, ymax.current, zmax.current];
            };
            try {
                if (!window.Joinery || typeof Workplane.prototype.splitAndJoin !== 'function') {
                    return { ok: false, error: 'Joinery API was not loaded into the browser CAD library' };
                }
                const catalogue = Joinery.methods.map(({ id }) => id);
                const rows = [];
                const failures = [];
                for (const method of methodIds) {
                    try {
                        const source = new Workplane('XY').box(60, 40, 20);
                    const sourceVolume = volume(source);
                    const sourceBounds = bbox(source);
                    const joined = source.splitAndJoin({
                        plane: { origin: [0, 0, 10], normal: [0, 0, 1], up: [0, 1, 0] },
                        method, size: 8, depth: 6, clearance: 0.2, positions: [[0, 0]], count: 1, wall: 1.2,
                    });
                    const partVolumes = joined.parts.map(volume);
                    const partBounds = joined.parts.map(bbox);
                    const metadata = joined.connectors;
                    const assembled = joined.toAssembly({ mode: 'assembled' });
                    const exploded = joined.toAssembly({ mode: 'exploded', gap: 20 });
                    const printed = joined.toAssembly({ mode: 'print', gap: 20 });
                    const separated = (first, second) => {
                        const a = bbox(first), b = bbox(second);
                        return a[3] < b[0] || b[3] < a[0] || a[4] < b[1] || b[4] < a[1] || a[5] < b[2] || b[5] < a[2];
                    };
                        rows.push({
                            method,
                            methodField: joined.method,
                            partCount: joined.parts.length,
                            keyCount: joined.keys.length,
                            connectorCount: metadata.length,
                            instructions: joined.instructions.length,
                            warningArray: Array.isArray(joined.warnings),
                            validParts: joined.parts.every(validSolid),
                            validKeys: joined.keys.every(validSolid),
                            partVolumes,
                            partBounds,
                            sourceVolume, sourceVolumeAfter: volume(source),
                            sourceBounds, sourceBoundsAfter: bbox(source),
                            pairedMetadata: metadata.every((connector) => connector && typeof connector === 'object'),
                            bothHalvesModified: partVolumes.every((partVolume) => Math.abs(partVolume - 24000) > 0.01),
                            solidSignature: [...joined.parts, ...joined.keys].map((part) => [
                                Number(volume(part).toFixed(4)), ...topology(part), ...bbox(part).map((value) => Number(value.toFixed(3))),
                            ]),
                            assemblyParts: assembled.parts?.length ?? assembled._parts?.length ?? 0,
                            explodedParts: exploded.parts?.length ?? exploded._parts?.length ?? 0,
                            printParts: printed.parts?.length ?? printed._parts?.length ?? 0,
                            printPartsSeparated: printed._parts.every((part, index) =>
                                printed._parts.slice(index + 1).every((other) => separated(part, other))),
                            assembledOverlaps: [...joined.parts, ...joined.keys].flatMap((part, index, all) =>
                                all.slice(index + 1).map((other) => overlapVolume(part, other))),
                        });
                    } catch (error) {
                        failures.push({ method, error: error.message, stack: error.stack });
                    }
                }
                return { ok: failures.length === 0, catalogue, rows, failures };
            } catch (error) {
                return { ok: false, error: error.message, stack: error.stack };
            }
        }""",
        METHOD_IDS,
    )

    report = Path(__file__).resolve().parents[1] / "output" / "testing" / f"joinery-{uuid4().hex}.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Joinery geometry report: {report}")
    assert result["ok"], json.dumps(result.get("failures", result), indent=2)
    assert result["catalogue"] == METHOD_IDS
    assert len(result["rows"]) == len(METHOD_IDS)
    signatures = {repr(row["solidSignature"]) for row in result["rows"]}
    assert len(signatures) == len(METHOD_IDS), "Connector families must create distinct solid geometry, not metadata aliases"
    for row in result["rows"]:
        assert row["methodField"] == row["method"]
        assert row["partCount"] == 2, row
        assert row["keyCount"] == EXPECTED_KEY_COUNTS[row["method"]], row
        assert row["connectorCount"] >= 1, row
        assert row["instructions"] >= 1, row
        assert row["warningArray"], row
        assert row["validParts"], row
        assert row["validKeys"], row
        assert all(signature[1] == 1 for signature in row["solidSignature"]), row
        assert all(part_volume > 0 for part_volume in row["partVolumes"]), row
        assert row["pairedMetadata"], row
        assert row["bothHalvesModified"], row
        assert row["sourceVolume"] == pytest.approx(row["sourceVolumeAfter"], abs=0.001), row
        assert row["sourceBounds"] == pytest.approx(row["sourceBoundsAfter"], abs=0.001), row
        assert row["assemblyParts"] >= 2 and row["explodedParts"] >= 2 and row["printParts"] >= 2, row
        assert row["printPartsSeparated"], row
        assert all(overlap <= 0.001 for overlap in row["assembledOverlaps"]), row
        # The split must be geometrically real: parts occupy distinct ranges on
        # opposite sides of the cut, not two references to the untouched input.
        assert row["partBounds"][0] != row["partBounds"][1], row


# ##################################################################
# test oblique cuts clearance and invalid configurations
# validates actual non-axis aligned boolean results and fail-closed option checks
# instead of accepting a mesh-count proxy for successful geometry.
def test_joinery_oblique_cut_clearance_and_validation(joinery_page):
    result = joinery_page.evaluate(
        """() => {
            const volume = (workplane) => {
                const props = new oc.GProp_GProps_1();
                oc.BRepGProp.VolumeProperties_1(workplane._shape, props, false, false, false);
                const mass = props.Mass();
                props.delete();
                return mass;
            };
            const valid = (workplane) => {
                const check = new oc.BRepCheck_Analyzer(workplane._shape, true, false);
                const result = check.IsValid_2() && volume(workplane) > 0.001;
                check.delete();
                return result;
            };
            const expectError = (options, source = new Workplane('XY').box(60, 40, 20)) => {
                try {
                    source.splitAndJoin(options);
                    return false;
                } catch (_) { return true; }
            };
            try {
                const options = {
                    plane: { origin: [0, 0, 10], normal: [1, 1, 1], up: [0, 0, 1] },
                    method: 'snap-key', size: 8, depth: 6, clearance: 0.2, count: 2, wall: 1.2,
                };
                const oblique = new Workplane('XY').box(60, 40, 20).splitAndJoin(options);
                const tight = new Workplane('XY').box(60, 40, 20).splitAndJoin({
                    ...options, plane: { origin: [0, 0, 10], normal: [0, 0, 1], up: [0, 1, 0] }, clearance: 0,
                });
                const loose = new Workplane('XY').box(60, 40, 20).splitAndJoin({
                    ...options, plane: { origin: [0, 0, 10], normal: [0, 0, 1], up: [0, 1, 0] }, clearance: 0.5,
                });
                return {
                    ok: true,
                    obliqueValid: oblique.parts.every(valid) && oblique.keys.every(valid),
                    defaultUpValid: new Workplane('XY').box(60,40,20).splitAndJoin({
                        ...options, count:1, plane:{origin:[0,0,10],normal:[0,0,1]}
                    }).parts.every(valid),
                    thickWallAutoValid: new Workplane('XY').box(80,60,40).splitAndJoin({
                        ...options, method:'dovetail', wall:3, count:2, detent:false,
                        plane:{origin:[0,0,20],normal:[0,0,1]}
                    }).parts.every(valid),
                    obliquePlane: oblique.plane,
                    obliquePartsDiffer: volume(oblique.parts[0]) !== volume(oblique.parts[1]),
                    clearanceChangesGeometry: tight.parts.some((part, index) => Math.abs(volume(part) - volume(loose.parts[index])) > 0.001)
                        || tight.keys.some((key, index) => Math.abs(volume(key) - volume(loose.keys[index])) > 0.001),
                    invalid: {
                        tooClose: expectError({ ...options, count: 2, positions: [[0, 0], [0.01, 0]] }),
                        shallowCuts: Joinery.methods.every(({id}) => expectError({
                            ...options, method:id, count:1,
                            plane:{origin:[0,0,1],normal:[0,0,1],up:[0,1,0]}
                        })),
                        zeroNormal: expectError({ ...options, plane: { ...options.plane, normal: [0, 0, 0] } }),
                        parallelUp: expectError({ ...options, plane: { ...options.plane, up: [1, 1, 1] } }),
                        noIntersection: expectError({ ...options, plane: { ...options.plane, origin: [0, 0, 1000] } }),
                        unknownMethod: expectError({ ...options, method: 'not-a-connector' }),
                        malformedPosition: expectError({ ...options, positions: [['no', 'coordinates']] }),
                        thinSource: expectError(
                            { ...options, plane: { origin: [0, 0, 0.5], normal: [0, 0, 1], up: [0, 1, 0] } },
                            new Workplane('XY').box(60, 40, 1),
                        ),
                    },
                };
            } catch (error) { return { ok: false, error: error.message, stack: error.stack }; }
        }"""
    )

    assert result["ok"], result.get("error", result)
    assert result["obliqueValid"] and result["defaultUpValid"] and result["thickWallAutoValid"], result
    assert result["obliquePartsDiffer"], result
    assert result["clearanceChangesGeometry"], result
    assert all(result["invalid"].values()), result


# ##################################################################
# test joined assembly has a real multi-part 3mf and works inside the worker
# verifies the production worker import/execution path and export bytes from the
# joined Assembly, not only main-thread geometry.
def test_joinery_worker_render_and_3mf_export(joinery_page):
    result = joinery_page.evaluate(
        """async () => {
            const worker = new Worker('/static/cad-worker.js', { type: 'module' });
            const receive = (success, failure, id) => new Promise((resolve, reject) => {
                const timer = setTimeout(() => reject(new Error(`Timed out waiting for ${success}`)), 90000);
                const listener = ({ data }) => {
                    if (id !== undefined && data.id !== undefined && data.id !== id) return;
                    if (data.type === success) { clearTimeout(timer); worker.removeEventListener('message', listener); resolve(data); }
                    if (data.type === failure || data.type === 'error') { clearTimeout(timer); worker.removeEventListener('message', listener); reject(new Error(data.error)); }
                };
                worker.addEventListener('message', listener);
            });
            const code = `
                const source = new Workplane('XY').box(60, 40, 20);
                const joined = source.splitAndJoin({ plane: { origin: [0, 0, 10], normal: [0, 0, 1], up: [0, 1, 0] }, method: 'snap-key', size: 8, depth: 6, clearance: 0.2, wall: 1.2 });
                const result = joined.toAssembly({ mode: 'print', gap: 20 });
            `;
            try {
                await receive('loaded', 'error');
                const initialized = receive('initialized', 'error', 1);
                worker.postMessage({ type: 'init', id: 1 });
                await initialized;
                const rendered = receive('renderComplete', 'renderError', 2);
                worker.postMessage({ type: 'render', code, id: 2 });
                const render = await rendered;
                const exported = receive('export3MFComplete', 'export3MFError', 3);
                worker.postMessage({ type: 'export3MF', code, id: 3 });
                const threeMf = await exported;
                const {default: JSZip} = await import('https://cdn.jsdelivr.net/npm/jszip@3.10.1/+esm');
                const zip = await JSZip.loadAsync(threeMf.buffer);
                const objects = await zip.file('3D/Objects/objects.model').async('string');
                const settings = await zip.file('Metadata/model_settings.config').async('string');
                return {
                    ok: true, meshes: render.meshData.meshes?.length ?? 0, bytes: threeMf.buffer.byteLength,
                    meshObjects: (objects.match(/<mesh>/g) || []).length,
                    lowerNamed: settings.includes('snap-key-lower'),
                    upperNamed: settings.includes('snap-key-upper'),
                    keyNamed: settings.includes('snap-key-key-1'),
                }; 
            } catch (error) { return { ok: false, error: error.message }; }
            finally { worker.terminate(); }
        }"""
    )

    assert result["ok"], result.get("error", result)
    assert result["meshes"] == 3, result
    assert result["meshObjects"] == 3, result
    assert result["lowerNamed"] and result["upperNamed"] and result["keyNamed"], result
    assert result["bytes"] > 1000, result


# Rigid mechanisms must have an insertion corridor, not merely a collision-free
# final pose. Snap flexure itself is calibrated physically; rail detents are off
# here so this test isolates the rigid swept path rather than elastic contact.
def test_joinery_rigid_insertion_paths(joinery_page):
    result = joinery_page.evaluate("""() => {
        const collision = (a,b) => {
            const progress = new oc.Message_ProgressRange_1();
            const common = new oc.BRepAlgoAPI_Common_3(a._shape,b._shape,progress);
            if (!common.IsDone()) throw new Error('Assembly collision boolean failed');
            const shape = common.Shape();
            const properties = new oc.GProp_GProps_1();
            oc.BRepGProp.VolumeProperties_1(shape,properties,false,false,false);
            const mass = Math.abs(properties.Mass());
            properties.delete();shape.delete();common.delete();progress.delete();
            return mass;
        };
        const failures = [];
        for (const method of ['butterfly-key','dovetail','jigsaw','cross-key','scarf-wedge','bridge-clip','bayonet']) {
            const joint = new Workplane('XY').box(60,40,20).splitAndJoin({
                plane:{origin:[0,0,10],normal:[0,0,1],up:[0,1,0]},
                method,size:8,depth:6,clearance:.2,wall:1.2,detent:false
            });
            const measure = (moving,fixed,phase) => {
                for (const stationary of fixed) {
                    const overlap = collision(moving,stationary);
                    if (overlap > .001) failures.push({method,phase,overlap});
                }
            };
            if (method === 'bayonet') {
                for (const distance of [8,4,0]) {
                    measure(joint.parts[0].rotate(0,0,1,-90).translate(0,0,-distance),
                        [joint.parts[1]],`axial ${distance}`);
                }
                for (const angle of [-90,-60,-30,0]) {
                    measure(joint.parts[0].rotate(0,0,1,angle),[joint.parts[1]],`twist ${angle}`);
                }
            } else if (method === 'dovetail' || method === 'jigsaw') {
                for (const distance of [45,30,15,0]) {
                    measure(joint.parts[1].translate(0,distance,0),[joint.parts[0]],`slide ${distance}`);
                }
            } else {
                for (const distance of [65,40,20,0]) {
                    const shift = method === 'cross-key' ? [-distance,0,0] : [0,-distance,0];
                    measure(joint.keys[0].translate(...shift),joint.parts,`key insertion ${distance}`);
                }
            }
        }
        return failures;
    }""")
    assert not result, json.dumps(result, indent=2)
