/**
 * CAD Editor - Main Application
 *
 * Integrates Monaco editor with CAD library and Three.js viewer
 * for live preview of CAD code.
 */

import { CADViewer } from './viewer.js';
import { initCAD, Workplane, Assembly } from './cad.js';

// Default example code - assembly with three colored objects
const DEFAULT_CODE = `// CAD Example: Assembly with three colored parts
// Edit this code to see live preview on the right!

// Red cube with hole and chamfered edges
const cube = new Workplane("XY")
    .box(20, 20, 20)
    .hole(8)
    .chamfer(2)
    .color("#e74c3c");

// Green cylinder offset to the right
const cylinder = new Workplane("XY")
    .cylinder(8, 25)
    .translate(30, 0, 0)
    .color("#2ecc71");

// Blue smaller cube offset to the left
const smallCube = new Workplane("XY")
    .box(12, 12, 15)
    .translate(-25, 0, 0)
    .color("#3498db");

// Create assembly with all parts
const result = new Assembly()
    .add(cube)
    .add(cylinder)
    .add(smallCube);

result;
`;

class CADEditor {
    constructor() {
        this.editor = null;
        this.viewer = null;
        this.oc = null;
        this.debounceTimer = null;
        this.debounceDelay = 800; // ms
        this.isReady = false;
        this._currentResult = null; // Store current Workplane or Assembly for export
        this._downloadSTLBtn = null;
        this._download3MFBtn = null;

        this._init();
    }

    async _init() {
        // Initialize Three.js viewer first (it doesn't need OC)
        const viewerContainer = document.getElementById('viewer-container');
        this.viewer = new CADViewer(viewerContainer);

        // Expose viewer for testing
        window.cadViewer = this.viewer;

        // Set up download buttons
        this._downloadSTLBtn = document.getElementById('download-stl-btn');
        this._downloadSTLBtn.addEventListener('click', () => this._downloadSTL());

        this._download3MFBtn = document.getElementById('download-3mf-btn');
        this._download3MFBtn.addEventListener('click', () => this._download3MF());

        // Load Monaco editor
        await this._loadMonaco();

        // Initialize OpenCascade
        await this._initOpenCascade();

        // Set up editor change listener
        this.editor.onDidChangeModelContent(() => {
            this._onCodeChange();
        });

        // Initial render
        this._render();
    }

    async _loadMonaco() {
        return new Promise((resolve) => {
            // Load Monaco from CDN
            const script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min/vs/loader.js';
            script.onload = () => {
                require.config({
                    paths: { vs: 'https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min/vs' }
                });

                require(['vs/editor/editor.main'], () => {
                    // Define custom theme
                    monaco.editor.defineTheme('cad-dark', {
                        base: 'vs-dark',
                        inherit: true,
                        rules: [
                            { token: 'comment', foreground: '6a9955' },
                            { token: 'keyword', foreground: 'c586c0' },
                            { token: 'string', foreground: 'ce9178' },
                            { token: 'number', foreground: 'b5cea8' },
                        ],
                        colors: {
                            'editor.background': '#0d1117',
                            'editor.foreground': '#c9d1d9',
                            'editor.lineHighlightBackground': '#161b22',
                            'editorCursor.foreground': '#00d4ff',
                            'editor.selectionBackground': '#264f78',
                        }
                    });

                    // Create editor
                    this.editor = monaco.editor.create(
                        document.getElementById('editor-container'),
                        {
                            value: DEFAULT_CODE,
                            language: 'javascript',
                            theme: 'cad-dark',
                            fontSize: 14,
                            fontFamily: "'JetBrains Mono', 'Fira Code', Monaco, monospace",
                            minimap: { enabled: false },
                            scrollBeyondLastLine: false,
                            lineNumbers: 'on',
                            renderLineHighlight: 'line',
                            automaticLayout: true,
                            tabSize: 4,
                            wordWrap: 'on',
                        }
                    );

                    resolve();
                });
            };
            document.head.appendChild(script);
        });
    }

    async _initOpenCascade() {
        this._setStatus('loading', 'Loading OpenCascade...');

        try {
            const cdnBase = 'https://cdn.jsdelivr.net/npm/opencascade.js@2.0.0-beta.b5ff984/dist';
            const initOC = await import(`${cdnBase}/opencascade.full.js`);

            this.oc = await initOC.default({
                locateFile: (file) => {
                    if (file.endsWith('.wasm')) {
                        return `${cdnBase}/${file}`;
                    }
                    return file;
                }
            });

            await this.oc.ready;

            // Initialize CAD library and expose to window for testing
            initCAD(this.oc);
            window.oc = this.oc;

            this.isReady = true;
            this._setStatus('ready', 'Ready');
            this._hideLoading();

        } catch (error) {
            this._setStatus('error', 'Failed to load');
            this._showError('Failed to initialize OpenCascade: ' + error.message);
            throw error;
        }
    }

    _onCodeChange() {
        // Clear previous timer
        if (this.debounceTimer) {
            clearTimeout(this.debounceTimer);
        }

        // Show loading state
        this._setStatus('loading', 'Compiling...');

        // Set new timer
        this.debounceTimer = setTimeout(() => {
            this._render();
        }, this.debounceDelay);
    }

