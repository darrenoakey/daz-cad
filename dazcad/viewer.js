/*
 * DazCAD 3D Viewer - Z-UP Coordinate System Implementation
 * 
 * 🚨 CRITICAL: This viewer uses Z-UP coordinate system to match CadQuery/OpenCascade
 * 📖 READ coordinate_system_docs.js for COMPREHENSIVE documentation before making changes!
 * 
 * Key Rules:
 * 1. THREE.Object3D.DefaultUp = new THREE.Vector3(0, 0, 1) - NEVER change this!
 * 2. Grid MUST be rotated to XY plane: grid.rotateX(Math.PI / 2)
 * 3. Apply backend transformations directly - no coordinate conversion!
 * 4. Camera positioned isometrically: (X, Y, Z) not (0, 0, Z)
 */

let scene, camera, renderer, controls;
let currentObjects = [];

function createTextTexture(text, color = '#ffffff') {
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');
    canvas.width = 64;
    canvas.height = 64;
    context.fillStyle = 'transparent';
    context.fillRect(0, 0, canvas.width, canvas.height);
    context.font = 'bold 48px Arial';
    context.fillStyle = color;
    context.textAlign = 'center';
    context.textBaseline = 'middle';
    context.fillText(text, canvas.width / 2, canvas.height / 2);
    const texture = new THREE.CanvasTexture(canvas);
    texture.needsUpdate = true;
    return texture;
}

function createAxisLabel(text, position, color) {
    const texture = createTextTexture(text, color);
    const spriteMaterial = new THREE.SpriteMaterial({
        map: texture,
        transparent: true
    });
    const sprite = new THREE.Sprite(spriteMaterial);
    sprite.position.copy(position);
    sprite.scale.set(4, 4, 1);
    return sprite;
}

function initViewer() {
    // 🚨 CRITICAL: Set Z-up coordinate system - MUST be first line!
    // See coordinate_system_docs.js for detailed explanation
    THREE.Object3D.DefaultUp = new THREE.Vector3(0, 0, 1);
    
    console.log('🔧 Coordinate System: Z-up initialized');
    console.log('📖 See coordinate_system_docs.js for comprehensive documentation');
    
    const container = document.getElementById('viewer3d');
    const w = container.clientWidth;
    const h = container.clientHeight;

    // Create scene with dark background suitable for CAD visualization
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0a0a0a);
    scene.fog = new THREE.Fog(0x0a0a0a, 200, 1000);

    // Setup camera - isometric view to show all three axes
    camera = new THREE.PerspectiveCamera(45, w / h, 0.1, 1000);
    camera.position.set(80, 80, 80); // Classic CAD isometric view
    
    // Create renderer with antialiasing
    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(w, h);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    container.appendChild(renderer.domElement);

    // Setup orbit controls (automatically respects Z-up)
    controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;

    // Add lighting
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

    // 🚨 CRITICAL: Create grid in XY plane (Z=0) to match CAD workplane
    const grid = new THREE.GridHelper(100, 20, 0x444444, 0x222222);
    grid.rotateX(Math.PI / 2); // Rotate from XZ to XY plane
    scene.add(grid);
    
    // Add Z-axis reference line (vertical in Z-up world)
    const zGeometry = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(0, 0, 0),
        new THREE.Vector3(0, 0, 50)
    ]);
    const zMaterial = new THREE.LineBasicMaterial({ color: 0x444444 });
    const zLine = new THREE.Line(zGeometry, zMaterial);
    scene.add(zLine);
    
    // Add axis labels with standard CAD colors: RGB = XYZ
    const xLabel = createAxisLabel('X', new THREE.Vector3(55, 0, 0), '#ff0000');  // Red
    const yLabel = createAxisLabel('Y', new THREE.Vector3(0, 55, 0), '#00ff00');  // Green  
    const zLabel = createAxisLabel('Z', new THREE.Vector3(0, 0, 55), '#0000ff');  // Blue
    scene.add(xLabel);
    scene.add(yLabel);
    scene.add(zLabel);

    // Setup responsive behavior and start render loop
    window.addEventListener('resize', onWindowResize, false);
    animate();
}

function onWindowResize() {
    const container = document.getElementById('viewer3d');
    const w = container.clientWidth;
    const h = container.clientHeight;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
}

function animate() {
    requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
}

function clearScene() {
    currentObjects.forEach(obj => scene.remove(obj));
    currentObjects = [];
}

function loadSTL(stlData, name, color, transform) {
    console.log(`🔧 Loading STL: ${name}`);
    
    const loader = new THREE.STLLoader();
    const binaryString = atob(stlData);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
    }
    const geometry = loader.parse(bytes.buffer);
    const material = new THREE.MeshPhongMaterial({
        color: new THREE.Color(color),
        specular: 0x111111,
        shininess: 200
    });
    const mesh = new THREE.Mesh(geometry, material);
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    mesh.name = name;
    
    // 🚨 CRITICAL: Handle transformations in Z-up coordinate system
    if (transform && transform.length === 16) {
        // Extract translation from row-major matrix (backend format)
        // See coordinate_system_docs.js for detailed matrix explanation
        const tx = transform[3];  // X translation (right/left)
        const ty = transform[7];  // Y translation (forward/back)  
        const tz = transform[11]; // Z translation (up/down)
        
        // Apply directly - no coordinate conversion needed!
        mesh.position.set(tx, ty, tz);
        console.log(`🔧 Applied transform: (${tx}, ${ty}, ${tz})`);
        
        // TODO: Add rotation/scaling extraction for advanced assemblies
    } else {
        // 🖨️ 3D PRINTING: Position objects on build plate (z=0)
        geometry.computeBoundingBox();
        const center = new THREE.Vector3();
        geometry.boundingBox.getCenter(center);
        
        // Center in X and Y for good viewing, but place on build plate for 3D printing
        // Move minimum Z to z=0 so object sits on build plate
        const minZ = geometry.boundingBox.min.z;
        geometry.translate(-center.x, -center.y, -minZ);
        console.log(`🔧 Positioned object on build plate: centered XY, min Z -> 0 (was ${minZ.toFixed(2)})`);
    }
    
    scene.add(mesh);
    currentObjects.push(mesh);
    fitCameraToObjects();
}

function fitCameraToObjects() {
    if (currentObjects.length === 0) return;
    
    // Calculate bounding box and position camera isometrically
    const box = new THREE.Box3();
    currentObjects.forEach(obj => box.expandByObject(obj));
    const center = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3());
    const maxDim = Math.max(size.x, size.y, size.z);
    
    const fov = camera.fov * (Math.PI / 180);
    const cameraZ = Math.abs(maxDim / (2 * Math.tan(fov / 2))) * 3.0;
    
    // Maintain isometric view in Z-up coordinate system
    camera.position.set(center.x + cameraZ, center.y + cameraZ, center.z + cameraZ);
    camera.lookAt(center);
    controls.target = center;
    controls.update();
}
