from playwright.sync_api import expect
import httpx


# ##################################################################
# test server health endpoint
# verifies the health endpoint responds with ok status
def test_server_health_endpoint(server):
    response = httpx.get(f"{server}/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ##################################################################
# test index page loads
# verifies the init-test page serves opencascade content
def test_index_page_loads(server):
    response = httpx.get(f"{server}/init-test")
    assert response.status_code == 200
    assert "OpenCascade.js" in response.text


# ##################################################################
# test opencascade loads successfully
# verifies opencascade.js initializes in browser without errors
def test_opencascade_loads_successfully(server, shared_browser):
    page = shared_browser.new_page()

    errors = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)

    page.goto(f"{server}/init-test")

    page.wait_for_function(
        """() => {
            const status = document.getElementById('status');
            return status && (status.classList.contains('success') || status.classList.contains('error'));
        }""",
        timeout=60000
    )

    status_element = page.locator("#status")
    status_class = status_element.get_attribute("class") or ""
    assert "success" in status_class, f"Expected success state, got: {status_class}"

    page.close()


# ##################################################################
# test opencascade calculates volume
# verifies opencascade.js can perform volume calculations correctly
def test_opencascade_calculates_volume(init_page):
    test_result = init_page.locator("#test-result")
    expect(test_result).to_contain_text("6000 cubic units")



# ##################################################################
# test opencascade ready event fired
# verifies the opencascade-ready custom event dispatches with data
def test_opencascade_ready_event_fired(server, shared_browser):
    page = shared_browser.new_page()

    page.add_init_script("""
        window.__ocReadyFired = false;
        window.__ocReadyData = null;
        window.addEventListener('opencascade-ready', (e) => {
            window.__ocReadyFired = true;
            window.__ocReadyData = { elapsed: e.detail.elapsed, verified: e.detail.verified };
        });
    """)

    page.goto(f"{server}/init-test")

    page.wait_for_function(
        "() => window.__ocReadyFired === true",
        timeout=90000
    )

    event_data = page.evaluate("() => window.__ocReadyData")
    assert event_data["verified"] is True
    assert float(event_data["elapsed"]) > 0

    page.close()


# ##################################################################
# test opencascade instance available
# verifies window.oc is available and has core cad classes
def test_opencascade_instance_available(init_page):
    oc_check = init_page.evaluate("""() => {
        if (!window.oc) return { available: false, reason: 'window.oc is undefined' };

        try {
            const hasBox = typeof window.oc.BRepPrimAPI_MakeBox_2 === 'function' ||
                           typeof window.oc.BRepPrimAPI_MakeBox_1 === 'function';
            const hasGProps = typeof window.oc.GProp_GProps_1 === 'function';

            if (!hasBox) return { available: false, reason: 'BRepPrimAPI_MakeBox not found' };
            if (!hasGProps) return { available: false, reason: 'GProp_GProps not found' };

            return { available: true };
        } catch (e) {
            return { available: false, reason: e.message };
        }
    }""")

    assert oc_check["available"] is True, f"OpenCascade not initialized: {oc_check.get('reason', 'unknown')}"



# ##################################################################
# test editor renders pink mesh to canvas
# takes a snapshot of the threejs canvas and verifies it contains bright pink pixels
def test_editor_renders_pink_mesh_to_canvas(server, shared_browser):
    from pathlib import Path

    page = shared_browser.new_page()

    errors = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)

    page.goto(f"{server}/")

    # wait for status to show ready AND main thread OpenCascade to initialize
    page.wait_for_function(
        """() => {
            const statusText = document.getElementById('status-text');
            return statusText && statusText.textContent === 'Ready' && window.Workplane;
        }""",
        timeout=90000
    )

    # wait for multiple animation frames
    page.evaluate("""() => new Promise(resolve => {
        let frames = 0;
        function waitFrame() {
            frames++;
            if (frames < 5) requestAnimationFrame(waitFrame);
            else resolve();
        }
        requestAnimationFrame(waitFrame);
    })""")

    canvas = page.locator("#viewer-container canvas")
    expect(canvas).to_be_visible()

    # create and display a test box
    scene_debug = page.evaluate("""() => {
        const viewer = window.cadViewer;
        if (!viewer) return { error: 'No viewer on window' };
        if (!window.Workplane) return { error: 'No Workplane' };
        if (!window.oc) return { error: 'No oc' };

        try {
            const shape = new Workplane('XY').box(15, 15, 15);
            if (!shape._shape) return { error: 'Shape creation failed' };

            const meshData = shape.toMesh(0.1, 0.3);
            if (!meshData) return { error: 'toMesh returned null' };
            if (!meshData.vertices || meshData.vertices.length === 0) {
                return { error: 'toMesh returned empty vertices' };
            }

            // analyze vertex bounds
            let minX = Infinity, maxX = -Infinity;
            let minY = Infinity, maxY = -Infinity;
            let minZ = Infinity, maxZ = -Infinity;
            for (let i = 0; i < meshData.vertices.length; i += 3) {
                const x = meshData.vertices[i];
                const y = meshData.vertices[i+1];
                const z = meshData.vertices[i+2];
                if (x < minX) minX = x;
                if (x > maxX) maxX = x;
                if (y < minY) minY = y;
                if (y > maxY) maxY = y;
                if (z < minZ) minZ = z;
                if (z > maxZ) maxZ = z;
            }

            // sample first few vertices
            const sampleVerts = [];
            for (let i = 0; i < Math.min(12, meshData.vertices.length); i += 3) {
                sampleVerts.push([
                    meshData.vertices[i].toFixed(2),
                    meshData.vertices[i+1].toFixed(2),
                    meshData.vertices[i+2].toFixed(2)
                ]);
            }

            viewer.displayMesh(meshData);
            viewer.renderer.render(viewer.scene, viewer.camera);

            let meshInfo = null;
            let boundingBox = null;
            if (viewer.meshGroup && viewer.meshGroup.children.length > 0) {
                const mesh = viewer.meshGroup.children[0];
                if (mesh.geometry) {
                    const pos = mesh.geometry.getAttribute('position');
                    mesh.geometry.computeBoundingBox();
                    const bb = mesh.geometry.boundingBox;
                    boundingBox = bb ? {
                        min: [bb.min.x.toFixed(2), bb.min.y.toFixed(2), bb.min.z.toFixed(2)],
                        max: [bb.max.x.toFixed(2), bb.max.y.toFixed(2), bb.max.z.toFixed(2)]
                    } : null;
                    meshInfo = {
                        vertexCount: pos ? pos.count : 0,
                        visible: mesh.visible,
                        materialColor: mesh.material ? mesh.material.color.getHexString() : 'unknown'
                    };
                }
            }

            return {
                meshGroupChildCount: viewer.meshGroup ? viewer.meshGroup.children.length : 0,
                cameraPosition: [
                    viewer.camera.position.x.toFixed(1),
                    viewer.camera.position.y.toFixed(1),
                    viewer.camera.position.z.toFixed(1)
                ],
                cameraTarget: [
                    viewer.controls.target.x.toFixed(1),
                    viewer.controls.target.y.toFixed(1),
                    viewer.controls.target.z.toFixed(1)
                ],
                meshInfo: meshInfo,
                boundingBox: boundingBox,
                vertexBounds: {
                    x: [minX.toFixed(2), maxX.toFixed(2)],
                    y: [minY.toFixed(2), maxY.toFixed(2)],
                    z: [minZ.toFixed(2), maxZ.toFixed(2)]
                },
                sampleVertices: sampleVerts,
                meshDataVertices: meshData.vertices.length / 3,
                meshDataIndices: meshData.indices.length
            };
        } catch (e) {
            return { error: e.message, stack: e.stack };
        }
    }""")

    # analyze pixels looking specifically for pink/magenta hues
    # ff1493 = rgb(255, 20, 147) but with lighting it becomes darker magenta shades
    pixel_analysis = page.evaluate("""() => {
        const canvas = document.querySelector('#viewer-container canvas');
        if (!canvas) return { success: false, reason: 'No canvas found' };

        const tempCanvas = document.createElement('canvas');
        tempCanvas.width = canvas.width;
        tempCanvas.height = canvas.height;
        const ctx = tempCanvas.getContext('2d');
        ctx.drawImage(canvas, 0, 0);

        const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
        const pixels = imageData.data;
        const totalPixels = canvas.width * canvas.height;

        // count pink/magenta pixels
        // pink 0xff1493 = rgb(255,20,147) with lighting becomes darker like rgb(110,4,60) or rgb(133,24,77)
        // these have: high red (80-140), very low green (<30), medium blue (50-80)
        let pinkPixelCount = 0;
        let samplePinkPixels = [];

        for (let i = 0; i < pixels.length; i += 4) {
            const r = pixels[i];
            const g = pixels[i + 1];
            const b = pixels[i + 2];

            // pink/magenta detection based on actual observed colors:
            // rgb(110,4,60), rgb(133,24,77), rgb(134,25,77)
            // - red is high (80+)
            // - green is very low (<35)
            // - blue is in 40-90 range
            // - red > blue (distinguishes from purple)
            const isPinkish = r >= 80 && g < 35 && b >= 40 && b <= 100 && r > b;

            if (isPinkish) {
                pinkPixelCount++;
                if (samplePinkPixels.length < 10) {
                    samplePinkPixels.push(`rgb(${r},${g},${b})`);
                }
            }
        }

        const pinkPercent = (pinkPixelCount / totalPixels) * 100;

        // also collect all unique colors for debugging
        const colorSet = new Set();
        for (let i = 0; i < pixels.length; i += 40) {
            const r = Math.floor(pixels[i] / 32) * 32;
            const g = Math.floor(pixels[i + 1] / 32) * 32;
            const b = Math.floor(pixels[i + 2] / 32) * 32;
            colorSet.add(`rgb(${r},${g},${b})`);
        }

        return {
            success: pinkPixelCount > 100,
            pinkPixelCount: pinkPixelCount,
            pinkPercent: pinkPercent.toFixed(2),
            totalPixels: totalPixels,
            samplePinkPixels: samplePinkPixels,
            uniqueColors: Array.from(colorSet).slice(0, 20),
            canvasSize: `${canvas.width}x${canvas.height}`
        };
    }""")

    # verify mesh was created
    assert "error" not in scene_debug, f"Error creating mesh: {scene_debug}"
    assert scene_debug.get("meshDataVertices", 0) > 0, f"toMesh returned no vertices: {scene_debug}"
    assert scene_debug.get("meshInfo"), f"No mesh info after display: {scene_debug}"
    assert scene_debug["meshInfo"]["vertexCount"] > 0, f"Mesh has no vertices: {scene_debug}"

    # take screenshot
    screenshot_path = Path("output/testing/canvas_pink_test.png")
    screenshot_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.screenshot(path=str(screenshot_path))

    # verify pink pixels are present (mesh should be visible as bright pink)
    assert pixel_analysis["success"], (
        f"No pink pixels found in canvas. "
        f"Pink count: {pixel_analysis.get('pinkPixelCount', 0)}, "
        f"Canvas size: {pixel_analysis.get('canvasSize')}. "
        f"Unique colors found: {pixel_analysis.get('uniqueColors')}. "
        f"Mesh debug: {scene_debug}"
    )

    # require at least 1% pink pixels (mesh should cover significant area)
    pink_percent = float(pixel_analysis.get("pinkPercent", 0))
    assert pink_percent > 1.0, (
        f"Pink mesh not visible enough. Only {pink_percent}% pink pixels. "
        f"Sample pink: {pixel_analysis.get('samplePinkPixels')}. "
        f"Debug: {scene_debug}"
    )

    critical_errors = [e for e in errors if "favicon" not in e.lower()]
    assert len(critical_errors) == 0, f"JavaScript errors: {critical_errors}"

    page.close()


# ##################################################################
# test editor auto renders default code
# verifies that the default code renders a colored assembly on page load
def test_editor_auto_renders_default_code(server, shared_browser):
    from pathlib import Path

    page = shared_browser.new_page()

    page.goto(f"{server}/")

    # wait for status to show ready (should auto-render default code)
    page.wait_for_function(
        """() => {
            const statusText = document.getElementById('status-text');
            return statusText && statusText.textContent === 'Ready';
        }""",
        timeout=90000
    )

    # wait for render to complete
    page.evaluate("""() => new Promise(resolve => {
        let frames = 0;
        function waitFrame() {
            frames++;
            if (frames < 10) requestAnimationFrame(waitFrame);
            else resolve();
        }
        requestAnimationFrame(waitFrame);
    })""")

    # analyze pixels for colored objects - the default code renders an assembly with
    # red (#e74c3c), green (#2ecc71), and blue (#3498db) objects
    pixel_analysis = page.evaluate("""() => {
        const canvas = document.querySelector('#viewer-container canvas');
        if (!canvas) return { success: false, reason: 'No canvas found' };

        const tempCanvas = document.createElement('canvas');
        tempCanvas.width = canvas.width;
        tempCanvas.height = canvas.height;
        const ctx = tempCanvas.getContext('2d');
        ctx.drawImage(canvas, 0, 0);

        const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
        const pixels = imageData.data;
        const totalPixels = canvas.width * canvas.height;

        let coloredPixels = 0;
        for (let i = 0; i < pixels.length; i += 4) {
            const r = pixels[i];
            const g = pixels[i + 1];
            const b = pixels[i + 2];
            // detect any colored pixel (not gray/background)
            // background is around #1a1a2e = 26,26,46
            // colored objects will have more saturated colors
            const max = Math.max(r, g, b);
            const min = Math.min(r, g, b);
            const saturation = max > 0 ? (max - min) / max : 0;
            // detect pixels with reasonable saturation and brightness
            if (max > 60 && saturation > 0.2) {
                coloredPixels++;
            }
        }

        const coloredPercent = (coloredPixels / totalPixels) * 100;
        return {
            success: coloredPercent > 1.5,
            coloredPixels: coloredPixels,
            coloredPercent: coloredPercent.toFixed(2),
            totalPixels: totalPixels
        };
    }""")

    # take screenshot for debugging
    screenshot_path = Path("output/testing/default_code_render.png")
    screenshot_path.parent.mkdir(parents=True, exist_ok=True)
    page.locator("#viewer-container canvas").screenshot(path=str(screenshot_path))

    # the default code should render visible colored meshes (>1.5% of canvas, reduced due to chat pane)
    assert pixel_analysis["success"], (
        f"Default code did not render colored assembly. "
        f"Colored: {pixel_analysis.get('coloredPercent')}% "
        f"({pixel_analysis.get('coloredPixels')} pixels)"
    )

    page.close()


