/*
 * DazCAD Coordinate System - Common Mistakes and Debugging Guide
 * 
 * This file contains the most common mistakes developers make with the Z-up
 * coordinate system and how to debug coordinate system issues.
 */

/*
 * ===============================================================================
 * COMMON MISTAKES AND HOW TO AVOID THEM
 * ===============================================================================
 * 
 * 🚫 CRITICAL MISTAKES THAT WILL BREAK EVERYTHING:
 * 
 * ❌ DON'T change THREE.Object3D.DefaultUp to (0,1,0) - this breaks Z-up!
 * ❌ DON'T remove grid.rotateX(Math.PI/2) - models appear to be lying on side!
 * ❌ DON'T swap Y and Z coordinates "to fix" orientation - fix in backend!
 * ❌ DON'T use Three.js Y-up tutorials or examples without adapting them!
 * ❌ DON'T modify transformation matrices to "convert" coordinate systems!
 * ❌ DON'T position camera at (0,0,Z) only - use isometric (X,Y,Z) view!
 * ❌ DON'T use lookAt() with up vector (0,1,0) - this forces Y-up!
 * 
 * 🚫 SUBTLE MISTAKES THAT CAUSE CONFUSION:
 * 
 * ❌ DON'T change axis label colors - users expect RGB = XYZ convention
 * ❌ DON'T move grid away from Z=0 plane - it represents CAD workplane
 * ❌ DON'T use OrbitControls with Y-up target calculations
 * ❌ DON'T assume Three.js examples work without Z-up modifications
 * ❌ DON'T center objects by moving the camera instead of the geometry
 * 
 * ✅ CORRECT PRACTICES TO MAINTAIN COORDINATE SYSTEM INTEGRITY:
 * 
 * ✅ DO preserve Z-up coordinate system throughout the entire application
 * ✅ DO apply backend transformations exactly as received (no conversion)
 * ✅ DO center single objects using geometry.translate(), not mesh.position
 * ✅ DO position assemblies using transformation matrices from backend
 * ✅ DO maintain RGB=XYZ axis color convention for user familiarity
 * ✅ DO use isometric camera positioning (equal X,Y,Z distances from origin)
 * ✅ DO test with simple shapes (boxes) to verify coordinate system works
 * ✅ DO document any new coordinate-related code with detailed comments
 * 
 * ===============================================================================
 * DEBUGGING COORDINATE SYSTEM ISSUES
 * ===============================================================================
 * 
 * If models appear rotated, positioned incorrectly, or the view looks wrong:
 * 
 * 🔍 Step 1: Check the Up Vector
 *    console.log('DefaultUp:', THREE.Object3D.DefaultUp);
 *    // Should log: Vector3 {x: 0, y: 0, z: 1}
 *    // If it shows {x: 0, y: 1, z: 0}, the coordinate system is broken!
 * 
 * 🔍 Step 2: Verify Grid Orientation  
 *    // Grid should appear horizontal (like a floor), not vertical (like a wall)
 *    // Check that grid.rotateX(Math.PI/2) is being called
 * 
 * 🔍 Step 3: Check Transformation Matrix Application
 *    console.log('Transform matrix:', transform);
 *    console.log('Extracted translation:', [transform[3], transform[7], transform[11]]);
 *    // Verify translations are being applied to mesh.position correctly
 * 
 * 🔍 Step 4: Verify Camera Position and Target
 *    console.log('Camera position:', camera.position);
 *    console.log('Camera target:', controls.target);
 *    // Camera should be at positive X,Y,Z, looking at center point
 * 
 * 🔍 Step 5: Test with Simple Geometry
 *    // Create a simple box and verify it appears correctly oriented
 *    // Box should sit on grid, not penetrate it or float above it
 * 
 * 🔍 Step 6: Check Scene Up Vector After Object Addition
 *    // Some operations can accidentally reset the up vector
 *    // Verify it's still (0,0,1) after loading models
 * 
 * ===============================================================================
 * COORDINATE SYSTEM TESTING CHECKLIST
 * ===============================================================================
 * 
 * Before merging any changes that affect coordinate handling:
 * 
 * □ Create a simple box at origin - it should sit on the grid
 * □ Create a box at (10, 20, 30) - it should be right, away, and up
 * □ Load an assembly - parts should maintain their relative positions  
 * □ Check axis labels - X=Red/Right, Y=Green/Away, Z=Blue/Up
 * □ Camera should show isometric view with all axes visible
 * □ Grid should appear as horizontal floor, not vertical wall
 * □ Export a model and reimport - position should be identical
 * □ Compare with CAD software view - orientation should match
 */
