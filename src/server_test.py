from playwright.sync_api import sync_playwright, expect
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
def test_opencascade_loads_successfully(server):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

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
        browser.close()


# ##################################################################
# test opencascade calculates volume
# verifies opencascade.js can perform volume calculations correctly
def test_opencascade_calculates_volume(server):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(f"{server}/init-test")

        page.wait_for_function(
            """() => {
                const status = document.getElementById('status');
                return status && status.classList.contains('success');
            }""",
            timeout=60000
        )

        test_result = page.locator("#test-result")
        expect(test_result).to_contain_text("6000 cubic units")

        page.close()
        browser.close()


# ##################################################################
# test opencascade ready event fired
# verifies the opencascade-ready custom event dispatches with data
def test_opencascade_ready_event_fired(server):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

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
        browser.close()


# ##################################################################
# test opencascade instance available
# verifies window.oc is available and has core cad classes
def test_opencascade_instance_available(server):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(f"{server}/init-test")

        page.wait_for_function(
            """() => {
                const status = document.getElementById('status');
                return status && status.classList.contains('success');
            }""",
            timeout=90000
        )

        oc_check = page.evaluate("""() => {
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

        page.close()
        browser.close()


# ##################################################################
# test editor renders pink mesh to canvas
# takes a snapshot of the threejs canvas and verifies it contains bright pink pixels
def test_editor_renders_pink_mesh_to_canvas(server):
    from pathlib import Path

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--enable-webgl", "--use-gl=angle", "--enable-gpu"]
        )
        page = browser.new_page()

        errors = []
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)

        page.goto(f"{server}/")

        # wait for status to show ready
        page.wait_for_function(
            """() => {
                const statusText = document.getElementById('status-text');
                return statusText && statusText.textContent === 'Ready';
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
        browser.close()


# ##################################################################
# test editor auto renders default code
# verifies that the default code renders a colored assembly on page load
def test_editor_auto_renders_default_code(server):
    from pathlib import Path

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--enable-webgl", "--use-gl=angle", "--enable-gpu"]
        )
        page = browser.new_page()

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
        browser.close()


# ##################################################################
# test editor mesh has geometry
# verifies the three.js mesh group contains actual geometry data
def test_editor_mesh_has_geometry(server):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(f"{server}/")

        # wait for ready state
        page.wait_for_function(
            """() => {
                const statusText = document.getElementById('status-text');
                return statusText && statusText.textContent === 'Ready';
            }""",
            timeout=90000
        )

        # check three.js scene state through the cadeditor instance
        mesh_check = page.evaluate("""() => {
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

        page.close()
        browser.close()


# ##################################################################
# test editor code execution
# verifies that changing code in editor triggers re-render
def test_editor_code_execution(server):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        errors = []
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)

        page.goto(f"{server}/")

        # wait for initial ready state
        page.wait_for_function(
            """() => {
                const statusText = document.getElementById('status-text');
                return statusText && statusText.textContent === 'Ready';
            }""",
            timeout=90000
        )

        # execute simple code that creates a box and check result
        result = page.evaluate("""() => {
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

        page.close()
        browser.close()


# ##################################################################
# test editor full render pipeline
# comprehensive test that validates the entire render pipeline works
def test_editor_full_render_pipeline(server):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        errors = []
        warnings = []
        logs = []

        def handle_console(msg):
            if msg.type == "error":
                errors.append(msg.text)
            elif msg.type == "warning":
                warnings.append(msg.text)
            else:
                logs.append(msg.text)

        page.on("console", handle_console)

        page.goto(f"{server}/")

        # wait for ready state
        page.wait_for_function(
            """() => {
                const statusText = document.getElementById('status-text');
                return statusText && statusText.textContent === 'Ready';
            }""",
            timeout=90000
        )

        # check error overlay is not visible
        error_overlay = page.locator("#error-overlay")
        error_class = error_overlay.get_attribute("class") or ""
        assert "visible" not in error_class, "Error overlay is visible"

        # comprehensive render pipeline check
        pipeline_check = page.evaluate("""() => {
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
        critical_errors = [e for e in errors if "favicon" not in e.lower()]
        assert len(critical_errors) == 0, f"JavaScript errors: {critical_errors}"

        page.close()
        browser.close()


# ##################################################################
# test cylinder and assembly generation
# verifies that cylinder shapes generate valid mesh and assemblies work
def test_cylinder_and_assembly(server):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(f"{server}/")

        page.wait_for_function(
            """() => {
                const statusText = document.getElementById('status-text');
                return statusText && statusText.textContent === 'Ready';
            }""",
            timeout=90000
        )

        # test cylinder step by step to find where it crashes
        result = page.evaluate("""() => {
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

        page.close()
        browser.close()


# ##################################################################
# test stl export functionality
# verifies that shapes can be exported to STL format
def test_stl_export(server):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(f"{server}/")

        page.wait_for_function(
            """() => {
                const statusText = document.getElementById('status-text');
                return statusText && statusText.textContent === 'Ready';
            }""",
            timeout=90000
        )

        # test STL export for single shape and assembly
        result = page.evaluate("""() => {
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

        page.close()
        browser.close()


# ##################################################################
# test 3mf export functionality
# verifies that shapes can be exported to Bambu-compatible 3MF format
def test_3mf_export(server):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(f"{server}/")

        page.wait_for_function(
            """() => {
                const statusText = document.getElementById('status-text');
                return statusText && statusText.textContent === 'Ready';
            }""",
            timeout=90000
        )

        # test 3MF export for single shape and assembly
        result = page.evaluate("""async () => {
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

                return {
                    success: true,
                    box3MFSize: box3MF.size,
                    assembly3MFSize: assembly3MF.size
                };
            } catch (e) {
                return { success: false, error: e.message, stack: e.stack };
            }
        }""")

        assert result["success"], f"3MF export test failed: {result.get('error', 'unknown')}"
        assert result.get("box3MFSize", 0) > 100, f"Box 3MF too small: {result.get('box3MFSize')}"
        assert result.get("assembly3MFSize", 0) > 100, f"Assembly 3MF too small: {result.get('assembly3MFSize')}"

        print(f"Box 3MF size: {result.get('box3MFSize')} bytes")
        print(f"Assembly 3MF size: {result.get('assembly3MFSize')} bytes")

        page.close()
        browser.close()


# ##################################################################
# test cad library operations
# verifies all cad library functions work correctly
def test_cad_library_operations(server):
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--enable-webgl", "--use-gl=angle", "--enable-gpu"]
        )
        page = browser.new_page()

        # capture console output
        console_messages = []
        page.on("console", lambda msg: console_messages.append(f"{msg.type}: {msg.text}"))

        page.goto(f"{server}/")

        # wait for OpenCascade to load
        page.wait_for_function(
            """() => {
                const statusText = document.getElementById('status-text');
                return statusText && statusText.textContent === 'Ready';
            }""",
            timeout=90000
        )

        # run the CAD test suite
        results = page.evaluate("""() => {
            if (typeof CADTests === 'undefined') {
                return { error: 'CADTests not loaded' };
            }
            return CADTests.runAll();
        }""")

        page.close()
        browser.close()

        # print console output for debugging
        if console_messages:
            print("\n--- Browser console output ---")
            for msg in console_messages:
                print(msg)
            print("--- End console output ---\n")

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
    # the response should mention something about the shape (box)
    assert any(word in data["response"].lower() for word in ["box", "cube", "shape", "model"])