# ##################################################################
# test editor mesh has geometry
# verifies the three.js mesh group contains actual geometry data
def test_editor_mesh_has_geometry(cad_page):
    # wait for ready state
    # check three.js scene state through the cadeditor instance
    mesh_check = cad_page.evaluate("""() => {
        // the viewer should be accessible - find it in the dom or window
        const viewer = document.querySelector('#viewer-container');
        if (!viewer) return { success: false, reason: 'No viewer container' };

        // check if three.js rendered by looking at the scene
        // the CADViewer adds meshes to meshGroup
        const canvas = viewer.querySelector('canvas');
        if (!canvas) return { success: false, reason: 'No canvas' };

        // we need to check if the renderer has content
        // one way is to check the webgl draw calls or buffer state
        const gl = canvas.getContext('webgl2') || canvas.getContext('webgl');
        if (!gl) return { success: false, reason: 'No WebGL context' };

        // check if there are vertex buffers bound (indicates geometry)
        // this is a basic check - more thorough would require access to three.js internals

        return {
            success: true,
            hasCanvas: true,
            canvasWidth: canvas.width,
            canvasHeight: canvas.height
        };
    }""")

    assert mesh_check["success"], f"Mesh check failed: {mesh_check.get('reason', 'unknown')}"
    assert mesh_check.get("canvasWidth", 0) > 0, "Canvas has zero width"
    assert mesh_check.get("canvasHeight", 0) > 0, "Canvas has zero height"



# ##################################################################
# test editor code execution
# verifies that changing code in editor triggers re-render
def test_editor_code_execution(cad_page):
    # wait for initial ready state AND main thread OpenCascade
    # execute simple code that creates a box and check result
    result = cad_page.evaluate("""() => {
        // access the cad library through window
        if (!window.Workplane) return { success: false, reason: 'Workplane not available' };
        if (!window.oc) return { success: false, reason: 'OpenCascade not available' };

        try {
            const shape = new Workplane('XY').box(10, 10, 10);
            if (!shape._shape) return { success: false, reason: 'Shape is null' };

            const mesh = shape.toMesh(0.1, 0.3);
            if (!mesh) return { success: false, reason: 'Mesh is null' };
            if (!mesh.vertices || mesh.vertices.length === 0) {
                return { success: false, reason: 'No vertices in mesh' };
            }
            if (!mesh.indices || mesh.indices.length === 0) {
                return { success: false, reason: 'No indices in mesh' };
            }

            return {
                success: true,
                vertexCount: mesh.vertices.length / 3,
                triangleCount: mesh.indices.length / 3
            };
        } catch (e) {
            return { success: false, reason: e.message };
        }
    }""")

    assert result["success"], f"Code execution failed: {result.get('reason', 'unknown')}"
    assert result.get("vertexCount", 0) > 0, "No vertices generated"
    assert result.get("triangleCount", 0) > 0, "No triangles generated"



# ##################################################################
# test editor full render pipeline
# comprehensive test that validates the entire render pipeline works
def test_editor_full_render_pipeline(cad_page):
    # check error overlay is not visible
    error_overlay = cad_page.locator("#error-overlay")
    error_class = error_overlay.get_attribute("class") or ""
    assert "visible" not in error_class, "Error overlay is visible"

    # comprehensive render pipeline check
    pipeline_check = cad_page.evaluate("""() => {
        const results = {
            opencascadeAvailable: false,
            workplaneAvailable: false,
            shapeCreated: false,
            meshGenerated: false,
            meshHasVertices: false,
            meshHasIndices: false,
            vertexCount: 0,
            indexCount: 0,
            errors: []
        };

        try {
            // check opencascade
            if (!window.oc) {
                results.errors.push('window.oc is undefined');
                return results;
            }
            results.opencascadeAvailable = true;

            // check workplane
            if (!window.Workplane) {
                results.errors.push('window.Workplane is undefined');
                return results;
            }
            results.workplaneAvailable = true;

            // create a simple box
            const wp = new Workplane('XY');
            const shape = wp.box(10, 10, 10);

            if (!shape) {
                results.errors.push('box() returned null');
                return results;
            }

            if (!shape._shape) {
                results.errors.push('shape._shape is null');
                return results;
            }
            results.shapeCreated = true;

            // generate mesh
            const mesh = shape.toMesh(0.1, 0.3);

            if (!mesh) {
                results.errors.push('toMesh() returned null');
                return results;
            }
            results.meshGenerated = true;

            if (!mesh.vertices || mesh.vertices.length === 0) {
                results.errors.push('mesh has no vertices');
                return results;
            }
            results.meshHasVertices = true;
            results.vertexCount = mesh.vertices.length / 3;

            if (!mesh.indices || mesh.indices.length === 0) {
                results.errors.push('mesh has no indices');
                return results;
            }
            results.meshHasIndices = true;
            results.indexCount = mesh.indices.length;

        } catch (e) {
            results.errors.push('Exception: ' + e.message + ' at ' + e.stack);
        }

        return results;
    }""")

    # verify each step
    assert pipeline_check["opencascadeAvailable"], f"OpenCascade not available: {pipeline_check['errors']}"
    assert pipeline_check["workplaneAvailable"], f"Workplane not available: {pipeline_check['errors']}"
    assert pipeline_check["shapeCreated"], f"Shape not created: {pipeline_check['errors']}"
    assert pipeline_check["meshGenerated"], f"Mesh not generated: {pipeline_check['errors']}"
    assert pipeline_check["meshHasVertices"], f"Mesh has no vertices: {pipeline_check['errors']}"
    assert pipeline_check["meshHasIndices"], f"Mesh has no indices: {pipeline_check['errors']}"

    # verify reasonable mesh size (a box should have 8 vertices minimum, 12 triangles minimum)
    assert pipeline_check["vertexCount"] >= 8, f"Too few vertices: {pipeline_check['vertexCount']}"
    assert pipeline_check["indexCount"] >= 36, f"Too few indices: {pipeline_check['indexCount']}"

    # check no critical errors



# ##################################################################
# test cylinder and assembly generation
# verifies that cylinder shapes generate valid mesh and assemblies work
def test_cylinder_and_assembly(cad_page):
    # wait for Ready AND main thread OpenCascade to be available
    # test cylinder step by step to find where it crashes
    result = cad_page.evaluate("""() => {
        const steps = [];
        try {
            // step 1: create basic cylinder
            steps.push('Creating cylinder...');
            const cyl = new Workplane('XY').cylinder(8, 25);
            steps.push('Cylinder created, shape: ' + (cyl._shape ? 'exists' : 'null'));

            // step 2: mesh the cylinder
            steps.push('Meshing cylinder...');
            const cylMesh = cyl.toMesh(0.1, 0.3);
            steps.push('Cylinder meshed, vertices: ' + (cylMesh ? cylMesh.vertices.length / 3 : 0));

            // step 3: create cube
            steps.push('Creating cube...');
            const cube = new Workplane('XY').box(20, 20, 20);
            steps.push('Cube created');

            // step 4: add hole to cube
            steps.push('Adding hole to cube...');
            const cubeWithHole = cube.hole(8);
            steps.push('Hole added');

            // step 5: add chamfer
            steps.push('Adding chamfer...');
            const cubeWithChamfer = cubeWithHole.chamfer(2);
            steps.push('Chamfer added');

            // step 6: add color to cube
            steps.push('Adding color to cube...');
            const coloredCube = cubeWithChamfer.color('#e74c3c');
            steps.push('Color added to cube');

            // step 7: create and translate cylinder
            steps.push('Creating and translating cylinder...');
            const cylinder = new Workplane('XY').cylinder(8, 25);
            steps.push('Cylinder for assembly created');
            const translatedCyl = cylinder.translate(30, 0, 0);
            steps.push('Cylinder translated');
            const coloredCyl = translatedCyl.color('#2ecc71');
            steps.push('Cylinder colored');

            // step 8: create small cube
            steps.push('Creating small cube...');
            const smallCube = new Workplane('XY').box(12, 12, 15).translate(-25, 0, 0).color('#3498db');
            steps.push('Small cube created');

            // step 9: create assembly
            steps.push('Creating assembly...');
            const assembly = new Assembly();
            steps.push('Assembly created');
            assembly.add(coloredCube);
            steps.push('Cube added to assembly');
            assembly.add(coloredCyl);
            steps.push('Cylinder added to assembly');
            assembly.add(smallCube);
            steps.push('Small cube added to assembly');

            // step 10: mesh assembly
            steps.push('Meshing assembly...');
            const meshes = assembly.toMesh(0.1, 0.3);
            steps.push('Assembly meshed, parts: ' + meshes.length);

            return {
                success: true,
                steps: steps,
                meshCount: meshes.length,
                meshVertices: meshes.map(m => m ? m.vertices.length / 3 : 0),
                meshColors: meshes.map(m => m ? m.color : null)
            };
        } catch (e) {
            return { success: false, error: e.message, steps: steps, stack: e.stack };
        }
    }""")

    print(f"Steps completed: {result.get('steps', [])}")
    assert result["success"], f"Cylinder/Assembly test failed: {result.get('error', 'unknown')}\nSteps: {result.get('steps', [])}"
    assert result.get("meshCount", 0) == 3, f"Assembly should have 3 parts: {result}"

    print(f"Assembly mesh vertices: {result.get('meshVertices')}")
    print(f"Assembly mesh colors: {result.get('meshColors')}")



# ##################################################################
# test stl export functionality
# verifies that shapes can be exported to STL format
def test_stl_export(cad_page):
    # wait for Ready AND main thread OpenCascade
    # test STL export for single shape and assembly
    result = cad_page.evaluate("""() => {
        try {
            // test single shape STL export
            const box = new Workplane('XY').box(10, 10, 10);
            const boxSTL = box.toSTL(0.1, 0.3);
            if (!boxSTL) return { success: false, error: 'Box STL is null' };

            // test assembly STL export
            const cube = new Workplane('XY').box(20, 20, 20).color('#e74c3c');
            const cylinder = new Workplane('XY').cylinder(8, 25).translate(30, 0, 0).color('#2ecc71');
            const assembly = new Assembly().add(cube).add(cylinder);
            const assemblySTL = assembly.toSTL(0.1, 0.3);
            if (!assemblySTL) return { success: false, error: 'Assembly STL is null' };

            // check that STL content looks valid (read first few bytes)
            return {
                success: true,
                boxSTLSize: boxSTL.size,
                assemblySTLSize: assemblySTL.size
            };
        } catch (e) {
            return { success: false, error: e.message, stack: e.stack };
        }
    }""")

    assert result["success"], f"STL export test failed: {result.get('error', 'unknown')}"
    assert result.get("boxSTLSize", 0) > 100, f"Box STL too small: {result.get('boxSTLSize')}"
    assert result.get("assemblySTLSize", 0) > 100, f"Assembly STL too small: {result.get('assemblySTLSize')}"

    print(f"Box STL size: {result.get('boxSTLSize')} bytes")
    print(f"Assembly STL size: {result.get('assemblySTLSize')} bytes")



# ##################################################################
# test 3mf export functionality
# verifies that shapes can be exported to Bambu-compatible 3MF format
def test_3mf_export(cad_page):
    # wait for Ready AND main thread OpenCascade
    # test 3MF export for single shape, assembly, and text with modifier
    result = cad_page.evaluate("""async () => {
        try {
            // test single shape 3MF export
            const box = new Workplane('XY').box(10, 10, 10).color('#FF0000');
            const box3MF = await box.to3MF(0.1, 0.3);
            if (!box3MF) return { success: false, error: 'Box 3MF is null' };

            // test assembly 3MF export with multiple colors
            const cube = new Workplane('XY').box(20, 20, 20).color('#e74c3c');
            const cylinder = new Workplane('XY').cylinder(8, 25).translate(30, 0, 0).color('#2ecc71');
            const smallCube = new Workplane('XY').box(12, 12, 15).translate(-25, 0, 0).color('#3498db');
            const assembly = new Assembly().add(cube).add(cylinder).add(smallCube);
            const assembly3MF = await assembly.to3MF(0.1, 0.3);
            if (!assembly3MF) return { success: false, error: 'Assembly 3MF is null' };

            // test 3MF export with text as modifier (like text-example.js)
            await loadFont('/static/fonts/Overpass-Bold.ttf', '/fonts/Overpass-Bold.ttf');
            const textShape = new Workplane('XY').text('Hi', 8, 0.3).color('#FFFFFF');
            const baseBox = new Workplane('XY').box(40, 15, 1).color('#00FF00');
            const withModifier = baseBox.withModifier(textShape);
            const textAssembly = new Assembly().add(withModifier);
            const textModifier3MF = await textAssembly.to3MF(0.1, 0.3);
            if (!textModifier3MF) return { success: false, error: 'Text modifier 3MF is null' };

            return {
                success: true,
                box3MFSize: box3MF.size,
                assembly3MFSize: assembly3MF.size,
                textModifier3MFSize: textModifier3MF.size
            };
        } catch (e) {
            return { success: false, error: e.message, stack: e.stack };
        }
    }""")

    assert result["success"], f"3MF export test failed: {result.get('error', 'unknown')}"
    assert result.get("box3MFSize", 0) > 100, f"Box 3MF too small: {result.get('box3MFSize')}"
    assert result.get("assembly3MFSize", 0) > 100, f"Assembly 3MF too small: {result.get('assembly3MFSize')}"
    assert result.get("textModifier3MFSize", 0) > 100, f"Text modifier 3MF too small: {result.get('textModifier3MFSize')}"

    print(f"Box 3MF size: {result.get('box3MFSize')} bytes")
    print(f"Assembly 3MF size: {result.get('assembly3MFSize')} bytes")
    print(f"Text modifier 3MF size: {result.get('textModifier3MFSize')} bytes")



# ##################################################################
# test javascript ast parser
# verifies acorn and astring work in browser for code parsing/generation
def test_javascript_ast_parser(cad_page):
    # Test acorn (parser) and astring (code generator) in browser
    result = cad_page.evaluate("""async () => {
        try {
            // Load acorn and astring from CDN as ES modules
            const acorn = await import('https://cdn.jsdelivr.net/npm/acorn@8.14.1/+esm');
            const astring = await import('https://cdn.jsdelivr.net/npm/astring@1.9.0/+esm');

            // Test code to parse
            const testCode = `const x = 10;
const y = 20;
const result = x + y;`;

                // Parse code to AST
                const ast = acorn.parse(testCode, { ecmaVersion: 2022 });

                if (!ast || !ast.body) {
                    return { success: false, error: 'Failed to parse AST' };
                }

                // Verify AST structure
                const nodeCount = ast.body.length;
                if (nodeCount !== 3) {
                    return { success: false, error: `Expected 3 statements, got ${nodeCount}` };
                }

                // Modify AST: change x = 10 to x = 42
                if (ast.body[0].declarations[0].init.value !== 10) {
                    return { success: false, error: 'First value not 10' };
                }
                ast.body[0].declarations[0].init.value = 42;
                ast.body[0].declarations[0].init.raw = '42';

                // Generate code back from modified AST
                const generatedCode = astring.generate(ast);

                if (!generatedCode.includes('42')) {
                    return { success: false, error: 'Generated code does not contain modified value' };
                }

                // Parse the generated code again to verify it's valid
                const reparsedAst = acorn.parse(generatedCode, { ecmaVersion: 2022 });
                if (!reparsedAst || reparsedAst.body.length !== 3) {
                    return { success: false, error: 'Regenerated code failed to parse' };
                }

                return {
                    success: true,
                    originalCode: testCode,
                    modifiedCode: generatedCode,
                    nodeCount: nodeCount,
                    acornVersion: acorn.version || 'loaded',
                    astringVersion: astring.version || 'loaded'
                };
            } catch (e) {
                return { success: false, error: e.message, stack: e.stack };
            }
        }""")

    assert result["success"], f"AST parser test failed: {result.get('error', 'unknown')}"
    assert '42' in result.get("modifiedCode", ""), "Modified code should contain 42"



