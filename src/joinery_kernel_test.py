import pytest


# Real OC primitives must preserve volume and the full plane frame, including
# roll around the normal; a successful mesh alone does not establish either.
def test_joinery_kernel_frame_and_prism(init_page):
    result = init_page.evaluate(
        """async () => {
            const kernel = await import('/static/joinery-kernel.js');
            const frame = {origin:[3,4,5], u:[0,1,0], v:[0,0,1], n:[1,0,0]};
            const box = kernel.localBox(oc, frame, [2,3,4], [6,8,10]);
            const prism = kernel.localPrism(oc, frame, [[0,0],[4,0],[0,3]], 1, 6, 'v');
            try {
                return {
                    boxValid: kernel.valid(oc,box),
                    prismValid: kernel.valid(oc,prism),
                    boxVolume: kernel.volume(oc,box),
                    prismVolume: kernel.volume(oc,prism),
                    boxBounds: kernel.bounds(oc,box),
                    solids: [kernel.solidCount(oc,box),kernel.solidCount(oc,prism)]
                };
            } catch (error) {
                return {error: String(error), message: error.message, stack: error.stack};
            } finally { box.delete(); prism.delete(); }
        }"""
    )
    assert "error" not in result, result
    assert result["boxValid"] and result["prismValid"], result
    assert result["boxVolume"] == pytest.approx(480, abs=0.001), result
    assert result["prismVolume"] == pytest.approx(30, abs=0.001), result
    assert result["boxBounds"] == pytest.approx([2, 3, 4, 12, 9, 12], abs=0.001), result
    assert result["solids"] == [1, 1], result
