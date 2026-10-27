/** Conservative, deterministic FDM finishing rules for editable Workplane solids. */
import { Workplane, getOC } from './cad.js';
import { valid } from './joinery-kernel.js';

const SELECTOR_PART = /^[|><][XYZ]$/i;

function optionsFor(options = {}) {
    const result = {
        verticalFillet: options.verticalFillet ?? 1,
        baseChamfer: options.baseChamfer ?? 0.4,
        preserveEdges: options.preserveEdges ?? [],
    };
    for (const name of ['verticalFillet', 'baseChamfer']) {
        if (!Number.isFinite(result[name]) || result[name] < 0) {
            throw new Error(`optimizeForPrinting: ${name} must be a non-negative finite millimetre value`);
        }
    }
    if (!Array.isArray(result.preserveEdges) || result.preserveEdges.some((selector) =>
        typeof selector !== 'string' || !selector.trim() || selector.trim().split(/\s+(?:and|or)\s+/i).some((part) => !SELECTOR_PART.test(part)))) {
        throw new Error('optimizeForPrinting: preserveEdges must contain CAD edge selectors such as "<X and <Y"');
    }
    if (result.verticalFillet === 0 && result.baseChamfer === 0) {
        throw new Error('optimizeForPrinting: enable a fillet or chamfer greater than zero');
    }
    return result;
}

function withoutPreservedEdges(shape, selected, selectors) {
    if (!selectors.length) return selected;
    const preserved = new Set();
    for (const selector of selectors) {
        for (const edge of shape.edges(selector)._selectedEdges) preserved.add(edge.HashCode(1000000));
    }
    selected._selectedEdges = selected._selectedEdges.filter((edge) => !preserved.has(edge.HashCode(1000000)));
    return preserved.size;
}

function requireValidResult(oc, source, candidate, operation) {
    if (candidate._shape === source._shape || !valid(oc, candidate._shape)) {
        throw new Error(`optimizeForPrinting: ${operation} failed; reduce its size or simplify the source geometry`);
    }
}

/** Apply only geometry whose intent is unambiguous, and retain a machine-readable audit. */
Workplane.prototype.optimizeForPrinting = function optimizeForPrinting(options = {}) {
    const settings = optionsFor(options);
    if (!this._shape || this.isAssembly) throw new Error('optimizeForPrinting requires one Workplane solid');
    const oc = getOC();
    if (!valid(oc, this._shape)) throw new Error('optimizeForPrinting requires one valid OpenCascade solid');

    let optimized = this;
    const changes = [];
    const warnings = [
        'Review overhangs, bridges, wall thickness, layer-direction loads, and fits in the slicer; these rules do not certify printability.',
    ];

    // A small base chamfer relieves first-layer flare/elephant-foot at bed-contact edges.
    if (settings.baseChamfer > 0) {
        const bottom = optimized.edges('<Z');
        if (bottom._selectedEdges.length) {
            const before = optimized;
            optimized = bottom.chamfer(settings.baseChamfer);
            requireValidResult(oc, before, optimized, 'base chamfer');
            changes.push({ rule: 'base-chamfer', edges: bottom._selectedEdges.length, millimetres: settings.baseChamfer });
        }
    }

    // Vertical rounds reduce sharp internal stress corners and nozzle-radius artefacts.
    // Explicit mating selectors are excluded so datum and butt-joint corners stay square.
    if (settings.verticalFillet > 0) {
        const vertical = optimized.edges('|Z');
        const candidateCount = vertical._selectedEdges.length;
        withoutPreservedEdges(optimized, vertical, settings.preserveEdges);
        if (vertical._selectedEdges.length) {
            const before = optimized;
            optimized = vertical.fillet(settings.verticalFillet);
            requireValidResult(oc, before, optimized, 'vertical fillet');
            changes.push({
                rule: 'vertical-fillet', edges: vertical._selectedEdges.length,
                preserved: candidateCount - vertical._selectedEdges.length, millimetres: settings.verticalFillet,
            });
        }
    }

    optimized.printReport = { settings, changes, warnings };
    return optimized;
};

export const Printability = { optionsFor };