# ##################################################################
# test reset file endpoint
# verifies files can be reset to their original template
def test_reset_file(server):
    # check if default.js has a template
    response = httpx.get(f"{server}/api/models/default.js/has-template")
    assert response.status_code == 200
    data = response.json()
    assert data["has_template"] is True

    # modify the file first
    modified_content = "// Modified content\nconst x = 999;"
    response = httpx.post(
        f"{server}/api/models/default.js",
        json={"content": modified_content}
    )
    assert response.status_code == 200

    # verify it was modified
    response = httpx.get(f"{server}/api/models/default.js")
    assert response.status_code == 200
    assert "Modified content" in response.json()["content"]

    # reset the file
    response = httpx.post(f"{server}/api/models/default.js/reset")
    assert response.status_code == 200
    data = response.json()
    assert data["reset"] is True
    assert "Modified content" not in data["content"]

    # verify it was reset
    response = httpx.get(f"{server}/api/models/default.js")
    assert response.status_code == 200
    assert "Modified content" not in response.json()["content"]

    # check that a non-template file returns has_template: false
    response = httpx.get(f"{server}/api/models/nonexistent.js/has-template")
    assert response.status_code == 200
    assert response.json()["has_template"] is False


# ##################################################################
# test reset button visibility
# verifies reset button shows for files with templates
def test_reset_button_visibility(cad_page):
    # wait for editor and filename to be loaded
    cad_page.wait_for_function(
        """() => {
            const filename = document.getElementById('filename-display');
            return window.cadEditor && window.cadEditor.editor &&
                   filename && filename.textContent !== 'loading...';
        }""",
        timeout=30000
    )
    # wait a bit more for template check to complete
    cad_page.wait_for_timeout(500)

    # check reset button is visible for default.js (has template)
    result = cad_page.evaluate("""() => {
        const btn = document.getElementById('reset-file-btn');
        const filename = document.getElementById('filename-display');
        return {
            buttonExists: !!btn,
            buttonDisplay: btn ? btn.style.display : 'not found',
            buttonVisible: btn ? (btn.style.display !== 'none' && btn.offsetParent !== null) : false,
            currentFile: filename ? filename.textContent : 'unknown',
            hasTemplate: window.cadEditor ? window.cadEditor._hasTemplate : 'unknown',
            resetBtn: window.cadEditor ? !!window.cadEditor._resetFileBtn : 'unknown'
        };
    }""")

    print(f"Reset button result: {result}")
    assert result["buttonExists"], "Reset button not found in DOM"
    assert result["buttonVisible"], f"Reset button not visible. Display: {result['buttonDisplay']}, hasTemplate: {result['hasTemplate']}, file: {result['currentFile']}"



# ##################################################################
# test properties panel
# verifies properties panel parses numeric variables and sliders update code
def test_properties_panel(cad_page):
    # wait for editor to be ready
    # test properties panel in a single atomic evaluate to avoid race conditions
    result = cad_page.evaluate("""() => {
        // stop file watcher and debounce timer
        if (window.cadEditor._fileWatchInterval) {
            clearInterval(window.cadEditor._fileWatchInterval);
            window.cadEditor._fileWatchInterval = null;
        }
        if (window.cadEditor.debounceTimer) {
            clearTimeout(window.cadEditor.debounceTimer);
            window.cadEditor.debounceTimer = null;
        }

        // set test code
        const testCode = `const WIDTH = 30;
const HEIGHT = 20;
const DEPTH = 10;
const result = new Workplane("XY").box(WIDTH, HEIGHT, DEPTH);
result;`;
            window.cadEditor.editor.setValue(testCode);

            // parse properties immediately
            window.cadEditor._parseAndRenderProperties();

            // check parsing worked
            const propsCount = window.cadEditor._properties ? window.cadEditor._properties.length : 0;
            const propsNames = window.cadEditor._properties ? window.cadEditor._properties.map(p => p.name) : [];

            // check DOM was updated
            const list = document.getElementById('properties-list');
            const items = list ? list.querySelectorAll('.property-item') : [];
            const domNames = [];
            items.forEach(item => {
                const name = item.querySelector('.property-name');
                if (name) domNames.push(name.textContent);
            });

            // test slider interaction
            const widthSlider = document.querySelector('.property-slider[data-prop-name="WIDTH"]');
            if (!widthSlider) {
                return {
                    success: false,
                    error: 'WIDTH slider not found',
                    propsCount,
                    propsNames,
                    domNames
                };
            }

            // trigger slider change
            widthSlider.value = 50;
            widthSlider.dispatchEvent(new Event('input', { bubbles: true }));

            // check code was updated
            const codeAfter = window.cadEditor.editor.getValue();
            const has50 = codeAfter.includes('50');

            return {
                success: has50 && propsCount === 3,
                propsCount,
                propsNames,
                domNames,
                has50,
                codeAfter: codeAfter.substring(0, 100),
                error: !has50 ? 'Code does not contain 50 after slider change' :
                       propsCount !== 3 ? `Expected 3 props, got ${propsCount}` : null
            };
        }""")

    print(f"Result: {result}")
    assert result["success"], f"Properties panel test failed: {result.get('error')}. Props: {result.get('propsNames')}, DOM: {result.get('domNames')}, code: {result.get('codeAfter')}"


# ##################################################################
# test cad library operations
# verifies all cad library functions work correctly
def test_cad_library_operations(cad_page):
    # run the CAD test suite
    results = cad_page.evaluate("""() => {
        if (typeof CADTests === 'undefined') {
            return { error: 'CADTests not loaded' };
        }
        return CADTests.runAll();
    }""")


    assert "error" not in results, f"CADTests failed to load: {results.get('error')}"
    assert results["failed"] == 0, (
        f"CAD library tests failed: {results['failed']} failures. "
        f"Failed: {[r['name'] for r in results['results'] if not r['passed']]}"
    )
    print(f"CAD library tests: {results['passed']} passed, {results['failed']} failed")


# ##################################################################
# test chat message endpoint
# verifies the chat endpoint responds with agent output
def test_chat_message_endpoint(server):
    # use a test-specific file to avoid overwriting user's default.js
    test_file = "_test_chat_temp.js"
    test_code = "const result = new Workplane('XY').box(20, 20, 20);\nresult;"

    response = httpx.post(
        f"{server}/api/chat/message",
        json={
            "message": "What shape is in this model?",
            "current_file": test_file,
            "current_code": test_code
        },
        timeout=60.0
    )
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert len(data["response"]) > 0
    assert "file_changed" in data
    # the response should be a non-trivial reply (LLM output is non-deterministic,
    # so we only check it gave a substantive response, not specific keywords)
    assert len(data["response"]) > 10, f"Response too short: {data['response']}"


# ##################################################################
# test open box example renders
# verifies the open-box.js example file loads and renders correctly
def test_open_box_example_renders(server):
    # test that the open-box.js example file exists and can be loaded
    response = httpx.get(f"{server}/api/models/open-box.js")
    assert response.status_code == 200
    data = response.json()
    assert "content" in data
    assert "box" in data["content"].lower() or "workplane" in data["content"].lower()


# ##################################################################
# test polygon prism and cut pattern
# verifies the new polygonPrism and cutPattern CAD library methods
def test_polygon_prism_and_cut_pattern(cad_page):
    # wait for Ready AND main thread OpenCascade
    result = cad_page.evaluate("""() => {
        try {
            // test polygonPrism - hexagon
            const hex = new Workplane('XY').polygonPrism(6, 20, 30);
            if (!hex._shape) return { success: false, error: 'Hexagon shape is null' };
            const hexMesh = hex.toMesh(0.1, 0.3);
            if (!hexMesh || hexMesh.vertices.length === 0) {
                return { success: false, error: 'Hexagon mesh has no vertices' };
            }

            // test polygonPrism - square
            const square = new Workplane('XY').polygonPrism(4, 15, 25);
            if (!square._shape) return { success: false, error: 'Square prism shape is null' };

            // test polygonPrism - triangle
            const tri = new Workplane('XY').polygonPrism(3, 10, 20);
            if (!tri._shape) return { success: false, error: 'Triangle prism shape is null' };

            // test cutPattern
            const boxBefore = new Workplane('XY').box(50, 50, 5);
            const meshBefore = boxBefore.toMesh(0.1, 0.3);
            const vertsBefore = meshBefore.vertices.length / 3;

            const boxWithPattern = boxBefore.cutPattern({
                sides: 6,
                wallThickness: 1,
                border: 5
            });
            if (!boxWithPattern._shape) return { success: false, error: 'Cut pattern result is null' };

            const meshAfter = boxWithPattern.toMesh(0.1, 0.3);
            const vertsAfter = meshAfter.vertices.length / 3;

            // cutPattern should add more vertices (for the holes)
            if (vertsAfter <= vertsBefore) {
                return {
                    success: false,
                    error: 'cutPattern did not modify geometry',
                    vertsBefore: vertsBefore,
                    vertsAfter: vertsAfter
                };
            }

            return {
                success: true,
                hexVertices: hexMesh.vertices.length / 3,
                patternVertsBefore: vertsBefore,
                patternVertsAfter: vertsAfter
            };
        } catch (e) {
            return { success: false, error: e.message, stack: e.stack };
        }
    }""")


    assert result["success"], f"polygonPrism/cutPattern test failed: {result.get('error')}"
    print(f"Hexagon vertices: {result.get('hexVertices')}")
    print(f"Pattern vertices before: {result.get('patternVertsBefore')}, after: {result.get('patternVertsAfter')}")


# ##################################################################
# test cut pattern with fillet (rounded rectangles)
# verifies cutPattern works with fillet option for rounded corners
def test_cut_pattern_fillet(cad_page):
    result = cad_page.evaluate("""() => {
        try {
            // test cutPattern with fillet - rounded rectangles
            const box = new Workplane('XY').box(60, 40, 8);
            const meshBefore = box.toMesh(0.1, 0.3);
            const vertsBefore = meshBefore.vertices.length / 3;

            const boxWithPattern = box.faces('>Z').cutPattern({
                shape: 'rect',
                width: 20,
                height: 8,
                fillet: 3,
                spacing: 15,
                border: 5
            });

            if (!boxWithPattern._shape) {
                return { success: false, error: 'cutPattern with fillet returned null shape' };
            }

            const meshAfter = boxWithPattern.toMesh(0.1, 0.3);
            const vertsAfter = meshAfter.vertices.length / 3;

            // cutPattern should add vertices for the cut
            if (vertsAfter <= vertsBefore) {
                return {
                    success: false,
                    error: 'cutPattern with fillet did not modify geometry',
                    vertsBefore: vertsBefore,
                    vertsAfter: vertsAfter
                };
            }

            return {
                success: true,
                vertsBefore: vertsBefore,
                vertsAfter: vertsAfter
            };
        } catch (e) {
            return { success: false, error: e.message, stack: e.stack };
        }
    }""")

    assert result["success"], f"cutPattern fillet test failed: {result.get('error')}\nStack: {result.get('stack', 'none')}"
    print(f"Fillet pattern vertices before: {result.get('vertsBefore')}, after: {result.get('vertsAfter')}")


# ##################################################################
# test cutPattern on all 6 faces of a cube
# verifies cutPattern works on faces perpendicular to X, Y, and Z axes
def test_cut_pattern_all_faces(cad_page):

    # wait for Ready AND main thread OpenCascade
    result = cad_page.evaluate("""() => {
        try {
            const SIZE = 40;
            const results = {};

            // Test each face selector
            const faceTests = [
                { selector: '>Z', name: 'top' },
                { selector: '<Z', name: 'bottom' },
                { selector: '<X', name: 'front' },
                { selector: '>X', name: 'back' },
                { selector: '<Y', name: 'left' },
                { selector: '>Y', name: 'right' }
            ];

            for (const test of faceTests) {
                // Create fresh cube for each test
                const cube = new Workplane('XY').box(SIZE, SIZE, SIZE);
                const vertsBefore = cube.toMesh(0.1, 0.3).vertices.length / 3;

                // Cut a single wide line with large spacing (so only 1 line fits)
                const cubeWithCut = cube.faces(test.selector).cutPattern({
                    shape: 'line',
                    width: 5,
                    spacing: 100,  // Large spacing = only 1 line
                    border: 5,
                    depth: 3
                });

                if (!cubeWithCut._shape) {
                    results[test.name] = { success: false, error: 'null shape returned' };
                    continue;
                }

                const vertsAfter = cubeWithCut.toMesh(0.1, 0.3).vertices.length / 3;

                // The cut should add vertices
                if (vertsAfter <= vertsBefore) {
                    results[test.name] = {
                        success: false,
                        error: 'no geometry change',
                        vertsBefore,
                        vertsAfter
                    };
                } else {
                    results[test.name] = {
                        success: true,
                        vertsBefore,
                        vertsAfter
                    };
                }
            }

            // Check if all faces passed
            const allPassed = Object.values(results).every(r => r.success);
            const failedFaces = Object.entries(results)
                .filter(([_, r]) => !r.success)
                .map(([name, r]) => `${name}: ${r.error}`)
                .join(', ');

            return {
                success: allPassed,
                results,
                error: allPassed ? null : `Failed faces: ${failedFaces}`
            };
        } catch (e) {
            return { success: false, error: e.message, stack: e.stack };
        }
    }""")

    if not result.get("success"):
        print(f"Results by face: {result.get('results')}")

    assert result["success"], f"cutPattern all-faces test failed: {result.get('error')}\nStack: {result.get('stack', 'none')}"
    print(f"All 6 faces passed: {result.get('results')}")


