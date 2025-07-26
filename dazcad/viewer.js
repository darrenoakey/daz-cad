function fitCameraToObjects() {
    if (currentObjects.length === 0) return;
    const box = new THREE.Box3();
    currentObjects.forEach(obj => box.expandByObject(obj));
    const center = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3());
    const maxDim = Math.max(size.x, size.y, size.z);
    const fov = camera.fov * (Math.PI / 180);
    // Increase the multiplier to zoom out more and show more of the grid
    const cameraZ = Math.abs(maxDim / (2 * Math.tan(fov / 2))) * 3.0;
    camera.position.set(center.x + cameraZ, center.y + cameraZ, center.z + cameraZ);
    camera.lookAt(center);
    controls.target = center;
    controls.update();
}