    _render() {
        if (!this.isReady) return;

        const code = this.editor.getValue();
        this._hideError();
        this._currentResult = null;
        this._downloadSTLBtn.disabled = true;
        this._download3MFBtn.disabled = true;

        try {
            // Create a sandboxed execution context
            const result = this._executeCode(code);

            if (result && result.isAssembly) {
                // Assembly - convert all parts to mesh and display
                const meshData = result.toMesh(0.1, 0.3);
                if (meshData && meshData.length > 0) {
                    this.viewer.displayMesh(meshData);
                    this._setStatus('ready', 'Ready');
                    this._currentResult = result;
                    this._downloadSTLBtn.disabled = false;
                    this._download3MFBtn.disabled = false;
                } else {
                    throw new Error('Assembly has no valid parts');
                }
            } else if (result && result._shape) {
                // Single Workplane - convert to mesh and display
                const meshData = result.toMesh(0.1, 0.3);
                if (meshData) {
                    this.viewer.displayMesh(meshData);
                    this._setStatus('ready', 'Ready');
                    this._currentResult = result;
                    this._downloadSTLBtn.disabled = false;
                    this._download3MFBtn.disabled = false;
                } else {
                    throw new Error('Failed to generate mesh from shape');
                }
            } else if (result && typeof result === 'object' && result.vertices) {
                // Already mesh data - can't export to STL
                this.viewer.displayMesh(result);
                this._setStatus('ready', 'Ready');
            } else {
                throw new Error('Code must return a Workplane, Assembly, or mesh data');
            }

        } catch (error) {
            this._setStatus('error', 'Error');
            this._showError(error.message);
            this.viewer.showError();
            this._highlightError(error);
            this._currentResult = null;
            this._downloadSTLBtn.disabled = true;
            this._download3MFBtn.disabled = true;
        }
    }

    _executeCode(code) {
        // Create function with CAD globals available
        // We wrap the code to capture the 'result' variable if defined
        // The code should define a 'result' variable with the final shape
        const wrappedCode = `
            "use strict";
            ${code}
            return (typeof result !== 'undefined') ? result : undefined;
        `;

        // Execute in context with Workplane and Assembly available
        const fn = new Function('Workplane', 'Assembly', 'oc', wrappedCode);
        return fn(Workplane, Assembly, this.oc);
    }

    _setStatus(state, text) {
        const dot = document.getElementById('status-dot');
        const statusText = document.getElementById('status-text');

        dot.className = 'status-dot';
        if (state === 'loading') {
            dot.classList.add('loading');
        } else if (state === 'error') {
            dot.classList.add('error');
        }

        statusText.textContent = text;
    }

    _showError(message) {
        const overlay = document.getElementById('error-overlay');
        const messageEl = document.getElementById('error-message');

        messageEl.textContent = message;
        overlay.classList.add('visible');
    }

    _hideError() {
        const overlay = document.getElementById('error-overlay');
        overlay.classList.remove('visible');
    }

    _hideLoading() {
        const loading = document.getElementById('loading-overlay');
        loading.classList.add('hidden');
    }

    _highlightError(error) {
        // Try to extract line number from error
        const match = error.stack?.match(/<anonymous>:(\d+):(\d+)/);
        if (match && this.editor) {
            const line = parseInt(match[1]) - 2; // Adjust for wrapper
            const column = parseInt(match[2]);

            // Add error decoration
            monaco.editor.setModelMarkers(
                this.editor.getModel(),
                'cad-errors',
                [{
                    startLineNumber: line,
                    startColumn: 1,
                    endLineNumber: line,
                    endColumn: 1000,
                    message: error.message,
                    severity: monaco.MarkerSeverity.Error
                }]
            );
        }
    }

    _downloadSTL() {
        if (!this._currentResult) {
            console.warn('No shape to export');
            return;
        }

        try {
            this._setStatus('loading', 'Exporting STL...');

            // Generate STL blob
            const blob = this._currentResult.toSTL(0.1, 0.3);
            if (!blob) {
                throw new Error('Failed to generate STL');
            }

            // Create download link
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'model.stl';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            this._setStatus('ready', 'Ready');
        } catch (error) {
            console.error('STL export failed:', error);
            this._setStatus('error', 'Export failed');
            this._showError('STL export failed: ' + error.message);
        }
    }

    async _download3MF() {
        if (!this._currentResult) {
            console.warn('No shape to export');
            return;
        }

        try {
            this._setStatus('loading', 'Exporting 3MF...');

            // Generate 3MF blob (async because of JSZip)
            const blob = await this._currentResult.to3MF(0.1, 0.3);
            if (!blob) {
                throw new Error('Failed to generate 3MF');
            }

            // Create download link
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'model.3mf';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            this._setStatus('ready', 'Ready');
        } catch (error) {
            console.error('3MF export failed:', error);
            this._setStatus('error', 'Export failed');
            this._showError('3MF export failed: ' + error.message);
        }
    }
}

// Start the application
new CADEditor();