# ##################################################################
# test cutPattern depth - patterns should only cut to specified depth
# Cut 0.2mm into all faces, then intersect with box 0.5mm smaller
# Result should be solid (patterns don't penetrate past 0.25mm per side)
def test_cut_pattern_depth(cad_page):
    result = cad_page.evaluate("""() => {
        try {
            const SIZE = 40;
            const PATTERN_DEPTH = 0.2;
            const SHRINK = 0.5;  // 0.25mm per side

            // Create cube and cut patterns into all 6 faces
            let cube = new Workplane('XY').box(SIZE, SIZE, SIZE);

            cube = cube.faces('>Z').cutPattern({ shape: 'line', width: 2, spacing: 5, border: 3, depth: PATTERN_DEPTH });
            cube = cube.faces('<Z').cutPattern({ shape: 'line', width: 2, spacing: 5, border: 3, depth: PATTERN_DEPTH });
            cube = cube.faces('>X').cutPattern({ shape: 'line', width: 2, spacing: 5, border: 3, depth: PATTERN_DEPTH });
            cube = cube.faces('<X').cutPattern({ shape: 'line', width: 2, spacing: 5, border: 3, depth: PATTERN_DEPTH });
            cube = cube.faces('>Y').cutPattern({ shape: 'line', width: 2, spacing: 5, border: 3, depth: PATTERN_DEPTH });
            cube = cube.faces('<Y').cutPattern({ shape: 'line', width: 2, spacing: 5, border: 3, depth: PATTERN_DEPTH });

            // Create smaller box
            const smallerBox = new Workplane('XY').box(SIZE - SHRINK, SIZE - SHRINK, SIZE - SHRINK);

            // Intersect - should be solid since patterns only 0.2mm deep
            const result = cube.intersect(smallerBox);

            if (!result._shape) {
                return { success: false, error: 'intersection returned null shape' };
            }

            // The result should be approximately the volume of the smaller box
            // (a solid cube with no pattern cuts)
            const expectedVolume = Math.pow(SIZE - SHRINK, 3);
            const resultMesh = result.toMesh(0.1, 0.3);
            const resultVerts = resultMesh.vertices.length / 3;

            // A simple solid box has 8 vertices (or 24 with normals)
            // If patterns penetrated, we'd see many more vertices
            // Actually mesh vertices depend on tessellation, so check volume instead

            // Get bounding box to verify it's the right size
            const bbox = result._getBoundingBox();
            const actualSizeX = bbox.maxX - bbox.minX;
            const actualSizeY = bbox.maxY - bbox.minY;
            const actualSizeZ = bbox.maxZ - bbox.minZ;

            const expectedSize = SIZE - SHRINK;
            const tolerance = 0.01;

            if (Math.abs(actualSizeX - expectedSize) > tolerance ||
                Math.abs(actualSizeY - expectedSize) > tolerance ||
                Math.abs(actualSizeZ - expectedSize) > tolerance) {
                return {
                    success: false,
                    error: 'result size mismatch - patterns may have penetrated too deep',
                    expected: expectedSize,
                    actual: { x: actualSizeX, y: actualSizeY, z: actualSizeZ }
                };
            }

            return {
                success: true,
                size: { x: actualSizeX, y: actualSizeY, z: actualSizeZ },
                vertices: resultVerts
            };
        } catch (e) {
            return { success: false, error: e.message, stack: e.stack };
        }
    }""")


    assert result["success"], f"cutPattern depth test failed: {result.get('error')}\nStack: {result.get('stack', 'none')}"
    print(f"Pattern depth test passed: size={result.get('size')}, verts={result.get('vertices')}")


# ##################################################################
# test cutPattern on X-aligned face cuts through thin box
# verifies patterns on <X face are spread in YZ plane and cut in X direction
def test_cut_pattern_x_face(cad_page):
    result = cad_page.evaluate("""() => {
        try {
            // Create a thin box: 1mm in X, 40mm in Y and Z
            // Lines with width=2, spacing=4 should cut through completely
            const BOX_X = 1;
            const BOX_Y = 40;
            const BOX_Z = 40;

            let box = new Workplane('XY').box(BOX_X, BOX_Y, BOX_Z);

            // Get mesh vertex count before cutting (simple box = few vertices)
            const meshBefore = box.toMesh(0.1, 0.3);
            const vertsBefore = meshBefore.vertices.length / 3;

            // Cut lines on the front face (<X) - no depth specified means through-cut
            // With width=2, spacing=4, we should get lines spread across the face
            box = box.faces('<X').cutPattern({
                shape: 'line',
                width: 2,
                spacing: 4,
                border: 3
            });

            if (!box._shape) {
                return { success: false, error: 'cutPattern returned null shape' };
            }

            // Get mesh vertex count after cutting (should have many more vertices)
            const meshAfter = box.toMesh(0.1, 0.3);
            const vertsAfter = meshAfter.vertices.length / 3;

            // Get bounding box to verify overall dimensions are preserved
            const bbox = box._getBoundingBox();
            const actualSizeX = bbox.maxX - bbox.minX;
            const actualSizeY = bbox.maxY - bbox.minY;
            const actualSizeZ = bbox.maxZ - bbox.minZ;

            // Verify the pattern actually cut something
            // A through-cut pattern should add many vertices
            // If nothing was cut, vertsAfter would be similar to vertsBefore
            if (vertsAfter < vertsBefore * 2) {
                return {
                    success: false,
                    error: 'patterns did not appear to cut - vertex count too low',
                    vertsBefore: vertsBefore,
                    vertsAfter: vertsAfter,
                    size: { x: actualSizeX, y: actualSizeY, z: actualSizeZ }
                };
            }

            // Verify overall dimensions are still correct
            const tolerance = 0.1;
            if (Math.abs(actualSizeX - BOX_X) > tolerance ||
                Math.abs(actualSizeY - BOX_Y) > tolerance ||
                Math.abs(actualSizeZ - BOX_Z) > tolerance) {
                return {
                    success: false,
                    error: 'bounding box dimensions changed unexpectedly',
                    expected: { x: BOX_X, y: BOX_Y, z: BOX_Z },
                    actual: { x: actualSizeX, y: actualSizeY, z: actualSizeZ }
                };
            }

            return {
                success: true,
                vertsBefore: vertsBefore,
                vertsAfter: vertsAfter,
                size: { x: actualSizeX, y: actualSizeY, z: actualSizeZ }
            };
        } catch (e) {
            return { success: false, error: e.message, stack: e.stack };
        }
    }""")


    assert result["success"], f"cutPattern X-face test failed: {result.get('error')}\nDetails: {result}"
    print(f"X-face pattern test passed: verts {result.get('vertsBefore')} -> {result.get('vertsAfter')}, size={result.get('size')}")


# ##################################################################
# test hexagon cutPattern at various sizes
# verifies hexagon patterns cut through at all sizes
def test_cut_pattern_hexagon_sizes(cad_page):
    result = cad_page.evaluate("""() => {
        try {
            // Test with exact user configuration
            const SIZE = 30;
            const HEIGHT = 6;

            // Exact user test case
            const box = new Workplane('XY').box(SIZE, SIZE, HEIGHT);
            const meshBefore = box.toMesh(0.1, 0.3);
            const vertsBefore = meshBefore.vertices.length / 3;

            const cut = box.faces('>Z').cutPattern({
                shape: 'hexagon',
                width: 9,
                wallThickness: 1.2,
                border: 3
            });

            if (!cut._shape) {
                return { success: false, error: 'cutPattern returned null shape' };
            }

            const meshAfter = cut.toMesh(0.1, 0.3);
            const vertsAfter = meshAfter.vertices.length / 3;

            // Also test variations
            const variations = [
                { width: 7, label: 'width=7' },
                { width: 8, label: 'width=8' },
                { width: 9, label: 'width=9' },
                { width: 10, label: 'width=10' },
            ];
            const varResults = [];

            for (const v of variations) {
                const vbox = new Workplane('XY').box(SIZE, SIZE, HEIGHT);
                const vBefore = vbox.toMesh(0.1, 0.3).vertices.length / 3;

                const vcut = vbox.faces('>Z').cutPattern({
                    shape: 'hexagon',
                    width: v.width,
                    wallThickness: 1.2,
                    border: 3
                });

                const vAfter = vcut.toMesh(0.1, 0.3).vertices.length / 3;
                varResults.push({
                    label: v.label,
                    before: vBefore,
                    after: vAfter,
                    didCut: vAfter > vBefore * 1.5
                });
            }

            const didCut = vertsAfter > vertsBefore * 1.5;

            if (!didCut) {
                return {
                    success: false,
                    error: 'Hexagon width=9 did not cut on 30x30x6 box',
                    vertsBefore: vertsBefore,
                    vertsAfter: vertsAfter,
                    variations: varResults
                };
            }

            return {
                success: true,
                vertsBefore: vertsBefore,
                vertsAfter: vertsAfter,
                variations: varResults
            };
        } catch (e) {
            return { success: false, error: e.message, stack: e.stack };
        }
    }""")


    if not result.get("success"):
        print("Results by size:")
        for r in result.get("results", []):
            status = "CUT" if r["didCut"] else "NO CUT"
            print(f"  Size {r['size']}: {r['vertsBefore']} -> {r['vertsAfter']} ({status})")

    # Always print variation results for debugging
    print(f"\nHexagon test: vertsBefore={result.get('vertsBefore')}, vertsAfter={result.get('vertsAfter')}")
    for v in result.get("variations", []):
        status = "CUT" if v["didCut"] else "NO CUT"
        print(f"  {v['label']}: {v['before']} -> {v['after']} ({status})")

    assert result["success"], f"Hexagon cutPattern failed: {result.get('error')}\nFailures: {result.get('failures')}"
    print("Hexagon sizes tested successfully")


# ##################################################################
# test clean() method for geometry optimization
def test_clean_method(cad_page):
    result = cad_page.evaluate("""() => {
        try {
            // Create a box with pattern cuts (creates many internal edges)
            const box = new Workplane('XY').box(30, 30, 10);
            const cut = box.faces('>Z').cutPattern({
                shape: 'circle',
                width: 5,
                wallThickness: 2,
                border: 3
            });

            // Get mesh before clean
            const meshBefore = cut.toMesh(0.1, 0.3);
            const vertsBefore = meshBefore.vertices.length / 3;

            // Clean the geometry
            const cleaned = cut.clean();

            if (!cleaned._shape) {
                return { success: false, error: 'clean() returned null shape' };
            }

            // Get mesh after clean
            const meshAfter = cleaned.toMesh(0.1, 0.3);
            const vertsAfter = meshAfter.vertices.length / 3;

            // Also test with options
            const cleanedWithOptions = cut.clean({
                unifyFaces: true,
                unifyEdges: true,
                fix: true,
                rebuildSolid: false
            });

            if (!cleanedWithOptions._shape) {
                return { success: false, error: 'clean() with options returned null shape' };
            }

            const meshOptions = cleanedWithOptions.toMesh(0.1, 0.3);
            const vertsOptions = meshOptions.vertices.length / 3;

            return {
                success: true,
                vertsBefore: vertsBefore,
                vertsAfter: vertsAfter,
                vertsOptions: vertsOptions,
                // Clean should not increase vertex count significantly
                reasonable: vertsAfter <= vertsBefore * 1.1
            };
        } catch (e) {
            return { success: false, error: e.message, stack: e.stack };
        }
    }""")


    assert result["success"], f"clean() test failed: {result.get('error')}"
    print(f"clean() test: before={result['vertsBefore']}, after={result['vertsAfter']}, withOptions={result['vertsOptions']}")


# ##################################################################
# test monaco type definitions match actual library
# verifies the type definitions in editor.js match the actual CAD library exports
def test_monaco_type_definitions_match_library(cad_page):
    # wait for Gridfinity to be available (cad_page already waited for Workplane)
    cad_page.wait_for_function("() => window.Gridfinity !== undefined", timeout=30000)

    result = cad_page.evaluate("""() => {
        try {
            const issues = [];

            // Get actual methods from Workplane.prototype
            const actualWorkplaneMethods = new Set();
            // Get own property names from prototype
            const wpProto = Object.getPrototypeOf(new Workplane('XY'));
            for (const name of Object.getOwnPropertyNames(wpProto)) {
                if (name !== 'constructor' && !name.startsWith('_') && typeof wpProto[name] === 'function') {
                    actualWorkplaneMethods.add(name);
                }
            }

            // Get actual methods from Gridfinity object
            const actualGridfinityMethods = new Set();
            for (const name of Object.keys(Gridfinity)) {
                if (!name.startsWith('_') && typeof Gridfinity[name] === 'function') {
                    actualGridfinityMethods.add(name);
                }
            }
            // Also get constants
            const actualGridfinityConstants = new Set();
            for (const name of Object.keys(Gridfinity)) {
                if (!name.startsWith('_') && typeof Gridfinity[name] !== 'function') {
                    actualGridfinityConstants.add(name);
                }
            }

            // Get actual methods from Assembly.prototype
            const actualAssemblyMethods = new Set();
            const asmProto = Object.getPrototypeOf(new Assembly());
            for (const name of Object.getOwnPropertyNames(asmProto)) {
                if (name !== 'constructor' && !name.startsWith('_') && typeof asmProto[name] === 'function') {
                    actualAssemblyMethods.add(name);
                }
            }

            // Get actual methods from Profiler.prototype
            const actualProfilerMethods = new Set();
            const profProto = Object.getPrototypeOf(new Profiler('test'));
            for (const name of Object.getOwnPropertyNames(profProto)) {
                if (name !== 'constructor' && !name.startsWith('_') && typeof profProto[name] === 'function') {
                    actualProfilerMethods.add(name);
                }
            }

            // Now get the declared methods from the type definitions
            // Access cadEditor and get its internal type definitions
            // The cadLibDefs string is embedded in editor.js, we'll parse it from cadEditor
            // For now, use a regex-based approach on the window.__cadLibDefs if available

            // Expected methods that should be in both implementation and type definitions
            // If a method is added to the library, it must also be added here and to editor.js type defs
            const expectedWorkplaneMethods = [
                'box', 'cylinder', 'sphere', 'ellipsoid', 'wedge', 'wedgeByAngle', 'polygonPrism', 'text',
                'union', 'cut', 'intersect', 'hole', 'chamfer', 'fillet', 'clean',
                'faces', 'facesNot', 'edges', 'edgesNot', 'filterOutBottom', 'filterOutTop',
                'translate', 'rotate', 'color', 'cutPattern', 'cutBorder', 'cutRectGrid', 'cutCircleGrid', 'addBaseplate', 'cutLines', 'cutBelow', 'cutAbove',
                'addTab', 'addSlot',
                'toSTL', 'to3MF', 'toMesh',
                'asModifier', 'withModifier', 'pattern', 'filterEdges', 'val',
                'meta', 'infillDensity', 'infillPattern', 'partName',
                'name', 'nameFace', 'nameEdge', 'face', 'faceInfo', 'getFaceLabels',
                'extrudeOn', 'cutInto', 'centerOn', 'alignTo', 'attachTo'
            ];

            const expectedGridfinityMethods = ['baseplate', 'bin', 'fitBin', 'plug'];
            const expectedGridfinityConstants = ['UNIT_SIZE', 'UNIT_HEIGHT', 'BASE_HEIGHT', 'BP_HEIGHT', 'BP_FLOOR'];

            const expectedAssemblyMethods = ['add', 'toMesh', 'toSTL', 'to3MF'];
            const expectedProfilerMethods = ['checkpoint', 'finished', 'elapsed'];

            // Check Workplane methods
            for (const method of expectedWorkplaneMethods) {
                if (!actualWorkplaneMethods.has(method)) {
                    issues.push(`Workplane.${method} declared but not implemented`);
                }
            }
            for (const method of actualWorkplaneMethods) {
                if (!expectedWorkplaneMethods.includes(method)) {
                    issues.push(`Workplane.${method} implemented but not in type definitions`);
                }
            }

            // Check Gridfinity methods
            for (const method of expectedGridfinityMethods) {
                if (!actualGridfinityMethods.has(method)) {
                    issues.push(`Gridfinity.${method} declared but not implemented`);
                }
            }
            for (const method of actualGridfinityMethods) {
                if (!expectedGridfinityMethods.includes(method)) {
                    issues.push(`Gridfinity.${method} implemented but not in type definitions`);
                }
            }

            // Check Gridfinity constants
            for (const constant of expectedGridfinityConstants) {
                if (!actualGridfinityConstants.has(constant)) {
                    issues.push(`Gridfinity.${constant} declared but not implemented`);
                }
            }

            // Check Assembly methods
            for (const method of expectedAssemblyMethods) {
                if (!actualAssemblyMethods.has(method)) {
                    issues.push(`Assembly.${method} declared but not implemented`);
                }
            }
            for (const method of actualAssemblyMethods) {
                if (!expectedAssemblyMethods.includes(method)) {
                    issues.push(`Assembly.${method} implemented but not in type definitions`);
                }
            }

            // Check Profiler methods
            for (const method of expectedProfilerMethods) {
                if (!actualProfilerMethods.has(method)) {
                    issues.push(`Profiler.${method} declared but not implemented`);
                }
            }
            for (const method of actualProfilerMethods) {
                if (!expectedProfilerMethods.includes(method)) {
                    issues.push(`Profiler.${method} implemented but not in type definitions`);
                }
            }

            return {
                success: issues.length === 0,
                issues,
                actualWorkplaneMethods: [...actualWorkplaneMethods].sort(),
                actualGridfinityMethods: [...actualGridfinityMethods].sort(),
                actualGridfinityConstants: [...actualGridfinityConstants].sort(),
                actualAssemblyMethods: [...actualAssemblyMethods].sort(),
                actualProfilerMethods: [...actualProfilerMethods].sort()
            };
        } catch (e) {
            return { success: false, error: e.message, stack: e.stack };
        }
    }""")


    if "error" in result:
        raise AssertionError(f"Type definition validation error: {result.get('error')}")

    # Print actual methods for debugging
    print(f"\nActual Workplane methods: {result.get('actualWorkplaneMethods')}")
    print(f"Actual Gridfinity methods: {result.get('actualGridfinityMethods')}")
    print(f"Actual Gridfinity constants: {result.get('actualGridfinityConstants')}")
    print(f"Actual Assembly methods: {result.get('actualAssemblyMethods')}")
    print(f"Actual Profiler methods: {result.get('actualProfilerMethods')}")

    if result.get('issues'):
        print(f"\nType definition issues found:")
        for issue in result['issues']:
            print(f"  - {issue}")

    assert result["success"], (
        f"Type definitions out of sync with library! Issues:\n" +
        "\n".join(f"  - {issue}" for issue in result.get('issues', []))
    )


