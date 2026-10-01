/**
 * CAD Worker - Background thread for OpenCascade operations
 *
 * Handles ALL CAD operations: rendering, exports, etc.
 * The main thread only handles UI and Three.js rendering.
 */

import { initCAD, Workplane, Assembly, Profiler, loadFont, getDefaultFont } from './cad.js';
import { loadOpenCascade } from './opencascade.js';
import { Gridfinity } from './gridfinity.js';
import './patterns.js';  // Extends Workplane with unified cutPattern()
import './naming.js';    // Extends Workplane with named references
import { Joinery } from './joinery.js'; // Extends Workplane with splitAndJoin()

let oc = null;
let isInitialized = false;
let isRendering = false;

// Intercept console to forward to main thread
const originalConsole = {
    log: console.log.bind(console),
    error: console.error.bind(console),
    warn: console.warn.bind(console),
    info: console.info.bind(console)
};

function forwardConsole(level, args) {
    // Convert args to strings
    const message = args.map(arg => {
        if (typeof arg === 'object') {
            try {
                return JSON.stringify(arg, null, 2);
            } catch {
                return String(arg);
            }
        }
        return String(arg);
    }).join(' ');

    self.postMessage({ type: 'console', level, message });
}

console.log = (...args) => {
    originalConsole.log(...args);
    forwardConsole('log', args);
};

console.error = (...args) => {
    originalConsole.error(...args);
    forwardConsole('error', args);
};

console.warn = (...args) => {
    originalConsole.warn(...args);
    forwardConsole('warn', args);
};

console.info = (...args) => {
    originalConsole.info(...args);
    forwardConsole('info', args);
};

// Post message helpers
function postStatus(status, message) {
    self.postMessage({ type: 'status', status, message });
}

function postError(error) {
    self.postMessage({ type: 'error', error });
}

function postResult(meshData) {
    self.postMessage({ type: 'result', meshData });
}

// Initialize OpenCascade
async function initOpenCascade() {
    if (isInitialized) return;

    postStatus('loading', 'Loading OpenCascade...');

    try {
        oc = await loadOpenCascade();

        // Initialize CAD library with this OpenCascade instance
        initCAD(oc);

        // Pre-load default font for text rendering
        postStatus('loading', 'Loading default font...');
        try {
            // Use Overpass Bold as default (more reliable than external CDN)
            await loadFont('/static/fonts/Overpass-Bold.ttf', '/fonts/Overpass-Bold.ttf');
            console.log('[CAD] Default font loaded');
        } catch (fontError) {
            console.warn('[CAD] Could not load default font:', fontError.message);
            // Continue without font - text() will error if used
        }

        isInitialized = true;
        postStatus('ready', 'Ready');

    } catch (error) {
        postError('Failed to initialize OpenCascade: ' + error.message);
        throw error;
    }
}

// Execute CAD code and return mesh data
function executeCode(code) {
    if (!isInitialized) {
        throw new Error('OpenCascade not initialized');
    }

    // Execute the code with the CAD API and this worker's initialized OpenCascade instance available
    const fn = new Function('Workplane', 'Assembly', 'Profiler', 'loadFont', 'getDefaultFont', 'Gridfinity', 'Joinery', 'oc', code + '\nreturn result;');
    const result = fn(Workplane, Assembly, Profiler, loadFont, getDefaultFont, Gridfinity, Joinery, oc);

    if (!result) {
        throw new Error('Code did not produce a result');
    }

    // Convert to mesh data
    if (result.isAssembly) {
        const meshes = result.toMesh(0.1, 0.5);
        // Collect face labels from each part
        const assemblyFaceLabels = [];
        if (result._parts) {
            for (const part of result._parts) {
                if (part && typeof part.getFaceLabels === 'function') {
                    assemblyFaceLabels.push(part.getFaceLabels());
                }
            }
        }
        return { isAssembly: true, meshes, faceLabels: assemblyFaceLabels.length > 0 ? assemblyFaceLabels[0] : null };
    } else {
        const mesh = result.toMesh(0.1, 0.5);
        const faceLabels = typeof result.getFaceLabels === 'function' ? result.getFaceLabels() : null;
        return { isAssembly: false, mesh, faceLabels };
    }
}

