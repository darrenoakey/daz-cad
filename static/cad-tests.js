/**
 * CAD Library Test Suite
 *
 * Tests all CAD operations to verify they actually modify geometry.
 * Run via: CADTests.runAll() in browser console after editor loads
 */

class CADTests {
    static results = [];

    static log(name, passed, details = '') {
        const status = passed ? 'PASS' : 'FAIL';
        const msg = `[${status}] ${name}${details ? ': ' + details : ''}`;
        console.log(msg);
        this.results.push({ name, passed, details });
    }

    static getMeshStats(workplane) {
        if (!workplane || !workplane._shape) return null;
        const mesh = workplane.toMesh(0.1, 0.3);
        if (!mesh) return null;
        return {
            vertexCount: mesh.vertices.length / 3,
            triangleCount: mesh.indices.length / 3,
            vertices: mesh.vertices
        };
    }

    static getBoundingBox(workplane) {
        if (!workplane || !workplane._shape) return null;
        const mesh = workplane.toMesh(0.1, 0.3);
        if (!mesh || !mesh.vertices) return null;

        let minX = Infinity, minY = Infinity, minZ = Infinity;
        let maxX = -Infinity, maxY = -Infinity, maxZ = -Infinity;

        for (let i = 0; i < mesh.vertices.length; i += 3) {
            minX = Math.min(minX, mesh.vertices[i]);
            maxX = Math.max(maxX, mesh.vertices[i]);
            minY = Math.min(minY, mesh.vertices[i + 1]);
            maxY = Math.max(maxY, mesh.vertices[i + 1]);
            minZ = Math.min(minZ, mesh.vertices[i + 2]);
            maxZ = Math.max(maxZ, mesh.vertices[i + 2]);
        }

        return {
            minX, minY, minZ, maxX, maxY, maxZ,
            sizeX: maxX - minX,
            sizeY: maxY - minY,
            sizeZ: maxZ - minZ
        };
    }

    // Test: box creates geometry
    static testBox() {
        const box = new Workplane("XY").box(20, 30, 40);
        const stats = this.getMeshStats(box);
        const bbox = this.getBoundingBox(box);

        const hasGeometry = stats && stats.vertexCount > 0 && stats.triangleCount > 0;
        const correctSize = bbox &&
            Math.abs(bbox.sizeX - 20) < 0.1 &&
            Math.abs(bbox.sizeY - 30) < 0.1 &&
            Math.abs(bbox.sizeZ - 40) < 0.1;

        this.log('box', hasGeometry && correctSize,
            `vertices: ${stats?.vertexCount}, size: ${bbox?.sizeX?.toFixed(1)}x${bbox?.sizeY?.toFixed(1)}x${bbox?.sizeZ?.toFixed(1)}`);
        return hasGeometry && correctSize;
    }

    // Test: cylinder creates geometry
    static testCylinder() {
        const cyl = new Workplane("XY").cylinder(10, 30);
        const stats = this.getMeshStats(cyl);
        const bbox = this.getBoundingBox(cyl);

        const hasGeometry = stats && stats.vertexCount > 0;
        const correctHeight = bbox && Math.abs(bbox.sizeZ - 30) < 0.1;
        const correctDiameter = bbox && Math.abs(bbox.sizeX - 20) < 1; // diameter = 2*radius

        this.log('cylinder', hasGeometry && correctHeight && correctDiameter,
            `vertices: ${stats?.vertexCount}, height: ${bbox?.sizeZ?.toFixed(1)}, diameter: ${bbox?.sizeX?.toFixed(1)}`);
        return hasGeometry && correctHeight;
    }

    // Test: sphere creates geometry
    static testSphere() {
        const sphere = new Workplane("XY").sphere(15);
        const stats = this.getMeshStats(sphere);
        const bbox = this.getBoundingBox(sphere);

        const hasGeometry = stats && stats.vertexCount > 0;
        const correctSize = bbox && Math.abs(bbox.sizeX - 30) < 1; // diameter = 2*radius

        this.log('sphere', hasGeometry && correctSize,
            `vertices: ${stats?.vertexCount}, diameter: ${bbox?.sizeX?.toFixed(1)}`);
        return hasGeometry && correctSize;
    }