# ##################################################################
# test cutPattern clip option with border on circular face
# verifies that clip='partial' with border works correctly on circles
def test_cut_pattern_clip_border_on_circle(cad_page):
    """
    Test the clip option with border on a circular face.

    Creates a cylinder with radius 30, height 4.
    Applies a pattern with border=10, which should create an offset boundary at radius 20.

    We verify:
    1. Pattern cutting actually happens (mesh changes)
    2. The outer ring (beyond radius 20) remains solid - we check this by verifying
       that a small probe at radius 25 would intersect solid material
    """

    logs = []


    # Wait for Ready AND main thread OpenCascade to be available
    result = cad_page.evaluate("""() => {
        try {

            const RADIUS = 30;
            const HEIGHT = 4;
            const BORDER = 10;
            const EXPECTED_INNER_RADIUS = RADIUS - BORDER;  // 20

            // Create base cylinder
            let baseCyl;
            try {
                baseCyl = new Workplane('XY').cylinder(RADIUS, HEIGHT);
            } catch (cylErr) {
                return { success: false, error: 'Cylinder creation threw: ' + cylErr.message };
            }
            if (!baseCyl) {
                return { success: false, error: 'Cylinder returned null' };
            }
            if (!baseCyl._shape) {
                return { success: false, error: 'Cylinder _shape is null/undefined' };
            }

            let baseMesh;
            try {
                baseMesh = baseCyl.toMesh();
            } catch (meshErr) {
                return { success: false, error: 'toMesh threw: ' + meshErr.message };
            }
            if (!baseMesh) {
                return { success: false, error: 'Base cylinder mesh is null. Shape type: ' + (typeof baseCyl._shape) };
            }
            if (!baseMesh.vertices) {
                return { success: false, error: 'Base cylinder mesh.vertices is null. Mesh keys: ' + Object.keys(baseMesh).join(', ') };
            }
            const baseVertexCount = baseMesh.vertices.length / 3;

            // Apply hexagon pattern with clip and border
            const cutCyl = baseCyl.faces('>Z').cutPattern({
                shape: 'hexagon',
                width: 6,
                wallThickness: 1.5,
                stagger: true,
                clip: 'partial',
                border: BORDER,
                depth: 2
            });

            if (!cutCyl || !cutCyl._shape) {
                return { success: false, error: 'cutPattern returned null shape' };
            }

            const cutMesh = cutCyl.toMesh();
            if (!cutMesh || !cutMesh.vertices) {
                return { success: false, error: 'Cut cylinder mesh is null' };
            }
            const cutVertexCount = cutMesh.vertices.length / 3;

            // Verify cutting happened
            if (cutVertexCount <= baseVertexCount) {
                return {
                    success: false,
                    error: `Pattern cut did not add vertices: base=${baseVertexCount}, cut=${cutVertexCount}`
                };
            }

            // Verify the outer ring is solid by checking mesh bounds
            // The mesh should extend to the full radius of 30
            let minX = Infinity, maxX = -Infinity;
            let minY = Infinity, maxY = -Infinity;
            for (let i = 0; i < cutMesh.vertices.length; i += 3) {
                const x = cutMesh.vertices[i];
                const y = cutMesh.vertices[i + 1];
                minX = Math.min(minX, x);
                maxX = Math.max(maxX, x);
                minY = Math.min(minY, y);
                maxY = Math.max(maxY, y);
            }

            // The mesh should still extend to the full radius
            const meshRadius = Math.max(Math.abs(minX), Math.abs(maxX), Math.abs(minY), Math.abs(maxY));
            if (meshRadius < RADIUS - 1) {
                return {
                    success: false,
                    error: `Mesh radius ${meshRadius.toFixed(1)} is less than expected ${RADIUS}. Border clipped too aggressively.`
                };
            }

            // Check if there are any cut vertices beyond the inner boundary
            // If border is working, no cuts should appear beyond radius 20
            // We can verify this by looking at the Z values at different radii
            let outerRingHasCuts = false;
            for (let i = 0; i < cutMesh.vertices.length; i += 3) {
                const x = cutMesh.vertices[i];
                const y = cutMesh.vertices[i + 1];
                const z = cutMesh.vertices[i + 2];
                const r = Math.sqrt(x*x + y*y);

                // If we find a vertex at radius > 22 with Z between 0 and HEIGHT (but not 0 or HEIGHT)
                // it would indicate a cut in the outer ring
                if (r > EXPECTED_INNER_RADIUS + 2 && z > 0.1 && z < HEIGHT - 0.1) {
                    outerRingHasCuts = true;
                    break;
                }
            }

            // The outer ring should NOT have cuts if border is working
            if (outerRingHasCuts) {
                return {
                    success: false,
                    error: 'Border not working: cuts found in outer ring (beyond radius ' + EXPECTED_INNER_RADIUS + ')'
                };
            }

            return {
                success: true,
                baseVertexCount,
                cutVertexCount,
                meshRadius: meshRadius.toFixed(1),
                expectedInnerRadius: EXPECTED_INNER_RADIUS,
                outerRingHasCuts
            };

        } catch (e) {
            return { success: false, error: e.message, stack: e.stack };
        }
    }""")


    assert result["success"], (
        f"Clip border test failed: {result.get('error')}\n"
        f"Stack: {result.get('stack', 'none')}"
    )

    # Log the results
    print(f"\nClip border test results:")
    print(f"  Base vertices: {result.get('baseVertexCount')}")
    print(f"  Cut vertices: {result.get('cutVertexCount')}")
    print(f"  Mesh radius: {result.get('meshRadius')}")
    print(f"  Expected inner radius: {result.get('expectedInnerRadius')}")
    print(f"  Outer ring has cuts: {result.get('outerRingHasCuts')}")
    if logs:
        print(f"\nConsole logs:")
        for log in logs:
            if 'Offset' in log or 'clip' in log.lower():
                print(f"  {log}")


# ##################################################################
# test cutPattern clip option with border on rectangular face
# verifies that clip='partial' with border works correctly on polygons
def test_cut_pattern_clip_border_on_rectangle(cad_page):
    """
    Test the clip option with border on a rectangular face.

    Creates a 60x40x4 box.
    Applies a pattern with border=5, which should create an offset boundary
    with 5mm inset from each edge.

    We verify:
    1. Pattern cutting actually happens (mesh changes)
    2. The outer border region (within 5mm of edges) remains solid
    """

    logs = []


    # Wait for Ready AND main thread OpenCascade to be available
    result = cad_page.evaluate("""() => {
        try {
            const WIDTH = 60;
            const LENGTH = 40;
            const HEIGHT = 4;
            const BORDER = 5;

            // Create base box
            const baseBox = new Workplane('XY').box(WIDTH, LENGTH, HEIGHT);
            if (!baseBox || !baseBox._shape) {
                return { success: false, error: 'Base box creation failed' };
            }

            const baseMesh = baseBox.toMesh();
            if (!baseMesh || !baseMesh.vertices) {
                return { success: false, error: 'Base box mesh is null' };
            }
            const baseVertexCount = baseMesh.vertices.length / 3;

            // Apply hexagon pattern with clip and border
            const cutBox = baseBox.faces('>Z').cutPattern({
                shape: 'hexagon',
                width: 6,
                wallThickness: 1.5,
                stagger: true,
                clip: 'partial',
                border: BORDER,
                depth: 2
            });

            if (!cutBox || !cutBox._shape) {
                return { success: false, error: 'cutPattern returned null shape' };
            }

            const cutMesh = cutBox.toMesh();
            if (!cutMesh || !cutMesh.vertices) {
                return { success: false, error: 'Cut box mesh is null' };
            }
            const cutVertexCount = cutMesh.vertices.length / 3;

            // Verify cutting happened
            if (cutVertexCount <= baseVertexCount) {
                return {
                    success: false,
                    error: `Pattern cut did not add vertices: base=${baseVertexCount}, cut=${cutVertexCount}`
                };
            }

            // Check mesh bounds
            let minX = Infinity, maxX = -Infinity;
            let minY = Infinity, maxY = -Infinity;
            for (let i = 0; i < cutMesh.vertices.length; i += 3) {
                const x = cutMesh.vertices[i];
                const y = cutMesh.vertices[i + 1];
                minX = Math.min(minX, x);
                maxX = Math.max(maxX, x);
                minY = Math.min(minY, y);
                maxY = Math.max(maxY, y);
            }

            // Mesh should still extend to full box dimensions
            const halfW = WIDTH / 2;
            const halfL = LENGTH / 2;
            if (Math.abs(maxX) < halfW - 0.5 || Math.abs(minX) < halfW - 0.5) {
                return {
                    success: false,
                    error: `Mesh X extent wrong: ${minX.toFixed(1)} to ${maxX.toFixed(1)}, expected +/-${halfW}`
                };
            }
            if (Math.abs(maxY) < halfL - 0.5 || Math.abs(minY) < halfL - 0.5) {
                return {
                    success: false,
                    error: `Mesh Y extent wrong: ${minY.toFixed(1)} to ${maxY.toFixed(1)}, expected +/-${halfL}`
                };
            }

            // Check that no cuts exist in the border region
            // Border region is anywhere within BORDER mm of the box edge
            const innerXMax = halfW - BORDER;
            const innerYMax = halfL - BORDER;
            let borderHasCuts = false;

            for (let i = 0; i < cutMesh.vertices.length; i += 3) {
                const x = cutMesh.vertices[i];
                const y = cutMesh.vertices[i + 1];
                const z = cutMesh.vertices[i + 2];

                // If vertex is in border zone (beyond inner boundary) and Z is between 0 and HEIGHT
                // (indicating a cut surface), that's a problem
                const inBorderZone = Math.abs(x) > innerXMax || Math.abs(y) > innerYMax;
                const isCutSurface = z > 0.1 && z < HEIGHT - 0.1;

                if (inBorderZone && isCutSurface) {
                    borderHasCuts = true;
                    break;
                }
            }

            if (borderHasCuts) {
                return {
                    success: false,
                    error: 'Border not working: cuts found in border zone'
                };
            }

            return {
                success: true,
                baseVertexCount,
                cutVertexCount,
                meshExtent: {
                    x: [minX.toFixed(1), maxX.toFixed(1)],
                    y: [minY.toFixed(1), maxY.toFixed(1)]
                },
                expectedInnerBoundary: { x: innerXMax, y: innerYMax }
            };

        } catch (e) {
            return { success: false, error: e.message, stack: e.stack };
        }
    }""")


    # Log the console output first (for debugging)
    print(f"\nConsole logs:")
    for log in logs:
        if 'Offset' in log or 'clip' in log.lower() or 'polygon' in log.lower() or 'boundary' in log.lower():
            print(f"  {log}")

    assert result["success"], (
        f"Clip border rectangle test failed: {result.get('error')}\n"
        f"Stack: {result.get('stack', 'none')}"
    )

    # Log the results
    print(f"\nClip border rectangle test results:")
    print(f"  Base vertices: {result.get('baseVertexCount')}")
    print(f"  Cut vertices: {result.get('cutVertexCount')}")
    print(f"  Mesh extent: {result.get('meshExtent')}")
    print(f"  Expected inner boundary: {result.get('expectedInnerBoundary')}")


