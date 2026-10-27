const generators = new Map();
const listeners = new Set();

/** Register a generator that supplies a form, option reader, summary, and source builder. */
export function registerGenerator(definition) {
    if (!definition || typeof definition.id !== 'string' || !/^[a-z0-9][a-z0-9-]*$/.test(definition.id) ||
        typeof definition.fieldsId !== 'string' || !/^[a-z0-9][a-z0-9-]*$/.test(definition.fieldsId) ||
        typeof definition.label !== 'string' || !definition.label.trim() ||
        typeof definition.readOptions !== 'function' || typeof definition.summarize !== 'function' ||
        typeof definition.generate !== 'function') {
        throw new TypeError('Generator registration requires valid id, label, fieldsId, readOptions, summarize, and generate');
    }
    if (generators.has(definition.id)) throw new Error(`Generator already registered: ${definition.id}`);
    generators.set(definition.id, Object.freeze({ ...definition }));
    for (const listener of listeners) listener();
}

export function listGenerators() {
    return [...generators.values()].map(({ id, label }) => ({ id, label }));
}

export function getGenerator(id) {
    return generators.get(id) || null;
}

export function subscribeToGeneratorRegistry(listener) {
    if (typeof listener !== 'function') throw new TypeError('Generator registry listener must be a function');
    listeners.add(listener);
    return () => listeners.delete(listener);
}
