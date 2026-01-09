/**
 * CAD Worker - Background thread for OpenCascade operations
 *
 * Handles ALL CAD operations: rendering, exports, etc.
 * The main thread only handles UI and Three.js rendering.
 */

import { initCAD, Workplane, Assembly, Profiler } from './cad.js';

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
        const cdnBase = 'https://cdn.jsdelivr.net/npm/opencascade.js@2.0.0-beta.b5ff984/dist';

        // Dynamic import for OpenCascade
        const initOC = await import(`${cdnBase}/opencascade.full.js`);

        oc = await initOC.default({
            locateFile: (file) => {
                if (file.endsWith('.wasm')) {
                    return `${cdnBase}/${file}`;
                }
                return file;
            }
        });

        await oc.ready;

        // Initialize CAD library with this OpenCascade instance
        initCAD(oc);

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

    // Execute the code with Workplane, Assembly, and Profiler available
    const fn = new Function('Workplane', 'Assembly', 'Profiler', code + '\nreturn result;');
    const result = fn(Workplane, Assembly, Profiler);

    if (!result) {
        throw new Error('Code did not produce a result');
    }

    // Convert to mesh data
    if (result.isAssembly) {
        const meshes = result.toMesh(0.1, 0.5);
        return { isAssembly: true, meshes };
    } else {
        const mesh = result.toMesh(0.1, 0.5);
        return { isAssembly: false, mesh };
    }
}

// Execute code and return the raw CAD result (for exports)
function executeForExport(code) {
    if (!isInitialized) {
        throw new Error('OpenCascade not initialized');
    }

    const fn = new Function('Workplane', 'Assembly', 'Profiler', code + '\nreturn result;');
    return fn(Workplane, Assembly, Profiler);
}

// Handle messages from main thread
self.onmessage = async function(e) {
    const { type, code, id } = e.data;

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

        try {
            const meshData = executeCode(code);
            postResult(meshData);
            self.postMessage({ type: 'renderComplete', id, meshData });
        } catch (error) {
            postError(error.message);
            self.postMessage({ type: 'renderError', id, error: error.message });
        } finally {
            isRendering = false;
            postStatus('ready', 'Ready');
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