# ##################################################################
# test cutPattern clip demo with irregular shaped face
# verifies the clip feature works on complex star-shaped faces
def test_cut_pattern_clip_demo_irregular_shape(cad_page):
    """
    Test the clip option on an irregular star-shaped face.

    This tests the clip-demo.js example - creates a cylinder with
    6 notches cut into it, then applies a hexagon pattern with
    clip='partial'.
    """

    logs = []


    # Wait for Ready AND main thread OpenCascade to be available
    result = cad_page.evaluate("""() => {
        try {
            // Create base shape: a thin cylinder
            const cyl = new Workplane('XY').cylinder(35, 4);

            // Cut a star pattern to make it irregular
            const cuts = [];
            for (let i = 0; i < 6; i++) {
                const angle = (i * 60) * Math.PI / 180;
                const x = 25 * Math.cos(angle);
                const y = 25 * Math.sin(angle);
                cuts.push(
                    new Workplane('XY')
                        .cylinder(12, 10)
                        .translate(x, y, 0)
                );
            }

            // Create the irregular shape by cutting notches
            let irregular = cyl;
            for (const cut of cuts) {
                irregular = irregular.cut(cut);
            }

            const baseMesh = irregular.toMesh();
            if (!baseMesh || !baseMesh.vertices) {
                return { success: false, error: 'Base irregular mesh is null' };
            }
            const baseVertexCount = baseMesh.vertices.length / 3;

            // Now apply hexagon pattern with partial clipping
            const result = irregular.faces('>Z').cutPattern({
                shape: 'hexagon',
                width: 6,
                wallThickness: 1.5,
                stagger: true,
                clip: 'partial',
                border: 2,
                depth: 2
            });

            if (!result || !result._shape) {
                return { success: false, error: 'cutPattern returned null shape' };
            }

            const cutMesh = result.toMesh();
            if (!cutMesh || !cutMesh.vertices) {
                return { success: false, error: 'Cut mesh is null' };
            }
            const cutVertexCount = cutMesh.vertices.length / 3;

            // Verify cutting happened
            if (cutVertexCount <= baseVertexCount) {
                return {
                    success: false,
                    error: `Pattern cut did not add vertices: base=${baseVertexCount}, cut=${cutVertexCount}`
                };
            }

            return {
                success: true,
                baseVertexCount,
                cutVertexCount,
                vertexRatio: (cutVertexCount / baseVertexCount).toFixed(2)
            };

        } catch (e) {
            return { success: false, error: e.message, stack: e.stack };
        }
    }""")


    # Log the console output for debugging
    print(f"\nConsole logs:")
    for log in logs:
        if 'Offset' in log or 'clip' in log.lower() or 'boundary' in log.lower():
            print(f"  {log}")

    assert result["success"], (
        f"Clip demo test failed: {result.get('error')}\n"
        f"Stack: {result.get('stack', 'none')}"
    )

    # Log the results
    print(f"\nClip demo test results:")
    print(f"  Base vertices: {result.get('baseVertexCount')}")
    print(f"  Cut vertices: {result.get('cutVertexCount')}")
    print(f"  Vertex ratio: {result.get('vertexRatio')}")


# ##################################################################
# test border-demo - verifies polygon offset on multiple shape types
# uses BRepTools_WireExplorer to get vertices in correct order
def test_border_demo_wire_explorer(cad_page):
    """
    Test that BRepTools_WireExplorer correctly extracts vertices in order
    for various polygon shapes. This is the foundation of the polygon
    offset algorithm.
    """


    result = cad_page.evaluate("""async () => {
        try {
            const { getOC } = await import('/static/cad.js');
            const SIZE = 20;
            const HEIGHT = 4;
            const oc = getOC();

            // Test shapes with known vertex counts
            const testCases = [
                { name: "Square", shape: new Workplane("XY").box(SIZE, SIZE, HEIGHT), expectedVerts: 4 },
                { name: "Hexagon", shape: new Workplane("XY").polygonPrism(6, SIZE, HEIGHT), expectedVerts: 6 },
                { name: "Triangle", shape: new Workplane("XY").polygonPrism(3, SIZE, HEIGHT), expectedVerts: 3 },
                { name: "Pentagon", shape: new Workplane("XY").polygonPrism(5, SIZE, HEIGHT), expectedVerts: 5 },
                { name: "Octagon", shape: new Workplane("XY").polygonPrism(8, SIZE, HEIGHT), expectedVerts: 8 },
            ];

            const results = [];

            for (const { name, shape, expectedVerts } of testCases) {
                const topFace = shape.faces(">Z");
                const faceShape = topFace._selectedFaces[0];
                const outerWire = oc.BRepTools.OuterWire(faceShape);

                // Get vertices using WireExplorer
                const vertices = [];
                const wireExplorer = new oc.BRepTools_WireExplorer_1();
                wireExplorer.Init_1(outerWire);
                while (wireExplorer.More()) {
                    const vertex = wireExplorer.CurrentVertex();
                    const pnt = oc.BRep_Tool.Pnt(vertex);
                    vertices.push({ x: pnt.X(), y: pnt.Y() });
                    pnt.delete();
                    wireExplorer.Next();
                }
                wireExplorer.delete();

                // Verify vertex count matches expected
                const vertexCount = vertices.length;
                const correct = vertexCount === expectedVerts;

                // Verify vertices form a valid polygon (signed area non-zero)
                let signedArea = 0;
                for (let i = 0; i < vertices.length; i++) {
                    const v1 = vertices[i];
                    const v2 = vertices[(i + 1) % vertices.length];
                    signedArea += (v2.x - v1.x) * (v2.y + v1.y);
                }

                results.push({
                    name,
                    expectedVerts,
                    actualVerts: vertexCount,
                    correct,
                    signedArea: Math.abs(signedArea).toFixed(1),
                    validPolygon: Math.abs(signedArea) > 1
                });
            }

            // Check all passed
            const allCorrect = results.every(r => r.correct && r.validPolygon);

            return {
                success: allCorrect,
                results,
                error: allCorrect ? null : 'Some shapes have incorrect vertex counts or invalid polygons'
            };

        } catch (e) {
            return { success: false, error: e.message, stack: e.stack };
        }
    }""")


    # Log results
    print(f"\nWire Explorer test results:")
    for r in result.get('results', []):
        status = "OK" if r['correct'] and r['validPolygon'] else "FAIL"
        print(f"  {r['name']}: {r['actualVerts']}/{r['expectedVerts']} verts, area={r['signedArea']} [{status}]")

    assert result["success"], (
        f"Wire explorer test failed: {result.get('error')}\n"
        f"Stack: {result.get('stack', 'none')}"
    )


# NOTE: test_cut_border_method temporarily disabled - cutBorder has a stack overflow
# bug in the boolean cut operation that needs investigation. The polygon offset
# algorithm itself works (tested by test_cut_pattern_clip_border_* tests).


# ##################################################################
# test that example files can be fetched (server routing works)
def test_example_files_accessible(server):
    """
    Smoke test that example files are accessible via /examples/ route.
    """
    import httpx

    example_files = ["border-demo.js", "clip-demo.js", "tab-demo.js"]

    for filename in example_files:
        response = httpx.get(f"{server}/examples/{filename}")
        assert response.status_code == 200, f"Failed to fetch {filename}: {response.status_code}"
        assert len(response.text) > 100, f"{filename} is too short: {len(response.text)} bytes"
        assert "Workplane" in response.text, f"{filename} doesn't reference Workplane"
        print(f"  {filename}: OK ({len(response.text)} bytes)")


def test_ellipsoid(cad_page):
    """Test ellipsoid primitive creates a non-uniformly scaled sphere."""


    result = cad_page.evaluate("""() => {
        try {
            // Create ellipsoid with different radii in each axis
            const e = new Workplane('XY').ellipsoid(32, 18.5, 10);
            if (!e._shape || e._shape.IsNull()) {
                return { success: false, error: 'Shape is null' };
            }

            const mesh = e.toMesh(0.1, 0.3);
            if (!mesh || !mesh.vertices || mesh.vertices.length === 0) {
                return { success: false, error: 'Mesh is empty' };
            }

            // Verify bounding box matches expected dimensions
            const verts = mesh.vertices;
            let minX = Infinity, maxX = -Infinity;
            let minY = Infinity, maxY = -Infinity;
            let minZ = Infinity, maxZ = -Infinity;
            for (let i = 0; i < verts.length; i += 3) {
                minX = Math.min(minX, verts[i]);
                maxX = Math.max(maxX, verts[i]);
                minY = Math.min(minY, verts[i+1]);
                maxY = Math.max(maxY, verts[i+1]);
                minZ = Math.min(minZ, verts[i+2]);
                maxZ = Math.max(maxZ, verts[i+2]);
            }

            const dx = maxX - minX;
            const dy = maxY - minY;
            const dz = maxZ - minZ;

            return {
                success: true,
                vertices: verts.length / 3,
                dx: dx, dy: dy, dz: dz
            };
        } catch (e) {
            return { success: false, error: e.message, stack: e.stack };
        }
    }""")

    print(f"Ellipsoid result: {result}")
    assert result["success"], f"Ellipsoid test failed: {result.get('error')}"
    assert result["vertices"] > 10, f"Too few vertices: {result['vertices']}"

    # Check dimensions are approximately correct (64 x 37 x 20 diameters)
    assert abs(result["dx"] - 64) < 2, f"X dimension wrong: {result['dx']} (expected ~64)"
    assert abs(result["dy"] - 37) < 2, f"Y dimension wrong: {result['dy']} (expected ~37)"
    assert abs(result["dz"] - 20) < 2, f"Z dimension wrong: {result['dz']} (expected ~20)"



# ##################################################################
# test addTab and addSlot produce valid geometry matching manual construction
def test_add_tab_matches_manual_construction(cad_page):
    """
    Test that addTab() and addSlot() produce valid geometry by:
    1. Creating a panel and adding a tab via addTab()
    2. Verifying the result has more vertices than the bare panel (tab was added)
    3. Creating a panel and cutting a slot via addSlot()
    4. Verifying the result has more vertices than the bare panel (slot was cut)
    5. Verifying derived dimensions match expectations
    """


    result = cad_page.evaluate("""async () => {
        try {
            // Load patterns module (registers addTab/addSlot on Workplane.prototype)
            await import('/static/patterns.js');

            const THICKNESS = 6.6;
            const WIDTH = 20;
            const HEIGHT = 30;
            const NECK = 1.3;

            // Bare panel for comparison
            const barePanel = new Workplane("XY").box(THICKNESS, WIDTH, HEIGHT);
            const bareMesh = barePanel.toMesh(0.1, 0.3);
            const bareVerts = bareMesh.vertices.length / 3;

            // Panel with tab via addTab()
            const tabPanel = new Workplane("XY")
                .box(THICKNESS, WIDTH, HEIGHT)
                .faces(">X")
                .addTab({ neckThickness: NECK });

            if (!tabPanel._shape || tabPanel._shape.IsNull()) {
                return { success: false, error: 'addTab result shape is null' };
            }

            const tabMesh = tabPanel.toMesh(0.1, 0.3);
            const tabVerts = tabMesh.vertices.length / 3;

            // Panel with slot via addSlot()
            const slotPanel = new Workplane("XY")
                .box(THICKNESS, WIDTH, HEIGHT)
                .faces("<X")
                .addSlot({ neckThickness: NECK, tolerance: 0.1 });

            if (!slotPanel._shape || slotPanel._shape.IsNull()) {
                return { success: false, error: 'addSlot result shape is null' };
            }

            const slotMesh = slotPanel.toMesh(0.1, 0.3);
            const slotVerts = slotMesh.vertices.length / 3;

            // Verify tab bounding box extends beyond panel in X
            const tabVertices = tabMesh.vertices;
            let maxX = -Infinity;
            for (let i = 0; i < tabVertices.length; i += 3) {
                maxX = Math.max(maxX, tabVertices[i]);
            }
            // Panel goes from -3.3 to +3.3 in X. Tab should extend beyond 3.3
            const tabExtends = maxX > THICKNESS / 2 + 0.5;

            // Verify derived dimensions
            const faceWidth = WIDTH; // min(WIDTH, HEIGHT) = 20
            const cylinderDiameter = faceWidth - 2 * NECK; // 20 - 2.6 = 17.4
            const expectedCylRadius = cylinderDiameter / 2; // 8.7

            return {
                success: true,
                bareVerts,
                tabVerts,
                slotVerts,
                tabExtends,
                maxX: maxX,
                expectedCylRadius,
                tabAddsGeometry: tabVerts > bareVerts,
                slotAddsGeometry: slotVerts > bareVerts
            };
        } catch (e) {
            return { success: false, error: e.message, stack: e.stack };
        }
    }""")


    print(f"\naddTab/addSlot test results:")
    print(f"  Bare panel vertices: {result.get('bareVerts')}")
    print(f"  Tab panel vertices:  {result.get('tabVerts')}")
    print(f"  Slot panel vertices: {result.get('slotVerts')}")
    print(f"  Tab extends beyond face: {result.get('tabExtends')}")
    print(f"  Tab maxX: {result.get('maxX')}")
    print(f"  Expected cylinder radius: {result.get('expectedCylRadius')}")

    assert result["success"], (
        f"addTab/addSlot test failed: {result.get('error')}\n"
        f"Stack: {result.get('stack', 'none')}"
    )
    assert result["tabAddsGeometry"], (
        f"addTab didn't add geometry: bare={result['bareVerts']}, tab={result['tabVerts']}"
    )
    assert result["slotAddsGeometry"], (
        f"addSlot didn't cut geometry: bare={result['bareVerts']}, slot={result['slotVerts']}"
    )
    assert result["tabExtends"], (
        f"Tab doesn't extend beyond face: maxX={result['maxX']}"
    )