    // Test: hole removes material
    static testHole() {
        const boxBefore = new Workplane("XY").box(20, 20, 20);
        const boxWithHole = new Workplane("XY").box(20, 20, 20).hole(8);

        const statsBefore = this.getMeshStats(boxBefore);
        const statsAfter = this.getMeshStats(boxWithHole);

        // Hole should add more vertices/triangles (for the hole surface)
        const changed = statsAfter && statsBefore &&
            statsAfter.vertexCount !== statsBefore.vertexCount;

        this.log('hole', changed,
            `vertices before: ${statsBefore?.vertexCount}, after: ${statsAfter?.vertexCount}`);
        return changed;
    }

    // Test: chamfer modifies edges
    static testChamfer() {
        const boxBefore = new Workplane("XY").box(20, 20, 20);
        const boxWithChamfer = new Workplane("XY").box(20, 20, 20).chamfer(2);

        const statsBefore = this.getMeshStats(boxBefore);
        const statsAfter = this.getMeshStats(boxWithChamfer);

        // Chamfer should change vertex count
        const changed = statsAfter && statsBefore &&
            statsAfter.vertexCount !== statsBefore.vertexCount;

        this.log('chamfer', changed,
            `vertices before: ${statsBefore?.vertexCount}, after: ${statsAfter?.vertexCount}`);
        return changed;
    }

    // Test: fillet modifies edges
    static testFillet() {
        const boxBefore = new Workplane("XY").box(20, 20, 20);
        const boxWithFillet = new Workplane("XY").box(20, 20, 20).fillet(2);

        const statsBefore = this.getMeshStats(boxBefore);
        const statsAfter = this.getMeshStats(boxWithFillet);

        // Fillet should change vertex count (add curved surface vertices)
        const changed = statsAfter && statsBefore &&
            statsAfter.vertexCount !== statsBefore.vertexCount;

        this.log('fillet', changed,
            `vertices before: ${statsBefore?.vertexCount}, after: ${statsAfter?.vertexCount}`);
        return changed;
    }

    // Test: translate moves geometry
    static testTranslate() {
        const box = new Workplane("XY").box(10, 10, 10);
        const boxMoved = new Workplane("XY").box(10, 10, 10).translate(50, 0, 0);

        const bboxBefore = this.getBoundingBox(box);
        const bboxAfter = this.getBoundingBox(boxMoved);

        const moved = bboxBefore && bboxAfter &&
            Math.abs(bboxAfter.minX - bboxBefore.minX - 50) < 0.1;

        this.log('translate', moved,
            `minX before: ${bboxBefore?.minX?.toFixed(1)}, after: ${bboxAfter?.minX?.toFixed(1)}`);
        return moved;
    }

    // Test: rotate changes geometry orientation
    static testRotate() {
        const box = new Workplane("XY").box(10, 20, 5);
        const boxRotated = new Workplane("XY").box(10, 20, 5).rotate(0, 0, 1, 90);

        const bboxBefore = this.getBoundingBox(box);
        const bboxAfter = this.getBoundingBox(boxRotated);

        // After 90 degree rotation around Z, X and Y sizes should swap
        const rotated = bboxBefore && bboxAfter &&
            Math.abs(bboxAfter.sizeX - bboxBefore.sizeY) < 0.5 &&
            Math.abs(bboxAfter.sizeY - bboxBefore.sizeX) < 0.5;

        this.log('rotate', rotated,
            `before: ${bboxBefore?.sizeX?.toFixed(1)}x${bboxBefore?.sizeY?.toFixed(1)}, after: ${bboxAfter?.sizeX?.toFixed(1)}x${bboxAfter?.sizeY?.toFixed(1)}`);
        return rotated;
    }

    // Test: union combines shapes
    static testUnion() {
        const box1 = new Workplane("XY").box(10, 10, 10);
        const box2 = new Workplane("XY").box(10, 10, 10).translate(5, 0, 0);
        const combined = box1.union(box2);

        const bbox1 = this.getBoundingBox(box1);
        const bboxCombined = this.getBoundingBox(combined);

        // Combined should be wider
        const wider = bbox1 && bboxCombined && bboxCombined.sizeX > bbox1.sizeX;

        this.log('union', wider,
            `width before: ${bbox1?.sizeX?.toFixed(1)}, after: ${bboxCombined?.sizeX?.toFixed(1)}`);
        return wider;
    }

