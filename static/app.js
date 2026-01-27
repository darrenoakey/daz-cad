/**
 * OpenCascade.js Initialization Module
 *
 * Handles loading and initializing OpenCascade.js WebAssembly module,
 * with comprehensive error handling and status reporting.
 */

// Global state for OpenCascade instance
let ocInstance = null;

/**
 * Log levels and their corresponding CSS classes
 */
const LogLevel = {
    INFO: 'info',
    SUCCESS: 'success',
    ERROR: 'error',
    WARN: 'warn'
};

/**
 * Append a log entry to the log container
 */
function log(message, level = LogLevel.INFO) {
    const logContainer = document.getElementById('log');
    const entry = document.createElement('div');
    entry.className = `log-entry ${level}`;
    const timestamp = new Date().toISOString().split('T')[1].slice(0, 12);
    entry.textContent = `[${timestamp}] ${message}`;
    logContainer.appendChild(entry);
    logContainer.scrollTop = logContainer.scrollHeight;
    console.log(`[${level.toUpperCase()}] ${message}`);
}

/**
 * Update the status display
 */
function updateStatus(state, message) {
    const statusEl = document.getElementById('status');
    statusEl.className = `status ${state}`;

    let icon = '';
    if (state === 'loading') {
        icon = '<div class="spinner"></div>';
    } else if (state === 'success') {
        icon = '<span class="checkmark"></span>';
    } else if (state === 'error') {
        icon = '<span class="error-icon"></span>';
    }

    statusEl.innerHTML = `${icon}<span>${message}</span>`;
}

/**
 * Show test result
 */
function showTestResult(passed, message) {
    const resultEl = document.getElementById('test-result');
    const messageEl = document.getElementById('test-message');
    resultEl.className = `visible ${passed ? 'pass' : 'fail'}`;
    messageEl.textContent = message;
}

/**
 * Initialize OpenCascade.js
 *
 * Uses the beta version which provides a default export function.
 *
 * @returns {Promise<object>} The initialized OpenCascade instance
 * @throws {Error} If initialization fails
 */
async function initOpenCascade() {
    log('Starting OpenCascade.js initialization...');

    try {
        // Import opencascade.js - the beta version exports a default init function
        log('Loading OpenCascade.js module...');

        // Use dynamic import with the full URL to the ES module version
        // The beta version provides opencascade.full.mjs as an ES module
        const cdnBase = 'https://cdn.jsdelivr.net/npm/opencascade.js@2.0.0-beta.b5ff984/dist';

        // Import the main module
        const initOC = await import(`${cdnBase}/opencascade.full.js`);

        log('Module loaded, initializing WASM...');

        // The module exports a default function that initializes the WASM
        // We need to provide the WASM file location
        const oc = await initOC.default({
            locateFile: (file) => {
                if (file.endsWith('.wasm')) {
                    return `${cdnBase}/${file}`;
                }
                return file;
            }
        });

        // Wait for the module to be ready
        await oc.ready;

        log('WASM module initialized successfully', LogLevel.SUCCESS);

        // Store globally for access
        ocInstance = oc;
        window.oc = oc;

        return oc;
    } catch (error) {
        log(`Initialization failed: ${error.message}`, LogLevel.ERROR);
        throw error;
    }
}

/**
 * Verify OpenCascade is working by performing a simple calculation
 * Creates a simple box and verifies its properties
 *
 * @param {object} oc - The OpenCascade instance
 * @returns {boolean} True if verification passed
 */
function verifyOpenCascade(oc) {
    log('Running verification tests...');

    try {
        // Test 1: Create a simple box
        log('Creating test box (10x20x30)...');
        const box = new oc.BRepPrimAPI_MakeBox_2(10, 20, 30);
        const shape = box.Shape();

        if (!shape || shape.IsNull()) {
            throw new Error('Failed to create box shape');
        }
        log('Box shape created successfully', LogLevel.SUCCESS);

        // Test 2: Calculate volume using GProp
        log('Calculating volume...');
        const props = new oc.GProp_GProps_1();
        oc.BRepGProp.VolumeProperties_1(shape, props, false, false, false);
        const volume = props.Mass();

        const expectedVolume = 10 * 20 * 30; // 6000
        const tolerance = 0.001;

        if (Math.abs(volume - expectedVolume) > tolerance) {
            throw new Error(`Volume mismatch: expected ${expectedVolume}, got ${volume}`);
        }
        log(`Volume calculation correct: ${volume} (expected: ${expectedVolume})`, LogLevel.SUCCESS);

        // Test 3: Get bounding box
        log('Calculating bounding box...');
        const bbox = new oc.Bnd_Box_1();
        oc.BRepBndLib.Add(shape, bbox, false);

        const xMin = { current: 0 };
        const yMin = { current: 0 };
        const zMin = { current: 0 };
        const xMax = { current: 0 };
        const yMax = { current: 0 };
        const zMax = { current: 0 };
        bbox.Get(xMin, yMin, zMin, xMax, yMax, zMax);

        log(`Bounding box: (${xMin.current},${yMin.current},${zMin.current}) to (${xMax.current},${yMax.current},${zMax.current})`, LogLevel.SUCCESS);

        // Clean up
        box.delete();
        props.delete();
        bbox.delete();

        log('All verification tests passed!', LogLevel.SUCCESS);
        return true;

    } catch (error) {
        log(`Verification failed: ${error.message}`, LogLevel.ERROR);
        return false;
    }
}

/**
 * Main initialization entry point
 */
async function main() {
    const startTime = performance.now();

    try {
        log('=== OpenCascade.js Initialization ===');

        // Initialize OpenCascade
        const oc = await initOpenCascade();

        // Run verification
        const verified = verifyOpenCascade(oc);

        const elapsed = ((performance.now() - startTime) / 1000).toFixed(2);

        if (verified) {
            updateStatus('success', `OpenCascade.js ready! (${elapsed}s)`);
            showTestResult(true, `Created box, calculated volume (6000 cubic units), verified in ${elapsed}s`);
            log(`=== Initialization complete in ${elapsed}s ===`, LogLevel.SUCCESS);

            // Dispatch custom event for test detection
            window.dispatchEvent(new CustomEvent('opencascade-ready', {
                detail: { oc, elapsed, verified: true }
            }));
        } else {
            throw new Error('Verification tests failed');
        }

    } catch (error) {
        updateStatus('error', `Initialization failed: ${error.message}`);
        showTestResult(false, error.message);
        log(`=== Initialization failed ===`, LogLevel.ERROR);

        // Dispatch failure event
        window.dispatchEvent(new CustomEvent('opencascade-error', {
            detail: { error: error.message }
        }));
    }
}

// Start initialization when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', main);
} else {
    main();
}