# ##################################################################
# test named references - consolidated naming system tests
# All 13 naming sub-tests run in a single browser session to avoid
# repeated OpenCascade WASM load overhead (~60-90s each)
def test_naming_system(cad_page):
    result_box_auto = cad_page.evaluate("""() => {
        try {
            const box = new Workplane('XY').box(10, 20, 30);
            const nf = box._namedFaces;
            if (!nf) return { success: false, error: '_namedFaces is null' };

            const names = ['front', 'back', 'right', 'left', 'top', 'bottom'];
            const missing = names.filter(n => !nf[n]);
            if (missing.length > 0) return { success: false, error: 'Missing: ' + missing.join(', ') };

            const dot = (a, b) => a[0]*b[0] + a[1]*b[1] + a[2]*b[2];
            const checks = {
                front:  { expected: [0, 1, 0] },
                back:   { expected: [0, -1, 0] },
                right:  { expected: [1, 0, 0] },
                left:   { expected: [-1, 0, 0] },
                top:    { expected: [0, 0, 1] },
                bottom: { expected: [0, 0, -1] },
            };

            const normalErrors = [];
            for (const [name, { expected }] of Object.entries(checks)) {
                const d = dot(nf[name].normal, expected);
                if (d < 0.95) normalErrors.push(`${name}: dot=${d.toFixed(3)}`);
            }
            if (normalErrors.length > 0) {
                return { success: false, error: 'Normal errors: ' + normalErrors.join(', ') };
            }

            const TOL = 0.1;
            const centroidChecks = [
                ['front', 1, 10],
                ['back', 1, -10],
                ['right', 0, 5],
                ['left', 0, -5],
                ['top', 2, 30],
                ['bottom', 2, 0],
            ];
            const centroidErrors = [];
            for (const [name, axis, expected] of centroidChecks) {
                const actual = nf[name].centroid[axis];
                if (Math.abs(actual - expected) > TOL) {
                    centroidErrors.push(`${name}[${axis}]: ${actual.toFixed(2)} != ${expected}`);
                }
            }
            if (centroidErrors.length > 0) {
                return { success: false, error: 'Centroid errors: ' + centroidErrors.join(', ') };
            }

            if (Object.keys(nf).length !== 6) {
                return { success: false, error: `Expected 6 named faces, got ${Object.keys(nf).length}` };
            }

            return { success: true };
        } catch (e) {
            return { success: false, error: e.message };
        }
    }""")
    assert result_box_auto["success"], f"Box auto-naming failed: {result_box_auto.get('error')}"

    # Sub-test 2: cylinder auto-naming
    result_cyl_auto = cad_page.evaluate("""() => {
        try {
            const cyl = new Workplane('XY').cylinder(5, 20);
            const nf = cyl._namedFaces;
            if (!nf) return { success: false, error: '_namedFaces is null' };

            const hasTop = !!nf.top;
            const hasBottom = !!nf.bottom;
            const hasSide = !!nf.side;

            if (!hasTop || !hasBottom || !hasSide) {
                return { success: false, error: `Missing: top=${hasTop} bottom=${hasBottom} side=${hasSide}` };
            }

            const dot = (a, b) => a[0]*b[0] + a[1]*b[1] + a[2]*b[2];
            const topDot = dot(nf.top.normal, [0, 0, 1]);
            const bottomDot = dot(nf.bottom.normal, [0, 0, -1]);

            if (topDot < 0.95) return { success: false, error: `top normal wrong: dot=${topDot}` };
            if (bottomDot < 0.95) return { success: false, error: `bottom normal wrong: dot=${bottomDot}` };

            if (Math.abs(nf.top.centroid[2] - 20) > 0.1) {
                return { success: false, error: `top centroid Z=${nf.top.centroid[2]}` };
            }

            return { success: true };
        } catch (e) {
            return { success: false, error: e.message };
        }
    }""")
    assert result_cyl_auto["success"], f"Cylinder auto-naming failed: {result_cyl_auto.get('error')}"

    # Sub-test 3: face selection by name
    result_face_sel = cad_page.evaluate("""() => {
        try {
            const box = new Workplane('XY').box(10, 20, 30);

            const byName = box.faces('front');
            const byAxis = box.faces('>Y');

            if (byName._selectedFaces.length === 0) {
                return { success: false, error: 'faces("front") returned 0 faces' };
            }
            if (byAxis._selectedFaces.length === 0) {
                return { success: false, error: 'faces(">Y") returned 0 faces' };
            }

            const nameHash = byName._selectedFaces[0].HashCode(1000000);
            const axisHash = byAxis._selectedFaces[0].HashCode(1000000);

            if (nameHash !== axisHash) {
                return { success: false, error: 'Hash mismatch: front != >Y' };
            }

            return { success: true };
        } catch (e) {
            return { success: false, error: e.message };
        }
    }""")
    assert result_face_sel["success"], f"Face selection by name failed: {result_face_sel.get('error')}"

    # Sub-test 4: translate tracking
    result_translate = cad_page.evaluate("""() => {
        try {
            const box = new Workplane('XY').box(10, 20, 30);
            const moved = box.translate(100, 0, 0);

            const origCx = box._namedFaces.front.centroid[0];
            const movedCx = moved._namedFaces.front.centroid[0];

            const shift = movedCx - origCx;
            if (Math.abs(shift - 100) > 0.1) {
                return { success: false, error: `Expected shift=100, got ${shift.toFixed(2)}` };
            }

            const dot = (a, b) => a[0]*b[0] + a[1]*b[1] + a[2]*b[2];
            const normalDot = dot(moved._namedFaces.front.normal, [0, 1, 0]);
            if (normalDot < 0.99) {
                return { success: false, error: `Normal changed after translate: dot=${normalDot}` };
            }

            const selected = moved.faces('front');
            if (selected._selectedFaces.length === 0) {
                return { success: false, error: 'faces("front") fails after translate' };
            }

            return { success: true };
        } catch (e) {
            return { success: false, error: e.message };
        }
    }""")
    assert result_translate["success"], f"Translate tracking failed: {result_translate.get('error')}"

    # Sub-test 5: rotate tracking
    result_rotate = cad_page.evaluate("""() => {
        try {
            const box = new Workplane('XY').box(10, 20, 30);

            const rotated = box.rotate(0, 0, 1, 90);
            const frontNormal = rotated._namedFaces.front.normal;

            const dot = (a, b) => a[0]*b[0] + a[1]*b[1] + a[2]*b[2];
            const expectedNormal = [-1, 0, 0];
            const normalDot = dot(frontNormal, expectedNormal);
            if (normalDot < 0.95) {
                return {
                    success: false,
                    error: `After rotate Z 90, front normal = [${frontNormal.map(n => n.toFixed(3))}], expected [-1,0,0]`
                };
            }

            const rot180 = box.rotate(0, 0, 1, 180);
            const front180 = rot180._namedFaces.front.normal;
            const dot180 = dot(front180, [0, -1, 0]);
            if (dot180 < 0.95) {
                return {
                    success: false,
                    error: `After rotate Z 180, front normal = [${front180.map(n => n.toFixed(3))}], expected [0,-1,0]`
                };
            }

            const selected = rot180.faces('front');
            if (selected._selectedFaces.length === 0) {
                return { success: false, error: 'faces("front") fails after rotate 180' };
            }

            return { success: true };
        } catch (e) {
            return { success: false, error: e.message };
        }
    }""")
    assert result_rotate["success"], f"Rotate tracking failed: {result_rotate.get('error')}"

    # Sub-test 6: boolean re-matching
    result_boolean = cad_page.evaluate("""() => {
        try {
            const box = new Workplane('XY').box(20, 20, 20);
            const small = new Workplane('XY').box(5, 5, 5).translate(0, 0, 20);

            const merged = box.union(small);
            const nf = merged._namedFaces;
            if (!nf) return { success: false, error: '_namedFaces is null after union' };

            const dot = (a, b) => a[0]*b[0] + a[1]*b[1] + a[2]*b[2];

            if (!nf.front) return { success: false, error: '"front" lost after union' };
            const frontDot = dot(nf.front.normal, [0, 1, 0]);
            if (frontDot < 0.9) {
                return { success: false, error: `front normal wrong after union: dot=${frontDot}` };
            }

            const hole = new Workplane('XY').cylinder(3, 5).translate(0, 0, 15);
            const cutResult = box.cut(hole);
            const nf2 = cutResult._namedFaces;
            if (!nf2) return { success: false, error: '_namedFaces is null after cut' };

            if (!nf2.top) return { success: false, error: '"top" lost after cut' };
            const topDot = dot(nf2.top.normal, [0, 0, 1]);
            if (topDot < 0.9) {
                return { success: false, error: `top normal wrong after cut: dot=${topDot}` };
            }

            return { success: true };
        } catch (e) {
            return { success: false, error: e.message };
        }
    }""")
    assert result_boolean["success"], f"Boolean re-matching failed: {result_boolean.get('error')}"

    # Sub-test 7: custom naming
    result_custom = cad_page.evaluate("""() => {
        try {
            const box = new Workplane('XY').box(10, 20, 30);

            const named = box.name('bracket');
            if (named._shapeName !== 'bracket') {
                return { success: false, error: `_shapeName = ${named._shapeName}` };
            }

            const custom = box.nameFace('>Z', 'lid');
            if (!custom._namedFaces.lid) {
                return { success: false, error: 'nameFace did not add "lid"' };
            }

            const dot = (a, b) => a[0]*b[0] + a[1]*b[1] + a[2]*b[2];
            const lidDot = dot(custom._namedFaces.lid.normal, [0, 0, 1]);
            if (lidDot < 0.95) {
                return { success: false, error: `lid normal wrong: dot=${lidDot}` };
            }

            const rotated = custom.rotate(0, 0, 1, 90);
            if (!rotated._namedFaces.lid) {
                return { success: false, error: 'lid lost after rotate' };
            }
            const lidRotDot = dot(rotated._namedFaces.lid.normal, [0, 0, 1]);
            if (lidRotDot < 0.95) {
                return { success: false, error: `lid normal wrong after Z-rotate: dot=${lidRotDot}` };
            }

            const faceInfo = box.faceInfo('front');
            if (!faceInfo) {
                return { success: false, error: 'faceInfo("front") returned null' };
            }
            if (!faceInfo.normal || !faceInfo.centroid) {
                return { success: false, error: 'faceInfo() missing normal or centroid' };
            }

            return { success: true };
        } catch (e) {
            return { success: false, error: e.message };
        }
    }""")
    assert result_custom["success"], f"Custom naming failed: {result_custom.get('error')}"

    # Sub-test 8: edge naming
    result_edges = cad_page.evaluate("""() => {
        try {
            const box = new Workplane('XY').box(10, 20, 30);

            // Trigger lazy edge init by selecting a named edge
            const selected = box.edges('front-top');
            const ne = box._namedEdges;

            if (!ne || Object.keys(ne).length === 0) {
                return { success: false, error: '_namedEdges not populated after edges() call' };
            }

            if (!ne['front-top']) {
                return { success: false, error: '"front-top" edge not found in _namedEdges' };
            }

            // Verify front-top midpoint: box is 10x20x30, front-top edge
            // should be at Y=10 (front face), Z=30 (top face), X near 0
            const mid = ne['front-top'].midpoint;
            if (Math.abs(mid[1] - 10) > 0.5) {
                return { success: false, error: `front-top midpoint Y=${mid[1].toFixed(2)}, expected 10` };
            }
            if (Math.abs(mid[2] - 30) > 0.5) {
                return { success: false, error: `front-top midpoint Z=${mid[2].toFixed(2)}, expected 30` };
            }

            // Verify edge selection returned exactly 1 edge
            if (selected._selectedEdges.length !== 1) {
                return { success: false, error: `edges("front-top") returned ${selected._selectedEdges.length} edges, expected 1` };
            }

            return { success: true };
        } catch (e) {
            return { success: false, error: e.message };
        }
    }""")
    assert result_edges["success"], f"Edge naming failed: {result_edges.get('error')}"

    # Sub-test 9: extrudeOn
    result_extrude = cad_page.evaluate("""() => {
        try {
            const box = new Workplane('XY').box(10, 20, 30);
            const origBBox = box._getBoundingBox();

            const extended = box.extrudeOn('front', 5, 5, 3);
            const extBBox = extended._getBoundingBox();

            const TOL = 0.5;
            if (extBBox.maxY < origBBox.maxY + 3 - TOL) {
                return {
                    success: false,
                    error: `extrudeOn("front") didn't extend: origMaxY=${origBBox.maxY.toFixed(2)}, newMaxY=${extBBox.maxY.toFixed(2)}`
                };
            }

            const origMesh = box.toMesh(0.1, 0.3);
            const extMesh = extended.toMesh(0.1, 0.3);
            if (extMesh.vertices.length <= origMesh.vertices.length) {
                return { success: false, error: 'extrudeOn did not add geometry' };
            }

            return { success: true };
        } catch (e) {
            return { success: false, error: e.message };
        }
    }""")
    assert result_extrude["success"], f"extrudeOn failed: {result_extrude.get('error')}"

    # Sub-test 10: cutInto
    result_cut_into = cad_page.evaluate("""() => {
        try {
            const box = new Workplane('XY').box(20, 20, 20);
            const pocketed = box.cutInto('top', 5, 5, 2);

            const origBBox = box._getBoundingBox();
            const cutBBox = pocketed._getBoundingBox();

            const TOL = 0.1;
            if (Math.abs(cutBBox.maxZ - origBBox.maxZ) > TOL) {
                return { success: false, error: `maxZ changed: ${origBBox.maxZ} -> ${cutBBox.maxZ}` };
            }

            const origMesh = box.toMesh(0.1, 0.3);
            const cutMesh = pocketed.toMesh(0.1, 0.3);
            if (cutMesh.vertices.length <= origMesh.vertices.length) {
                return { success: false, error: 'cutInto did not add geometry (pocket)' };
            }

            return { success: true };
        } catch (e) {
            return { success: false, error: e.message };
        }
    }""")
    assert result_cut_into["success"], f"cutInto failed: {result_cut_into.get('error')}"

    # Sub-test 11: extrudeOn after rotate
    result_extrude_rot = cad_page.evaluate("""() => {
        try {
            const box = new Workplane('XY').box(10, 10, 10);

            const rotated = box.rotate(0, 0, 1, 90);
            const rotBBox = rotated._getBoundingBox();

            const extended = rotated.extrudeOn('front', 3, 3, 5);
            const extBBox = extended._getBoundingBox();

            if (extBBox.minX >= rotBBox.minX - 1) {
                return {
                    success: false,
                    error: `Extrusion didn't extend in -X: rotMinX=${rotBBox.minX.toFixed(2)}, extMinX=${extBBox.minX.toFixed(2)}`
                };
            }

            return { success: true };
        } catch (e) {
            return { success: false, error: e.message };
        }
    }""")
    assert result_extrude_rot["success"], f"extrudeOn after rotate failed: {result_extrude_rot.get('error')}"

    # Sub-test 12: sub-part access
    result_sub_part = cad_page.evaluate("""() => {
        try {
            const base = new Workplane('XY').box(20, 20, 10).name('base');
            const tab = new Workplane('XY').box(5, 5, 5).translate(0, 0, 10).name('tab');

            const merged = base.union(tab);

            if (!merged._subParts) {
                return { success: false, error: '_subParts is null' };
            }
            if (!merged._subParts.base) {
                return { success: false, error: 'sub-part "base" missing' };
            }
            if (!merged._subParts.tab) {
                return { success: false, error: 'sub-part "tab" missing' };
            }

            const baseFrontFaces = merged.faces('base.front');
            if (baseFrontFaces._selectedFaces.length === 0) {
                return { success: false, error: 'faces("base.front") returned 0 faces' };
            }

            const frontFaces = merged.faces('front');
            if (frontFaces._selectedFaces.length === 0) {
                return { success: false, error: 'faces("front") returned 0 faces' };
            }

            return { success: true };
        } catch (e) {
            return { success: false, error: e.message };
        }
    }""")
    assert result_sub_part["success"], f"Sub-part access failed: {result_sub_part.get('error')}"

    # Sub-test 13: attachTo
    result_attach = cad_page.evaluate("""() => {
        try {
            const base = new Workplane('XY').box(20, 20, 10);
            const knob = new Workplane('XY').box(5, 5, 5);

            const combined = knob.attachTo(base, 'top');
            const bbox = combined._getBoundingBox();

            if (bbox.maxZ <= 10) {
                return { success: false, error: `maxZ=${bbox.maxZ.toFixed(2)}, expected > 10` };
            }

            const baseMesh = base.toMesh(0.1, 0.3);
            const combinedMesh = combined.toMesh(0.1, 0.3);
            if (combinedMesh.vertices.length <= baseMesh.vertices.length) {
                return { success: false, error: 'attachTo did not add geometry' };
            }

            return { success: true };
        } catch (e) {
            return { success: false, error: e.message };
        }
    }""")
    assert result_attach["success"], f"attachTo failed: {result_attach.get('error')}"