// Execute code and return the raw CAD result (for exports)
function executeForExport(code) {
    if (!isInitialized) {
        throw new Error('OpenCascade not initialized');
    }

    const fn = new Function('Workplane', 'Assembly', 'Profiler', 'loadFont', 'getDefaultFont', 'Gridfinity', 'Joinery', 'oc', code + '\nreturn result;');
    return fn(Workplane, Assembly, Profiler, loadFont, getDefaultFont, Gridfinity, Joinery, oc);
}

// Handle messages from main thread
self.onmessage = async function(e) {
    const { type, code, id, generated } = e.data;

    if (type === 'init') {
        try {
            await initOpenCascade();
            self.postMessage({ type: 'initialized', id });
        } catch (error) {
            postError(error.message);
        }
    } else if (type === 'render') {
        if (isRendering) {
            self.postMessage({ type: 'busy', id });
            return;
        }

        if (!isInitialized) {
            postError('OpenCascade not initialized');
            return;
        }

        isRendering = true;
        postStatus('compiling', 'Compiling...');
        console.log('[Worker] Started rendering');
        const renderStart = performance.now();

        try {
            const meshData = executeCode(code);
            const elapsed = ((performance.now() - renderStart) / 1000).toFixed(2);
            console.log(`[Worker] Finished rendering (${elapsed}s)`);
            postResult(meshData);
            self.postMessage({ type: 'renderComplete', id, meshData });
        } catch (error) {
            console.log('[Worker] Rendering failed:', error.message);
            postError(error.message);
            self.postMessage({ type: 'renderError', id, error: error.message });
        } finally {
            isRendering = false;
            // renderComplete/renderError are authoritative. A trailing Ready
            // used to hide render errors or mark stale results as exportable.
        }
    } else if (type === 'validateJoinery') {
        // Preflight before the UI edits Monaco: a failed source is never replaced.
        try {
            const result = executeForExport(code);
            if (!result) throw new Error('Source did not produce a result variable.');
            if (generated) {
                if (!result.isAssembly) throw new Error('Generated Cut/Join result was not an Assembly.');
            } else {
                if (result.isAssembly) throw new Error('Cut/Join currently accepts one Workplane result; choose or create a single part before splitting.');
                if (typeof result.splitAndJoin !== 'function') throw new Error('This result is not a Workplane that can be split.');
            }
            self.postMessage({ type: 'joineryValidation', id, ok: true, warnings: [] });
        } catch (error) {
            self.postMessage({ type: 'joineryValidation', id, ok: false, error: `Cut/Join was not applied: ${error.message}` });
        }
    } else if (type === 'exportSTL') {
        if (!isInitialized) {
            postError('OpenCascade not initialized');
            return;
        }

        try {
            const result = executeForExport(code);
            if (!result || !result.toSTL) {
                throw new Error('No exportable result');
            }
            const blob = result.toSTL();
            // Convert blob to array buffer for transfer
            const buffer = await blob.arrayBuffer();
            self.postMessage({ type: 'exportSTLComplete', id, buffer }, [buffer]);
        } catch (error) {
            self.postMessage({ type: 'exportSTLError', id, error: error.message });
        }
    } else if (type === 'export3MF') {
        if (!isInitialized) {
            postError('OpenCascade not initialized');
            return;
        }

        try {
            const result = executeForExport(code);
            if (!result || !result.to3MF) {
                throw new Error('No exportable result (3MF requires Assembly)');
            }
            const blob = await result.to3MF();
            if (!blob) {
                throw new Error('Failed to generate 3MF');
            }
            const buffer = await blob.arrayBuffer();
            self.postMessage({ type: 'export3MFComplete', id, buffer }, [buffer]);
        } catch (error) {
            self.postMessage({ type: 'export3MFError', id, error: error.message });
        }
    }
};

// Signal that worker is loaded
self.postMessage({ type: 'loaded' });
