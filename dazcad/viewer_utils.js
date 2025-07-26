/*
 * ================================================================================
 * DazCAD Viewer Utilities - Text and Axis Label Functions
 * ================================================================================
 * 
 * This module contains utility functions for creating text textures and axis labels
 * in the 3D viewer. These functions support the Z-up coordinate system used by DazCAD.
 */

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