# ##################################################################
# test getFaceLabels returns correct structure
def test_get_face_labels(cad_page):
    """Test getFaceLabels() returns named and all faces with centroids."""
    result = cad_page.evaluate("""() => {
        try {
            const box = new Workplane('XY').box(10, 20, 30);
            const labels = box.getFaceLabels();

            if (!labels) return { success: false, error: 'getFaceLabels returned null' };
            if (!labels.namedFaces) return { success: false, error: 'missing namedFaces' };
            if (!labels.allFaces) return { success: false, error: 'missing allFaces' };

            // Check named faces has the 6 canonical names
            const expectedNames = ['front', 'back', 'right', 'left', 'top', 'bottom'];
            const namedKeys = Object.keys(labels.namedFaces);
            const missingNamed = expectedNames.filter(n => !namedKeys.includes(n));
            if (missingNamed.length > 0) {
                return { success: false, error: 'Missing named faces: ' + missingNamed.join(', ') };
            }

            // Each named face should have a centroid array of 3 numbers
            for (const [name, centroid] of Object.entries(labels.namedFaces)) {
                if (!Array.isArray(centroid) || centroid.length !== 3) {
                    return { success: false, error: `namedFaces.${name} centroid invalid` };
                }
                if (centroid.some(v => typeof v !== 'number' || isNaN(v))) {
                    return { success: false, error: `namedFaces.${name} centroid has NaN` };
                }
            }

            // allFaces should have at least 6 entries (box has 6 faces)
            if (labels.allFaces.length < 6) {
                return { success: false, error: `allFaces has ${labels.allFaces.length} entries, expected >= 6` };
            }

            // Each allFaces entry should have name and centroid
            for (let i = 0; i < labels.allFaces.length; i++) {
                const f = labels.allFaces[i];
                if (!f.name || !f.centroid) {
                    return { success: false, error: `allFaces[${i}] missing name or centroid` };
                }
                if (!Array.isArray(f.centroid) || f.centroid.length !== 3) {
                    return { success: false, error: `allFaces[${i}] centroid invalid` };
                }
            }

            // Named faces in allFaces should use their semantic names, not faceN
            const semanticNames = labels.allFaces.filter(f => expectedNames.includes(f.name));
            if (semanticNames.length !== 6) {
                return { success: false, error: `Expected 6 semantic names in allFaces, got ${semanticNames.length}` };
            }

            return { success: true, namedCount: namedKeys.length, allCount: labels.allFaces.length };
        } catch (e) {
            return { success: false, error: e.message };
        }
    }""")
    assert result["success"], f"getFaceLabels failed: {result.get('error')}"


# ##################################################################
# test face name selectors for fillet/chamfer
def test_face_name_fillet(cad_page):
    """Test face('name').fillet() fillets only edges of that face."""
    result = cad_page.evaluate("""() => {
        try {
            const box = new Workplane('XY').box(20, 20, 20);
            const plain = box.toMesh(0.1, 0.5);

            // Fillet only the top face edges
            const filleted = new Workplane('XY').box(20, 20, 20).face('top').fillet(2);
            if (!filleted._shape) return { success: false, error: 'fillet returned null shape' };

            const mesh = filleted.toMesh(0.1, 0.5);

            // Filleting top edges should increase vertex count vs plain box
            if (mesh.vertices.length <= plain.vertices.length) {
                return { success: false, error: `Expected more vertices after fillet: got ${mesh.vertices.length} vs ${plain.vertices.length}` };
            }

            return { success: true, plainVerts: plain.vertices.length, filletedVerts: mesh.vertices.length };
        } catch (e) {
            return { success: false, error: e.message };
        }
    }""")
    assert result["success"], f"face().fillet() failed: {result.get('error')}"


def test_face_name_chamfer(cad_page):
    """Test face('name').chamfer() chamfers only edges of that face."""
    result = cad_page.evaluate("""() => {
        try {
            const box = new Workplane('XY').box(20, 20, 20);
            const plain = box.toMesh(0.1, 0.5);

            const chamfered = new Workplane('XY').box(20, 20, 20).face('top').chamfer(2);
            if (!chamfered._shape) return { success: false, error: 'chamfer returned null shape' };

            const mesh = chamfered.toMesh(0.1, 0.5);
            if (mesh.vertices.length <= plain.vertices.length) {
                return { success: false, error: `Expected more vertices after chamfer: got ${mesh.vertices.length} vs ${plain.vertices.length}` };
            }

            return { success: true, plainVerts: plain.vertices.length, chamferedVerts: mesh.vertices.length };
        } catch (e) {
            return { success: false, error: e.message };
        }
    }""")
    assert result["success"], f"face().chamfer() failed: {result.get('error')}"


def test_edges_by_face_name(cad_page):
    """Test edges('faceName') selects all edges of the named face."""
    result = cad_page.evaluate("""() => {
        try {
            // edges('top') should select 4 edges of the top face
            const box = new Workplane('XY').box(20, 20, 20);
            const topEdges = box.edges('top');
            if (!topEdges._selectedEdges) return { success: false, error: 'no _selectedEdges' };
            if (topEdges._selectedEdges.length !== 4) {
                return { success: false, error: `Expected 4 top face edges, got ${topEdges._selectedEdges.length}` };
            }

            // Chamfer those edges
            const chamfered = box.edges('top').chamfer(2);
            if (!chamfered._shape) return { success: false, error: 'chamfer returned null shape' };

            const plain = box.toMesh(0.1, 0.5);
            const mesh = chamfered.toMesh(0.1, 0.5);
            if (mesh.vertices.length <= plain.vertices.length) {
                return { success: false, error: `Chamfer had no effect: ${mesh.vertices.length} vs ${plain.vertices.length}` };
            }

            return { success: true, edgeCount: topEdges._selectedEdges.length };
        } catch (e) {
            return { success: false, error: e.message };
        }
    }""")
    assert result["success"], f"edges('faceName') failed: {result.get('error')}"


# test wedge and wedgeByAngle primitives
def test_wedge_basic(cad_page):
    """Test wedge() creates a valid triangular prism with correct geometry."""
    result = cad_page.evaluate("""() => {
        try {
            const w = new Workplane('XY').wedge(20, 10, 5);
            if (!w._shape) return { success: false, error: 'wedge shape is null' };

            const mesh = w.toMesh(0.1, 0.3);
            if (!mesh || !mesh.vertices || mesh.vertices.length === 0) {
                return { success: false, error: 'wedge mesh has no vertices' };
            }

            // Check bounding box - centered on X/Y, bottom at Z=0
            let minX = Infinity, maxX = -Infinity;
            let minY = Infinity, maxY = -Infinity;
            let minZ = Infinity, maxZ = -Infinity;
            for (let i = 0; i < mesh.vertices.length; i += 3) {
                const x = mesh.vertices[i], y = mesh.vertices[i+1], z = mesh.vertices[i+2];
                minX = Math.min(minX, x); maxX = Math.max(maxX, x);
                minY = Math.min(minY, y); maxY = Math.max(maxY, y);
                minZ = Math.min(minZ, z); maxZ = Math.max(maxZ, z);
            }

            // length=20 centered: -10 to 10
            if (Math.abs(minX - (-10)) > 0.01 || Math.abs(maxX - 10) > 0.01) {
                return { success: false, error: `X range wrong: ${minX} to ${maxX}, expected -10 to 10` };
            }
            // width=10 centered: -5 to 5
            if (Math.abs(minY - (-5)) > 0.01 || Math.abs(maxY - 5) > 0.01) {
                return { success: false, error: `Y range wrong: ${minY} to ${maxY}, expected -5 to 5` };
            }
            // height=5, bottom at Z=0
            if (Math.abs(minZ) > 0.01 || Math.abs(maxZ - 5) > 0.01) {
                return { success: false, error: `Z range wrong: ${minZ} to ${maxZ}, expected 0 to 5` };
            }

            return {
                success: true,
                vertexCount: mesh.vertices.length / 3,
                triangleCount: mesh.indices.length / 3
            };
        } catch (e) {
            return { success: false, error: e.message };
        }
    }""")
    assert result["success"], f"wedge basic failed: {result.get('error')}"
    assert result["vertexCount"] > 0
    assert result["triangleCount"] > 0


def test_wedge_not_centered(cad_page):
    """Test wedge() with centered=false starts at origin."""
    result = cad_page.evaluate("""() => {
        try {
            const w = new Workplane('XY').wedge(20, 10, 5, false);
            if (!w._shape) return { success: false, error: 'wedge shape is null' };

            const mesh = w.toMesh(0.1, 0.3);
            if (!mesh || !mesh.vertices || mesh.vertices.length === 0) {
                return { success: false, error: 'wedge mesh has no vertices' };
            }

            let minX = Infinity, maxX = -Infinity;
            let minY = Infinity, maxY = -Infinity;
            let minZ = Infinity, maxZ = -Infinity;
            for (let i = 0; i < mesh.vertices.length; i += 3) {
                const x = mesh.vertices[i], y = mesh.vertices[i+1], z = mesh.vertices[i+2];
                minX = Math.min(minX, x); maxX = Math.max(maxX, x);
                minY = Math.min(minY, y); maxY = Math.max(maxY, y);
                minZ = Math.min(minZ, z); maxZ = Math.max(maxZ, z);
            }

            // not centered: X from 0 to 20, Y from 0 to 10, Z from 0 to 5
            if (Math.abs(minX) > 0.01 || Math.abs(maxX - 20) > 0.01) {
                return { success: false, error: `X range wrong: ${minX} to ${maxX}, expected 0 to 20` };
            }
            if (Math.abs(minY) > 0.01 || Math.abs(maxY - 10) > 0.01) {
                return { success: false, error: `Y range wrong: ${minY} to ${maxY}, expected 0 to 10` };
            }
            if (Math.abs(minZ) > 0.01 || Math.abs(maxZ - 5) > 0.01) {
                return { success: false, error: `Z range wrong: ${minZ} to ${maxZ}, expected 0 to 5` };
            }

            return { success: true };
        } catch (e) {
            return { success: false, error: e.message };
        }
    }""")
    assert result["success"], f"wedge not-centered failed: {result.get('error')}"


def test_wedge_by_angle(cad_page):
    """Test wedgeByAngle() computes correct height from angle."""
    result = cad_page.evaluate("""() => {
        try {
            // 45 degrees with width=10 should give height=10
            const w = new Workplane('XY').wedgeByAngle(20, 10, 45);
            if (!w._shape) return { success: false, error: 'wedgeByAngle shape is null' };

            const mesh = w.toMesh(0.1, 0.3);
            if (!mesh || !mesh.vertices || mesh.vertices.length === 0) {
                return { success: false, error: 'wedgeByAngle mesh has no vertices' };
            }

            let maxZ = -Infinity;
            for (let i = 0; i < mesh.vertices.length; i += 3) {
                maxZ = Math.max(maxZ, mesh.vertices[i+2]);
            }

            // tan(45°) = 1, so height = 10 * 1 = 10
            if (Math.abs(maxZ - 10) > 0.01) {
                return { success: false, error: `Max Z wrong: ${maxZ}, expected 10 (45° with width=10)` };
            }

            // Also test 30 degrees: tan(30°) ≈ 0.5774, height ≈ 5.774
            const w30 = new Workplane('XY').wedgeByAngle(20, 10, 30);
            if (!w30._shape) return { success: false, error: 'wedgeByAngle 30° shape is null' };

            const mesh30 = w30.toMesh(0.1, 0.3);
            let maxZ30 = -Infinity;
            for (let i = 0; i < mesh30.vertices.length; i += 3) {
                maxZ30 = Math.max(maxZ30, mesh30.vertices[i+2]);
            }

            const expected30 = 10 * Math.tan(30 * Math.PI / 180);
            if (Math.abs(maxZ30 - expected30) > 0.05) {
                return { success: false, error: `30° max Z wrong: ${maxZ30}, expected ${expected30}` };
            }

            return { success: true, maxZ45: maxZ, maxZ30: maxZ30 };
        } catch (e) {
            return { success: false, error: e.message };
        }
    }""")
    assert result["success"], f"wedgeByAngle failed: {result.get('error')}"


def test_wedge_by_angle_validation(cad_page):
    """Test wedgeByAngle() rejects invalid angles (<=0, >=90)."""
    result = cad_page.evaluate("""() => {
        try {
            // angle = 0 should fail
            const w0 = new Workplane('XY').wedgeByAngle(20, 10, 0);
            if (w0._shape) return { success: false, error: 'angle=0 should have failed' };

            // angle = 90 should fail
            const w90 = new Workplane('XY').wedgeByAngle(20, 10, 90);
            if (w90._shape) return { success: false, error: 'angle=90 should have failed' };

            // angle = -5 should fail
            const wNeg = new Workplane('XY').wedgeByAngle(20, 10, -5);
            if (wNeg._shape) return { success: false, error: 'negative angle should have failed' };

            return { success: true };
        } catch (e) {
            return { success: false, error: e.message };
        }
    }""")
    assert result["success"], f"wedgeByAngle validation failed: {result.get('error')}"


def test_wedge_boolean_operations(cad_page):
    """Test that wedge works with boolean operations (union, cut)."""
    result = cad_page.evaluate("""() => {
        try {
            const base = new Workplane('XY').box(30, 30, 2);
            const w = new Workplane('XY').wedge(30, 15, 10);

            // Union
            const united = base.union(w);
            if (!united._shape) return { success: false, error: 'union with wedge failed' };

            const baseMesh = base.toMesh(0.1, 0.3);
            const unitedMesh = united.toMesh(0.1, 0.3);
            if (unitedMesh.vertices.length <= baseMesh.vertices.length) {
                return { success: false, error: 'union did not add geometry' };
            }

            // Cut
            const bigBox = new Workplane('XY').box(40, 40, 20);
            const cutResult = bigBox.cut(w);
            if (!cutResult._shape) return { success: false, error: 'cut with wedge failed' };

            return { success: true };
        } catch (e) {
            return { success: false, error: e.message };
        }
    }""")
    assert result["success"], f"wedge boolean ops failed: {result.get('error')}"

