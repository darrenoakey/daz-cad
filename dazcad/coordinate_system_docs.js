/*
 * ================================================================================
 * DazCAD 3D Viewer - CRITICAL Coordinate System Documentation
 * ================================================================================
 * 
 * 🚨 ABSOLUTELY CRITICAL COORDINATE SYSTEM INFORMATION 🚨
 * READ THIS COMPLETELY BEFORE MAKING ANY CHANGES OR YOU WILL BREAK EVERYTHING!
 * 
 * This viewer uses a Z-UP coordinate system to match CadQuery/OpenCascade conventions.
 * Three.js defaults to Y-UP, so we must be EXTREMELY careful about coordinate transformations.
 * 
 * 📖 RELATED DOCUMENTATION FILES:
 * - coordinate_system_debug.js - Common mistakes and debugging guide
 * - See viewer.js for the actual implementation with key comments
 * 
 * ===============================================================================
 * COORDINATE SYSTEM OVERVIEW
 * ===============================================================================
 * 
 * CadQuery/OpenCascade (Backend):    Three.js Default (Frontend):    DazCAD Viewer (What we use):
 * ┌─────────────────────────────┐   ┌─────────────────────────────┐   ┌─────────────────────────────┐
 * │ - X: Right (+X) →           │   │ - X: Right (+X) →           │   │ - X: Right (+X) →           │
 * │ - Y: Forward/Away (+Y) ↑    │   │ - Y: Up (+Y) ↑              │   │ - Y: Forward/Away (+Y) ↑    │
 * │ - Z: Up (+Z) ⬆              │   │ - Z: Forward/Away (+Z) ↑    │   │ - Z: Up (+Z) ⬆              │
 * │                             │   │                             │   │                             │
 * │ This is OpenCascade/CAD     │   │ This is WebGL/game engine   │   │ This matches CAD exactly    │
 * │ standard used worldwide     │   │ standard                    │   │ DO NOT CHANGE THIS!         │
 * └─────────────────────────────┘   └─────────────────────────────┘   └─────────────────────────────┘
 * 
 * ===============================================================================
 * WHY THIS MATTERS - REAL WORLD CONSEQUENCES OF GETTING THIS WRONG
 * ===============================================================================
 * 
 * ❌ If you change the coordinate system:
 *    - All models will appear sideways or upside down
 *    - Assembly positioning will be completely wrong
 *    - Grid will be in the wrong plane
 *    - Users will be confused about which way is "up"
 *    - CAD files exported from other software won't display correctly
 *    - Transformation matrices from backend will be applied incorrectly
 * 
 * ✅ By keeping Z-UP:
 *    - Models appear exactly as they do in CAD software
 *    - Grid represents the XY "workplane" that CAD users expect
 *    - Assembly transformations work correctly
 *    - Export/import with other CAD software is seamless
 *    - Users can intuitively understand the 3D space
 * 
 * ===============================================================================
 * CRITICAL TRANSFORMATIONS AND RULES
 * ===============================================================================
 * 
 * 1. 🚨 SCENE UP VECTOR - THE MOST IMPORTANT LINE IN THE VIEWER:
 *    
 *    THREE.Object3D.DefaultUp = new THREE.Vector3(0, 0, 1);
 *    
 *    - This MUST be the first thing we do in initViewer()
 *    - This tells Three.js that "up" is the Z-axis, not Y-axis
 *    - Changing this breaks EVERYTHING - models, camera, controls, grid
 *    - If you see models sideways, check this line first!
 *    - This affects ALL objects added to the scene afterwards
 * 
 * 2. 🚨 GRID ORIENTATION - CRITICAL FOR USER SPATIAL UNDERSTANDING:
 *    
 *    const grid = new THREE.GridHelper(100, 20, 0x444444, 0x222222);
 *    grid.rotateX(Math.PI / 2); // CRITICAL: Rotate 90° to XY plane
 *    
 *    - Three.js GridHelper creates a grid in the XZ plane (horizontal with Y-up)
 *    - We rotate it 90° around X-axis to place it in XY plane (Z=0)
 *    - This matches CadQuery's default XY workplane where Z=0
 *    - If you remove this rotation, the grid appears vertical like a wall!
 *    - The grid represents the "ground" or base plane for CAD models
 * 
 * 3. 🚨 TRANSFORMATION MATRICES - BACKEND TO FRONTEND DATA FLOW:
 *    
 *    Backend (CadQuery) Matrix Format (Row-Major):
 *    [m11, m12, m13, m14]    ← Row 1: X-axis rotation/scale + X translation
 *    [m21, m22, m23, m24]    ← Row 2: Y-axis rotation/scale + Y translation  
 *    [m31, m32, m33, m34]    ← Row 3: Z-axis rotation/scale + Z translation
 *    [m41, m42, m43, m44]    ← Row 4: Perspective (usually [0,0,0,1])
 *    
 *    Translation Extraction:
 *    - tx = matrix[3]  = m14 (X translation: left/right movement)
 *    - ty = matrix[7]  = m24 (Y translation: forward/back movement)  
 *    - tz = matrix[11] = m34 (Z translation: up/down movement)
 *    
 *    🚨 CRITICAL: Apply these translations DIRECTLY - no coordinate conversion!
 *    The backend already sends data in the correct Z-up coordinate system.
 * 
 * 4. 🚨 AXIS LABELS AND VISUAL REFERENCES:
 *    
 *    - X-axis: RED label at (55, 0, 0) - points right (standard CAD convention)
 *    - Y-axis: GREEN label at (0, 55, 0) - points away from viewer  
 *    - Z-axis: BLUE label at (0, 0, 55) - points up (standard CAD convention)
 *    - Colors follow RGB = XYZ mnemonic: Red=X, Green=Y, Blue=Z
 *    - Labels positioned outside 100x100 grid so they're always visible
 *    - Z-axis line draws from (0,0,0) to (0,0,50) showing vertical reference
 * 
 * ===============================================================================
 * PERFORMANCE CONSIDERATIONS
 * ===============================================================================
 * 
 * The Z-up coordinate system choice affects performance:
 * 
 * ✅ BENEFITS:
 * - No coordinate conversion overhead during rendering
 * - Direct application of backend matrices (no transformation math)
 * - Geometry centering is one-time operation, not per-frame
 * - Camera calculations remain simple (no axis swapping)
 * 
 * 🚨 WHAT NOT TO DO (performance killers):
 * - Don't convert coordinates in animation loop
 * - Don't recalculate transformations every frame
 * - Don't modify DefaultUp vector during runtime
 * - Don't apply coordinate conversion matrices to geometry
 * 
 * Remember: The goal is to match the backend coordinate system exactly,
 * so minimal frontend transformation is needed.
 * 
 * 📖 For debugging issues and common mistakes, see coordinate_system_debug.js
 */

// This file is documentation only - see viewer.js for the actual implementation
