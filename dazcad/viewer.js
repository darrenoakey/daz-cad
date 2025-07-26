function initViewer() {
    // Set Three.js to use Z-up coordinate system to match CadQuery
    THREE.Object3D.DefaultUp = new THREE.Vector3(0, 0, 1);
    
    const container = document.getElementById('viewer3d');
    const w = container.clientWidth;
    const h = container.clientHeight;

    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0a0a0a);
    scene.fog = new THREE.Fog(0x0a0a0a, 200, 1000);

    camera = new THREE.PerspectiveCamera(45, w / h, 0.1, 1000);
    camera.position.set(50, 50, 50);

    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(w, h);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    container.appendChild(renderer.domElement);

    controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;

    scene.add(new THREE.AmbientLight(0x404040, 2));

    const dirLight = new THREE.DirectionalLight(0xffffff, 1);
    dirLight.position.set(50, 100, 50);
    dirLight.castShadow = true;
    dirLight.shadow.camera.near = 0.1;
    dirLight.shadow.camera.far = 500;
    dirLight.shadow.camera.left = -100;
    dirLight.shadow.camera.right = 100;
    dirLight.shadow.camera.top = 100;
    dirLight.shadow.camera.bottom = -100;
    scene.add(dirLight);

    // Create grid in XY plane (rotated from default XZ plane)
    const grid = new THREE.GridHelper(100, 20, 0x444444, 0x222222);
    grid.rotateX(Math.PI / 2); // Rotate to XY plane to match CadQuery
    scene.add(grid);
    
    // Create custom axes with correct CadQuery coordinate system
    const axesGroup = new THREE.Group();
    
    // X-axis (Red in CadQuery coordinate system)
    const xGeometry = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(0, 0, 0),
        new THREE.Vector3(20, 0, 0)
    ]);
    const xMaterial = new THREE.LineBasicMaterial({ color: 0xff0000 });
    const xLine = new THREE.Line(xGeometry, xMaterial);
    axesGroup.add(xLine);
    
    // Y-axis (Green in CadQuery coordinate system)
    const yGeometry = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(0, 0, 0),
        new THREE.Vector3(0, 20, 0)
    ]);
    const yMaterial = new THREE.LineBasicMaterial({ color: 0x00ff00 });
    const yLine = new THREE.Line(yGeometry, yMaterial);
    axesGroup.add(yLine);
    
    // Z-axis (Blue in CadQuery coordinate system)
    const zGeometry = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(0, 0, 0),
        new THREE.Vector3(0, 0, 20)
    ]);
    const zMaterial = new THREE.LineBasicMaterial({ color: 0x0000ff });
    const zLine = new THREE.Line(zGeometry, zMaterial);
    axesGroup.add(zLine);
    
    scene.add(axesGroup);
    
    // Add X, Y, and Z labels at the end of the axes
    const xLabel = createAxisLabel('X', new THREE.Vector3(22, 0, 0), '#ff0000');
    const yLabel = createAxisLabel('Y', new THREE.Vector3(0, 22, 0), '#00ff00');
    const zLabel = createAxisLabel('Z', new THREE.Vector3(0, 0, 22), '#0000ff');
    scene.add(xLabel);
    scene.add(yLabel);
    scene.add(zLabel);

    window.addEventListener('resize', onWindowResize, false);
    animate();
}