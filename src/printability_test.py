import pytest


@pytest.fixture(scope="session")
def printability_page(init_page):
    init_page.evaluate("""async () => {
        const cad = await import('/static/cad.js');
        cad.initCAD(window.oc);
        window.Workplane = cad.Workplane;
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
