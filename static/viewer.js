/**
 * Three.js CAD Viewer
 *
 * Provides 3D visualization of CAD geometry with orbit controls,
 * grid, and proper lighting.
 */

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

class CADViewer {
    constructor(container) {
        this.container = container;
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;
        this.meshGroup = null;
        this._userHasInteracted = false; // Track if user has moved/zoomed the view

        this._init();
        this._animate();
    }

    _init() {
        // Scene
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x1a1a2e);

        // Camera - CAD convention: Z is up
        const aspect = this.container.clientWidth / this.container.clientHeight;
        this.camera = new THREE.PerspectiveCamera(45, aspect, 0.1, 10000);
        this.camera.up.set(0, 0, 1);
        this.camera.position.set(30, -30, 30);
        this.camera.lookAt(0, 0, 0);

        // Renderer - preserveDrawingBuffer needed for screenshots and pixel reading
        this.renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
        this.renderer.setSize(this.container.clientWidth, this.container.clientHeight);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.container.appendChild(this.renderer.domElement);

        // Controls - CAD convention: Z is up
        this.controls = new OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.05;

        // Track when user manually interacts with the view
        this.controls.addEventListener('start', () => {
            this._userHasInteracted = true;
        });

        // Lighting - positioned for Z-up view
        const ambientLight = new THREE.AmbientLight(0x404040, 0.5);
        this.scene.add(ambientLight);

        const directionalLight1 = new THREE.DirectionalLight(0xffffff, 0.8);
        directionalLight1.position.set(50, -50, 50);
        this.scene.add(directionalLight1);

        const directionalLight2 = new THREE.DirectionalLight(0xffffff, 0.4);
        directionalLight2.position.set(-50, 50, 50);
        this.scene.add(directionalLight2);

        // Grid on XY plane (Z=0) - CAD convention
        this._addXYGrid(100, 20);

        // Custom thick axes - double length (30 units)
        this._addThickAxes(30, 0.3);

        // Axis labels - positioned past end of axes
        this._addAxisLabels(33);

        // Group for meshes
        this.meshGroup = new THREE.Group();
        this.scene.add(this.meshGroup);

        // Handle resize
        window.addEventListener('resize', () => this._onResize());

