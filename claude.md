# daz-cad-2 Project Guide

## Overview
Browser-based CAD application using OpenCascade.js for 3D modeling. JavaScript CAD library with CadQuery-like API.

## Key Files
- `static/patterns.js` - cutPattern() API for cutting shapes into faces
- `static/cad.js` - Core Workplane class and CAD operations
- `static/viewer.js` - Three.js 3D viewer
- `static/editor.js` - Monaco editor integration
- `static/cad-library-spec.md` - API docs sent to Claude agent for code generation
- `src/server_test.py` - Playwright-based E2E tests

## Testing
- Run tests: `python -m pytest src/server_test.py -v`
- Tests use Playwright and require a running server (pytest fixture handles this)
- Tests use `page.evaluate()` to run JavaScript in browser context
- Pattern tests verify cutting by comparing mesh vertex counts before/after
- **Mesh format:** `toMesh()` returns `{ vertices, indices, color, isModifier }` (not `position`)

## cutPattern() Architecture
- Cutters are created at Z=0 extending in +Z direction
- `_createFaceTransform()` rotates/translates cutters to align with any face
- For non-Z faces, rotation maps +Z to the face's inward normal direction
- X-aligned faces need extra 90° pre-rotation for lines (so length runs in Y)
- `spacing` parameter = gap between shapes (not center-to-center)
- Default spacing = width (50% solid, 50% cut)
- **Cutters are fused before cutting** - eliminates internal faces when shapes overlap
- This fixes hexagon patterns with thin wallThickness that would otherwise fail
- **Clipping for non-rectangular faces:**
  - `clip: 'partial'` - clips shapes at face boundary (partial shapes at edges)
  - `clip: 'whole'` - only keeps shapes fully inside (volume comparison check)
  - `_createOffsetFace()` handles border inset:
    - Circles: shrinks radius by border distance
    - Polygons: edge-based offset using `BRepTools_WireExplorer` for vertex ordering,
      computes inward normals per edge, finds intersections of adjacent offset edges
  - Clip solid extends both above and below face to fully contain cutters

## Geometry Optimization
- `clean()` method merges coplanar faces and collinear edges
- Uses `ShapeUpgrade_UnifySameDomain` and `ShapeFix_Shape`
- Call after complex boolean operations to simplify geometry
- Options: `{ unifyFaces, unifyEdges, fix, rebuildSolid }`

## Edge Selectors
- Simple: `|Z` (parallel to Z), `<X` (min X), `>Y` (max Y)
- Compound with "and": `edges("<X and <Y")` - intersection (edges matching ALL)
- Compound with "or": `edges("<X or |Z")` - union (edges matching ANY)
- Use `edgesNot()` to exclude: `edgesNot("|Z")` gets all non-vertical edges
- Chain operations: `box.edges("|Z").fillet(3).edgesNot("|Z").fillet(1)`

## Non-Uniform Scaling (Ellipsoid Pattern)
- `gp_GTrsf` + `BRepBuilderAPI_GTransform` for non-uniform scaling of shapes
- Used by `ellipsoid()`: creates unit sphere, scales by (rx, ry, rz)
- This pattern works for any shape that needs independent axis scaling

## Common Issues
- Face normal detection uses `BRepAdaptor_Surface.D1()` with cross product
- Check `face.Orientation_1()` for reversed faces that need normal flip
- Boolean cuts can fail silently - verify by checking mesh vertex counts
- Browser caching: NoCacheMiddleware adds no-cache headers to all /static/* files

## Version Control
- `local/models/` directory is auto-initialized as a git repo on server startup
- Every successful model save auto-commits with AI-generated message (Claude Haiku)
- Commits run in background task to not block save response
- Uses `claude-agent-sdk` with `model="haiku"` for commit message generation
- Error handling: falls back to simple "Update filename" message if Claude SDK fails

## Conventions
- Dimensions in millimeters
- Result variable must be defined in CAD scripts
- Colors as hex strings: `.color("#3498db")`
