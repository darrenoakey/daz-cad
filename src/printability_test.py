import pytest


@pytest.fixture(scope="session")
def printability_page(init_page):
    init_page.evaluate("""async () => {
        const cad = await import('/static/cad.js');
        cad.initCAD(window.oc);
        window.Workplane = cad.Workplane;
        window.Assembly = cad.Assembly;
        await import('/static/printability.js');
    }""")
    return init_page


# ##################################################################
# deterministic edge treatments on real OpenCascade solids
# proves both operations change valid geometry, retain an audit, preserve source,
# and honor a semantic mating-edge exclusion rather than just generating text.
def test_printability_transforms_real_solids_and_preserves_mating_edges(printability_page):
    result = printability_page.evaluate("""() => {
        const volume = (shape) => {
            const props = new oc.GProp_GProps_1();
            oc.BRepGProp.VolumeProperties_1(shape._shape, props, false, false, false);
            const mass = props.Mass(); props.delete(); return mass;
        };
        const isValid = (shape) => {
            const checker = new oc.BRepCheck_Analyzer(shape._shape, true, false);
            const answer = !shape._shape.IsNull() && checker.IsValid_2();
            checker.delete(); return answer;
        };
        const source = new Workplane('XY').box(30, 20, 12);
        const originalVolume = volume(source);
        const rounded = source.optimizeForPrinting({ verticalFillet: 1, baseChamfer: 0.4 });
        const mating = source.optimizeForPrinting({
            verticalFillet: 1, baseChamfer: 0.4, preserveEdges: ['<X and <Y'],
        });
        const baseOnly = source.optimizeForPrinting({ verticalFillet: 0, baseChamfer: 0.4 });
        return {
            originalVolume, roundedVolume: volume(rounded), matingVolume: volume(mating), baseVolume: volume(baseOnly),
            sourceUnchanged: volume(source) === originalVolume,
            valid: [rounded, mating, baseOnly].every(isValid),
            roundedChanges: rounded.printReport.changes,
            matingChanges: mating.printReport.changes,
            warnings: rounded.printReport.warnings,
            baseChanges: baseOnly.printReport.changes,
        };
    }""")
    assert result["sourceUnchanged"] and result["valid"]
    assert result["roundedVolume"] < result["originalVolume"]
    assert result["matingVolume"] > result["roundedVolume"]
    assert result["baseVolume"] < result["originalVolume"]
    assert {change["rule"] for change in result["roundedChanges"]} == {"base-chamfer", "vertical-fillet"}
    fillet = next(change for change in result["matingChanges"] if change["rule"] == "vertical-fillet")
    assert fillet["preserved"] == 1 and fillet["edges"] == 3
    assert [change["rule"] for change in result["baseChanges"]] == ["base-chamfer"]
    assert result["warnings"] and "do not certify" in result["warnings"][0]


# ##################################################################
# assemblies optimize every solid independently without flattening the model
# or losing project settings, part metadata, colors, and source geometry.
def test_printability_optimizes_assembly_parts_and_preserves_metadata(printability_page):
    result = printability_page.evaluate("""() => {
        const first = new Workplane('XY').box(30, 20, 12).walls(4).color('#e74c3c');
        const second = new Workplane('XY').box(16, 14, 10).translate(40, 0, 0).color('#2ecc71');
        const originalShapes = [first._shape, second._shape];
        const source = new Assembly().printSettings({ walls: 3, infillDensity: 20 }).add(first).add(second);
        const optimized = source.optimizeForPrinting({
            verticalFillet: 1, baseChamfer: 0.4, preserveEdges: ['<X and <Y'],
        });
        return {
            isAssembly: optimized.isAssembly,
            partCount: optimized._parts.length,
            colors: optimized._parts.map((part) => part._color),
            projectSettings: optimized._printSettings,
            firstWalls: optimized._parts[0]._meta.walls,
            originalsUnchanged: originalShapes.every((shape, index) => shape === source._parts[index]._shape),
            transformed: optimized._parts.every((part, index) => part._shape !== originalShapes[index]),
            reportParts: optimized.printReport.parts,
            reportPartIndexes: [...new Set(optimized.printReport.changes.map((change) => change.part))],
            warnings: optimized.printReport.warnings,
        };
    }""")
    assert result["isAssembly"] and result["partCount"] == 2
    assert result["colors"] == ["#e74c3c", "#2ecc71"]
    assert result["projectSettings"] == {"walls": 3, "infillDensity": 20}
    assert result["firstWalls"] == 4
    assert result["originalsUnchanged"] and result["transformed"]
    assert result["reportParts"] == 2 and result["reportPartIndexes"] == [1, 2]
    assert len(result["warnings"]) == 1


# ##################################################################
# incompatible assembly members are explicit skips, not a total-model rejection
# or a silent partial optimization. Other valid parts must still improve.
def test_printability_preserves_failed_assembly_part_with_warning(printability_page):
    result = printability_page.evaluate("""() => {
        const difficult = new Workplane('XY').cylinder(8, 25).color('#e74c3c');
        const simple = new Workplane('XY').box(12, 12, 15).translate(30, 0, 0).color('#2ecc71');
        const difficultShape = difficult._shape;
        const simpleShape = simple._shape;
        const optimized = new Assembly().add(difficult).add(simple).optimizeForPrinting({
            verticalFillet: 1, baseChamfer: 0.4, preserveEdges: ['<X and <Y'],
        });
        return {
            difficultUnchanged: optimized._parts[0]._shape === difficultShape,
            simpleTransformed: optimized._parts[1]._shape !== simpleShape,
            colors: optimized._parts.map((part) => part._color),
            unchangedParts: optimized.printReport.unchangedParts,
            warnings: optimized.printReport.warnings,
            changedParts: [...new Set(optimized.printReport.changes.map((change) => change.part))],
        };
    }""")
    assert result["difficultUnchanged"] and result["simpleTransformed"]
    assert result["colors"] == ["#e74c3c", "#2ecc71"]
    assert result["unchangedParts"] == [1] and result["changedParts"] == [2]
    assert any("Part 1 unchanged" in warning and "vertical fillet failed" in warning for warning in result["warnings"])


# ##################################################################
# invalid optimizer requests fail before returning an unchanged solid
# checks zero/negative/unknown selectors and geometric overreach so callers can
# preserve the user's editor instead of receiving silent partial success.
@pytest.mark.parametrize("options, message", [
    ({"verticalFillet": -1}, "non-negative"),
    ({"verticalFillet": 0, "baseChamfer": 0}, "enable"),
    ({"preserveEdges": ["not-a-selector"]}, "preserveEdges"),
    ({"verticalFillet": 100, "baseChamfer": 0}, "vertical fillet failed"),
])
def test_printability_rejects_unsafe_requests(printability_page, options, message):
    error = printability_page.evaluate("""(options) => {
        try {
            new Workplane('XY').box(30, 20, 12).optimizeForPrinting(options);
            return null;
        } catch (error) { return error.message; }
    }""", options)
    assert error and message in error