        // Initial resize
        this._onResize();
    }

    _onResize() {
        const width = this.container.clientWidth;
        const height = this.container.clientHeight;

        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(width, height);
    }

    _animate() {
        requestAnimationFrame(() => this._animate());
        this.controls.update();
        this.renderer.render(this.scene, this.camera);
    }

    /**
     * Clear all meshes from the viewer
     */
    clear() {
        this._disposeGroup(this.meshGroup);
    }

    /**
     * Reset the view flag so next render will fit camera
     */
    resetView() {
        this._userHasInteracted = false;
    }

    /**
     * Display a mesh or array of meshes from CAD geometry
     * @param {Object|Array} meshData - Object with vertices/indices/color, or array of such objects
     */
    displayMesh(meshData) {
        // Create new meshes first (before removing old ones to reduce flicker)
        const newMeshGroup = new THREE.Group();

        // Handle array of meshes (assembly)
        const meshes = Array.isArray(meshData) ? meshData : [meshData];

        for (const data of meshes) {
            if (!data || !data.vertices || !data.indices) {
                console.warn('Invalid mesh data in assembly');
                continue;
            }

            // Create geometry
            const geometry = new THREE.BufferGeometry();
            geometry.setAttribute('position', new THREE.BufferAttribute(data.vertices, 3));
            geometry.setIndex(new THREE.BufferAttribute(data.indices, 1));
            geometry.computeVertexNormals();

            // Parse color - default to bright pink if not specified
            let color = 0xff1493;
            if (data.color) {
                color = this._parseColor(data.color);
            }

            // Material for solid
            const solidMaterial = new THREE.MeshPhongMaterial({
                color: color,
                shininess: 30,
                side: THREE.DoubleSide
            });

            // Create mesh
            const mesh = new THREE.Mesh(geometry, solidMaterial);
            newMeshGroup.add(mesh);

            // Add wireframe overlay
            const wireframeMaterial = new THREE.MeshBasicMaterial({
                color: 0x003344,
                wireframe: true,
                transparent: true,
                opacity: 0.1
            });
            const wireframe = new THREE.Mesh(geometry.clone(), wireframeMaterial);
            newMeshGroup.add(wireframe);
        }

        // Swap: add new group, then remove old one (minimizes flicker)
        this.scene.add(newMeshGroup);
        this._disposeGroup(this.meshGroup);
        this.scene.remove(this.meshGroup);
        this.meshGroup = newMeshGroup;

        // Fit camera unless user has manually moved/zoomed the view
        if (!this._userHasInteracted && this.meshGroup.children.length > 0) {
            this._fitCameraToObject(this.meshGroup);
        }
    }

    /**
     * Dispose of all meshes in a group (cleanup GPU resources)
     */
    _disposeGroup(group) {
        while (group.children.length > 0) {
            const mesh = group.children[0];
            if (mesh.geometry) mesh.geometry.dispose();
            if (mesh.material) {
                if (Array.isArray(mesh.material)) {
                    mesh.material.forEach(m => m.dispose());
                } else {
                    mesh.material.dispose();
                }
            }
            group.remove(mesh);
        }
    }

    /**
     * Parse a color value to Three.js format
     * @param {string|number} color - CSS hex color string or number
     */
    _parseColor(color) {
        if (typeof color === 'number') {
            return color;
        }
        if (typeof color === 'string') {
            // Handle CSS hex colors like "#ff0000"
            if (color.startsWith('#')) {
                return parseInt(color.slice(1), 16);
            }
            // Handle named colors via Three.js
            const c = new THREE.Color(color);
            return c.getHex();
        }
        return 0xff1493; // default pink
    }

    /**
     * Display an edge wireframe (for debugging)
     */
    displayEdges(meshData) {
        if (!meshData || !meshData.vertices || !meshData.indices) return;

        const geometry = new THREE.BufferGeometry();
        geometry.setAttribute('position', new THREE.BufferAttribute(meshData.vertices, 3));
        geometry.setIndex(new THREE.BufferAttribute(meshData.indices, 1));

        const edges = new THREE.EdgesGeometry(geometry, 15);
        const line = new THREE.LineSegments(
            edges,
            new THREE.LineBasicMaterial({ color: 0x00ff00 })
        );
        this.meshGroup.add(line);
    }

    /**
     * Fit camera to show the entire object - CAD convention with Z up
     */
    _fitCameraToObject(object) {
        const box = new THREE.Box3().setFromObject(object);
        const center = box.getCenter(new THREE.Vector3());
        const size = box.getSize(new THREE.Vector3());

        const maxDim = Math.max(size.x, size.y, size.z);

        // Guard against empty or invalid bounding box
        if (!maxDim || maxDim <= 0 || !isFinite(maxDim)) {
            this.camera.position.set(50, -50, 50);
            this.camera.lookAt(0, 0, 0);
            this.controls.target.set(0, 0, 0);
            this.controls.update();
            return;
        }

        const fov = this.camera.fov * (Math.PI / 180);
        let cameraDist = Math.abs(maxDim / 2 / Math.tan(fov / 2));
        cameraDist *= 2.5; // Zoom out a bit

        // Ensure minimum distance
        cameraDist = Math.max(cameraDist, 10);

        // Position camera for Z-up CAD view (looking from front-right-above)
        this.camera.position.set(
            center.x + cameraDist,
            center.y - cameraDist,
            center.z + cameraDist
        );
        this.camera.lookAt(center);
        this.controls.target.copy(center);
        this.controls.update();
    }

    /**
     * Create thick axes using boxes - easier positioning than cylinders
     * CAD convention: X=left/right (red), Y=into/out (green), Z=up/down (blue)
     */
    _addThickAxes(length, thickness) {
        // X axis (red) - box along X direction
        const xGeometry = new THREE.BoxGeometry(length, thickness, thickness);
        const xMaterial = new THREE.MeshBasicMaterial({ color: 0xff4444 });
        const xAxis = new THREE.Mesh(xGeometry, xMaterial);
        xAxis.position.set(length / 2, 0, 0);
        this.scene.add(xAxis);

        // Y axis (green) - box along Y direction
        const yGeometry = new THREE.BoxGeometry(thickness, length, thickness);
        const yMaterial = new THREE.MeshBasicMaterial({ color: 0x44ff44 });
        const yAxis = new THREE.Mesh(yGeometry, yMaterial);
        yAxis.position.set(0, length / 2, 0);
        this.scene.add(yAxis);

        // Z axis (blue) - box along Z direction (up)
        const zGeometry = new THREE.BoxGeometry(thickness, thickness, length);
        const zMaterial = new THREE.MeshBasicMaterial({ color: 0x4444ff });
        const zAxis = new THREE.Mesh(zGeometry, zMaterial);
        zAxis.position.set(0, 0, length / 2);
        this.scene.add(zAxis);
    }

    /**
     * Create grid on XY plane (Z=0) for CAD coordinate system
     */
    _addXYGrid(size, divisions) {
        const gridGroup = new THREE.Group();

        // Create grid lines
        const step = size / divisions;
        const halfSize = size / 2;

        const majorColor = new THREE.Color(0x444466);
        const minorColor = new THREE.Color(0x333344);

        // Lines parallel to X axis
        for (let i = 0; i <= divisions; i++) {
            const y = -halfSize + i * step;
            const isMajor = i === divisions / 2;
            const color = isMajor ? majorColor : minorColor;

            const geometry = new THREE.BufferGeometry().setFromPoints([
                new THREE.Vector3(-halfSize, y, 0),
                new THREE.Vector3(halfSize, y, 0)
            ]);
            const line = new THREE.Line(geometry, new THREE.LineBasicMaterial({ color }));
            gridGroup.add(line);
        }

        // Lines parallel to Y axis
        for (let i = 0; i <= divisions; i++) {
            const x = -halfSize + i * step;
            const isMajor = i === divisions / 2;
            const color = isMajor ? majorColor : minorColor;

            const geometry = new THREE.BufferGeometry().setFromPoints([
                new THREE.Vector3(x, -halfSize, 0),
                new THREE.Vector3(x, halfSize, 0)
            ]);
            const line = new THREE.Line(geometry, new THREE.LineBasicMaterial({ color }));
            gridGroup.add(line);
        }

        this.scene.add(gridGroup);
    }

    /**
     * Show error state - clears meshes and resets view for next successful render
     */
    showError() {
        this.clear();
        this.resetView(); // Next successful render will fit camera
    }

    /**
     * Create a text sprite for axis labels
     */
    _createTextSprite(text, color) {
        const canvas = document.createElement('canvas');
        const size = 128;
        canvas.width = size;
        canvas.height = size;

        const ctx = canvas.getContext('2d');
        ctx.fillStyle = color;
        ctx.font = 'bold 80px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(text, size / 2, size / 2);

        const texture = new THREE.CanvasTexture(canvas);
        const material = new THREE.SpriteMaterial({
            map: texture,
            transparent: true,
            depthTest: true
        });

        const sprite = new THREE.Sprite(material);
        sprite.scale.set(4, 4, 1);
        return sprite;
    }

    /**
     * Add X, Y, Z labels at end of axes
     */
    _addAxisLabels(distance) {
        const xLabel = this._createTextSprite('X', '#ff4444');
        xLabel.position.set(distance, 0, 0);
        this.scene.add(xLabel);

        const yLabel = this._createTextSprite('Y', '#44ff44');
        yLabel.position.set(0, distance, 0);
        this.scene.add(yLabel);

        const zLabel = this._createTextSprite('Z', '#4444ff');
        zLabel.position.set(0, 0, distance);
        this.scene.add(zLabel);
    }
}

export { CADViewer };
