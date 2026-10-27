export function connectorCountForSeam(units) {
    return Math.max(1, Math.min(4, Math.floor(units / 2)));
}

/** Return seam-key positions in splitAndJoin's local plane frame. */
export function connectorPositionsForSeam(units, unitSize, axis, sourceBounds) {
    if (!Number.isInteger(units) || units < 1 || !Number.isFinite(unitSize) || unitSize <= 0) {
        throw new TypeError('Gridfinity seam positions require positive units and unit size');
    }
    if (axis !== 'x' && axis !== 'y') throw new TypeError('Gridfinity seam axis must be x or y');
    let offset = 0;
    if (axis === 'y') {
        if (!sourceBounds || !Number.isFinite(sourceBounds.minX) || !Number.isFinite(sourceBounds.maxX)) {
            throw new TypeError('A y-axis seam requires the segment X bounds');
        }
        // splitAndJoin's local u axis points toward -X for a Y-normal plane.
        offset = -(sourceBounds.minX + sourceBounds.maxX) / 2;
    }
    const span = units * unitSize;
    const count = connectorCountForSeam(units);
    return Array.from({ length: count }, (_, index) => [offset + ((index + 1) / (count + 1) - 0.5) * span, 0]);
}
