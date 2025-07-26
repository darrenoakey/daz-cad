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

    scene.add(new THREE.GridHelper(100, 20, 0x444444, 0x222222));
    
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
    
    // Add X and Y labels at the end of the axes
    const xLabel = createAxisLabel('X', new THREE.Vector3(22, 0, 0), '#ff0000');
    const yLabel = createAxisLabel('Y', new THREE.Vector3(0, 22, 0), '#00ff00');
    scene.add(xLabel);
    scene.add(yLabel);

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
    
    if (transform && transform.length === 16) {
        const matrix = new THREE.Matrix4();
        matrix.set(
            transform[0], transform[1], transform[2], transform[3],
            transform[4], transform[5], transform[6], transform[7],
            transform[8], transform[9], transform[10], transform[11],
            transform[12], transform[13], transform[14], transform[15]
        );
        mesh.applyMatrix4(matrix);
        console.log(`Applied transform to ${name}:`, transform);
    } else {
        geometry.computeBoundingBox();
        const center = new THREE.Vector3();
        geometry.boundingBox.getCenter(center);
        geometry.translate(-center.x, -center.y, -center.z);
    }
    scene.add(mesh);
    currentObjects.push(mesh);
    fitCameraToObjects();
}

function fitCameraToObjects() {
    if (currentObjects.length === 0) return;
    const box = new THREE.Box3();
    currentObjects.forEach(obj => box.expandByObject(obj));
    const center = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3());
    const maxDim = Math.max(size.x, size.y, size.z);
    const fov = camera.fov * (Math.PI / 180);
    const cameraZ = Math.abs(maxDim / (2 * Math.tan(fov / 2))) * 1.5;
    camera.position.set(center.x + cameraZ, center.y + cameraZ, center.z + cameraZ);
    camera.lookAt(center);
    controls.target = center;
    controls.update();
}