    // Test: cut removes material
    static testCut() {
        const box1 = new Workplane("XY").box(20, 20, 20);
        const box2 = new Workplane("XY").box(10, 10, 30); // tall thin box through center
        const cutResult = box1.cut(box2);

        const statsBefore = this.getMeshStats(box1);
        const statsAfter = this.getMeshStats(cutResult);

        // Cut should change the geometry
        const changed = statsBefore && statsAfter &&
            statsAfter.vertexCount !== statsBefore.vertexCount;

        this.log('cut', changed,
            `vertices before: ${statsBefore?.vertexCount}, after: ${statsAfter?.vertexCount}`);
        return changed;
    }

    // Test: intersect keeps only overlap
    static testIntersect() {
        const box1 = new Workplane("XY").box(20, 20, 20);
        const box2 = new Workplane("XY").box(20, 20, 20).translate(10, 0, 0);
        const intersected = box1.intersect(box2);

        const bbox1 = this.getBoundingBox(box1);
        const bboxIntersect = this.getBoundingBox(intersected);

        // Intersection should be smaller
        const smaller = bbox1 && bboxIntersect && bboxIntersect.sizeX < bbox1.sizeX;

        this.log('intersect', smaller,
            `width before: ${bbox1?.sizeX?.toFixed(1)}, after: ${bboxIntersect?.sizeX?.toFixed(1)}`);
        return smaller;
    }

    // Test: color sets color property
    static testColor() {
        const box = new Workplane("XY").box(10, 10, 10).color("#ff0000");
        const mesh = box.toMesh(0.1, 0.3);

        const hasColor = mesh && mesh.color === "#ff0000";

        this.log('color', hasColor, `color: ${mesh?.color}`);
        return hasColor;
    }

    // Test: Assembly combines multiple parts
    static testAssembly() {
        const part1 = new Workplane("XY").box(10, 10, 10).color("#ff0000");
        const part2 = new Workplane("XY").cylinder(5, 15).translate(20, 0, 0).color("#00ff00");
        const assembly = new Assembly().add(part1).add(part2);

        const meshes = assembly.toMesh(0.1, 0.3);
        const hasTwoParts = meshes && meshes.length === 2;
        const hasColors = hasTwoParts && meshes[0].color && meshes[1].color;

        this.log('assembly', hasTwoParts && hasColors,
            `parts: ${meshes?.length}, colors: ${meshes?.map(m => m.color).join(', ')}`);
        return hasTwoParts && hasColors;
    }

    // Test: faces selection
    static testFacesSelection() {
        const box = new Workplane("XY").box(20, 20, 20);
        const topFaces = box.faces(">Z");

        const hasSelection = topFaces._selectedFaces && topFaces._selectedFaces.length > 0;

        this.log('faces selection', hasSelection,
            `selected faces: ${topFaces._selectedFaces?.length}`);
        return hasSelection;
    }

    // Test: edges selection
    static testEdgesSelection() {
        const box = new Workplane("XY").box(20, 20, 20);
        const topEdges = box.faces(">Z").edges();

        const hasSelection = topEdges._selectedEdges && topEdges._selectedEdges.length > 0;

        this.log('edges selection', hasSelection,
            `selected edges: ${topEdges._selectedEdges?.length}`);
        return hasSelection;
    }

    // Run all tests
    static runAll() {
        console.log('=== CAD Library Test Suite ===\n');
        this.results = [];

        const tests = [
            () => this.testBox(),
            () => this.testCylinder(),
            () => this.testSphere(),
            () => this.testHole(),
            () => this.testChamfer(),
            () => this.testFillet(),
            () => this.testTranslate(),
            () => this.testRotate(),
            () => this.testUnion(),
            () => this.testCut(),
            () => this.testIntersect(),
            () => this.testColor(),
            () => this.testAssembly(),
            () => this.testFacesSelection(),
            () => this.testEdgesSelection(),
        ];

        for (const test of tests) {
            try {
                test();
            } catch (e) {
                console.error(`Test threw error: ${e.message}`);
                this.results.push({ name: 'unknown', passed: false, details: e.message });
            }
        }

        const passed = this.results.filter(r => r.passed).length;
        const failed = this.results.filter(r => !r.passed).length;

        console.log(`\n=== Results: ${passed} passed, ${failed} failed ===`);

        if (failed > 0) {
            console.log('\nFailed tests:');
            this.results.filter(r => !r.passed).forEach(r => {
                console.log(`  - ${r.name}: ${r.details}`);
            });
        }

        return { passed, failed, results: this.results };
    }
}

// Export for use
window.CADTests = CADTests;
