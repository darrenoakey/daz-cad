/**
 * CAD Editor - Main Application
 *
 * Integrates Monaco editor with CAD library and Three.js viewer
 * for live preview of CAD code.
 */

import { CADViewer } from './viewer.js';
import { initCAD, Workplane, Assembly, Profiler } from './cad.js';
import { Gridfinity } from './gridfinity.js';
import './patterns.js';  // Extends Workplane with unified cutPattern()
import * as acorn from 'https://cdn.jsdelivr.net/npm/acorn@8.14.1/+esm';
import * as astring from 'https://cdn.jsdelivr.net/npm/astring@1.9.0/+esm';

// Fallback code in case server load fails
const FALLBACK_CODE = `// CAD Example - Create a simple box
const result = new Workplane("XY").box(20, 20, 20);
result;
`;

class CADEditor {
    constructor() {
        this.editor = null;
        this.viewer = null;
        this.oc = null; // Main thread OpenCascade (for testing/direct API)
        this.debounceTimer = null;
        this.debounceDelay = 2000; // ms - longer delay for complex operations
        this.isReady = false;
        this._currentFile = null; // Current file being edited
        this._downloadSTLBtn = null;
        this._download3MFBtn = null;

        // Web Worker for background rendering
        this._worker = null;
        this._workerReady = false;
        this._isRendering = false; // True when worker is rendering
        this._isDirty = false; // True if code changed during render
        this._pendingCode = null; // Code to render after current render completes
        this._renderRequestId = 0; // Incremented for each render request

        // Spare worker for instant swap when cancelling renders
        this._spareWorker = null;
        this._spareWorkerReady = false;

        // Chat state
        this._isProcessing = false; // True when waiting for agent response
        this._skipSave = false; // True when file update came from agent
        this._chatInput = null;
        this._chatSendBtn = null;
        this._chatMessages = null;

        // Console output state
        this._consoleOutput = null;
        this._consoleClearBtn = null;

        // Properties panel state
        this._propertiesList = null;
        this._properties = []; // Array of {name, value, start, end} for numeric variables
        this._sliderTriggeredChange = false; // True when slider caused code change

        // File manager state
        this._fileSelectorBtn = null;
        this._fileDropdown = null;
        this._fileList = null;
        this._newFileInput = null;
        this._createFileBtn = null;
        this._resetFileBtn = null;
        this._availableFiles = [];
        this._hasTemplate = false;

        // Hot reload state
        this._fileMtime = null; // Last known modification time
        this._lastSaveTime = 0; // Timestamp of last save (to avoid reload loop)
        this._fileWatchInterval = null;

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

        // Set up opacity slider
        this._initOpacitySlider();

        // Initialize file manager
        this._initFileManager();

        // Initialize console output
        this._initConsole();

        // Initialize chat UI
        this._initChat();

        // Initialize properties panel
        this._initProperties();

        // Load Monaco editor
        await this._loadMonaco();

        // Initialize CAD Worker (background thread for OpenCascade)
        // The worker handles rendering; main thread OC is for tests/direct API use
        await this._initWorker();

        // Initialize main-thread OpenCascade for testing and direct API calls
        await this._initOpenCascade();

        // Load default file from server
        await this._loadDefaultFile();

        // Set up editor change listener
        this.editor.onDidChangeModelContent(() => {
            this._onCodeChange();
            // Re-parse properties when code changes (unless slider caused the change)
            if (!this._sliderTriggeredChange) {
                this._parseAndRenderProperties();
            }
            this._sliderTriggeredChange = false;
        });

        // Enable chat now that everything is ready
        this._enableChat();

        // Start file watcher for hot reload
        this._startFileWatcher();

        // Initial property parsing
        this._parseAndRenderProperties();

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
                    // Add CAD library type definitions for autocomplete
                    const cadLibDefs = `
                        /** Gridfinity bin/insert generator */
                        declare const Gridfinity: {
                            /** Grid unit size (42mm) */
                            readonly UNIT_SIZE: number;
                            /** Height unit (7mm) */
                            readonly UNIT_HEIGHT: number;
                            /** Base profile height (4.75mm) */
                            readonly BASE_HEIGHT: number;
                            /** Baseplate rim height (4.65mm) */
                            readonly BP_HEIGHT: number;
                            /** Baseplate floor thickness (1.0mm) */
                            readonly BP_FLOOR: number;

                            /**
                             * Create a solid gridfinity bin with standardized base profile
                             * @param options.x - X dimension in grid units (1 unit = 42mm)
                             * @param options.y - Y dimension in grid units
                             * @param options.z - Z dimension in height units (1 unit = 7mm)
                             * @param options.stackable - Include stacking lip at top (default: false)
                             * @param options.solid - Create solid or hollow shell (default: true)
                             */
                            bin(options: { x: number; y: number; z: number; stackable?: boolean; solid?: boolean }): Workplane;

                            /**
                             * Create a solid gridfinity insert plug (fits inside a bin)
                             * @param options.x - X dimension in grid units
                             * @param options.y - Y dimension in grid units
                             * @param options.z - Z dimension in height units
                             * @param options.tolerance - Wall clearance in mm (default: 0.30)
                             * @param options.stackable - Account for stacking lip (default: true)
                             */
                            plug(options: { x: number; y: number; z: number; tolerance?: number; stackable?: boolean }): Workplane;

                            /**
                             * Create a bin with multiple custom-sized cutouts, auto-sized to fit
                             * @param options.cuts - Array of [width, height] or {width, height, fillet?}
                             * @param options.z - Height in gridfinity units (1 unit = 7mm)
                             * @param options.spacing - Minimum spacing between cuts (default: 1.5mm)
                             * @param options.fillet - Default corner fillet radius (default: 3mm)
                             * @example Gridfinity.fitBin({ cuts: [[80, 40], [30, 20], [35, 20]], z: 3 })
                             */
                            fitBin(options: {
                                cuts: Array<[number, number] | { width: number; height: number; fillet?: number }>;
                                z: number;
                                spacing?: number;
                                fillet?: number;
                            }): Workplane;

                            /**
                             * Create a minimal gridfinity baseplate (open grid, no floor)
                             * @param options.x - X dimension in grid units (1 unit = 42mm)
                             * @param options.y - Y dimension in grid units
                             * @param options.fillet - Round outer corners (default: true)
                             * @param options.chamfer - Chamfer bottom edge for bed adhesion (default: true)
                             * @example Gridfinity.baseplate({ x: 3, y: 2 })
                             */
                            baseplate(options: { x: number; y: number; fillet?: boolean; chamfer?: boolean }): Workplane;
                        };

                        /** CAD Workplane for creating 3D shapes */
                        declare class Workplane {
                            constructor(plane?: "XY" | "XZ" | "YZ");

                            /** Create a box centered on XY, bottom at Z=0 */
                            box(length: number, width: number, height: number, centered?: boolean): Workplane;

                            /** Create a cylinder */
                            cylinder(radius: number, height: number): Workplane;
                            cylinder(options: { diameter?: number; radius?: number; height: number }): Workplane;

                            /** Create a sphere */
                            sphere(radius: number): Workplane;

                            /** Create a polygon prism (3=triangle, 4=square, 6=hexagon) */
                            polygonPrism(sides: number, flatToFlat: number, height: number): Workplane;

                            /** Create 3D text */
                            text(textString: string, fontSize: number, depth: number, fontName?: string): Workplane;

                            /** Union with another shape */
                            union(other: Workplane): Workplane;

                            /** Cut/subtract another shape */
                            cut(other: Workplane): Workplane;

                            /** Intersect with another shape */
                            intersect(other: Workplane): Workplane;

                            /** Create a hole (through or blind) */
                            hole(diameter: number, depth?: number): Workplane;

                            /** Chamfer edges */
                            chamfer(distance: number): Workplane;

                            /** Fillet/round edges */
                            fillet(radius: number): Workplane;

                            /** Select faces by direction */
                            faces(selector: ">Z" | "<Z" | ">X" | "<X" | ">Y" | "<Y" | "|Z" | "|X" | "|Y"): Workplane;

                            /** Exclude faces */
                            facesNot(selector: string): Workplane;

                            /** Select edges */
                            edges(selector?: "|Z" | "|X" | "|Y" | ">Z" | "<Z"): Workplane;

                            /** Exclude edges */
                            edgesNot(selector: string): Workplane;

                            /** Filter out bottom edges */
                            filterOutBottom(): Workplane;

                            /** Filter out top edges */
                            filterOutTop(): Workplane;

                            /** Move the shape */
                            translate(x: number, y: number, z: number): Workplane;

                            /** Rotate around axis through origin */
                            rotate(axisX: number, axisY: number, axisZ: number, degrees: number): Workplane;

                            /** Set color (hex string like "#ff0000") */
                            color(hexColor: string): Workplane;

                            /**
                             * Cut a unified pattern into a selected face
                             * Supports: line, rect, square, circle, hexagon, octagon, triangle, or any n-sided polygon
                             */
                            cutPattern(options: {
                                /** Shape type: 'line', 'rect', 'square', 'circle', 'hexagon', 'octagon', 'triangle', or number (sides) */
                                shape?: 'line' | 'rect' | 'square' | 'circle' | 'hexagon' | 'octagon' | 'triangle' | number;
                                /** Primary dimension (line width, rect width, circle diameter, polygon flat-to-flat) */
                                width?: number;
                                /** Secondary dimension (rect height). Defaults to width */
                                height?: number;
                                /** For lines: line length (null = auto fill face) */
                                length?: number;
                                /** Corner radius for rectangles/squares */
                                fillet?: number;
                                /** Round the ends of lines (stadium shape) */
                                roundEnds?: boolean;
                                /** Shear angle in degrees (parallelograms) */
                                shear?: number;
                                /** Rotate each individual shape by this angle */
                                rotation?: number;
                                /** Cut depth in mm. null = through-cut */
                                depth?: number;
                                /** Space between shape centers */
                                spacing?: number;
                                /** Override X spacing */
                                spacingX?: number;
                                /** Override Y spacing */
                                spacingY?: number;
                                /** Alternative: specify wall between shapes */
                                wallThickness?: number;
                                /** Margin from face edges */
                                border?: number;
                                /** Override X border */
                                borderX?: number;
                                /** Override Y border */
                                borderY?: number;
                                /** Split pattern into N column groups */
                                columns?: number;
                                /** Gap between column groups */
                                columnGap?: number;
                                /** Split into N row groups */
                                rows?: number;
                                /** Gap between row groups */
                                rowGap?: number;
                                /** Offset alternate rows (brick/hex pattern) */
                                stagger?: boolean;
                                /** Fraction of spacingX to offset */
                                staggerAmount?: number;
                                /** Rotate entire pattern (degrees) */
                                angle?: number;
                                /** For lines: 'x' (horizontal) or 'y' (vertical) */
                                direction?: 'x' | 'y';
                            }): Workplane;

                            /** Cut optimized rectangular grid */
                            cutRectGrid(options: { width: number; height: number; count?: number; fillet?: number; depth?: number; minBorder?: number; minSpacing?: number }): Workplane;

                            /** Cut optimized circular grid */
                            cutCircleGrid(options: { radius?: number; diameter?: number; count?: number; depth?: number; minBorder?: number; minSpacing?: number }): Workplane;

                            /** Add gridfinity baseplate onto top face, auto-sized to fit */
                            addBaseplate(options?: { fillet?: boolean }): Workplane;

                            /** Cut away everything below the origin plane on specified axis */
                            cutBelow(axis: "X" | "Y" | "Z"): Workplane;

                            /** Cut away everything above the origin plane on specified axis */
                            cutAbove(axis: "X" | "Y" | "Z"): Workplane;

                            /** Export to STL */
                            toSTL(linearDeflection?: number, angularDeflection?: number): Blob;

                            /** Export to 3MF (Bambu Lab compatible) */
                            to3MF(linearDeflection?: number, angularDeflection?: number): Promise<Blob>;

                            /** Convert shape to mesh data for rendering */
                            toMesh(linearDeflection?: number, angularDeflection?: number): { vertices: Float32Array; indices: Uint32Array; normals: Float32Array; color?: string };

                            /** Create a modifier for pattern operations */
                            asModifier(): Workplane;

                            /** Apply modifier and perform pattern operation */
                            withModifier(modifier: Workplane): Workplane;

                            /** Apply a repeating pattern */
                            pattern(options: { axis: [number, number, number]; count: number; spacing: number }): Workplane;

                            /** Filter edges by custom criteria */
                            filterEdges(selector: (edge: any) => boolean): Workplane;

                            /** Get the underlying shape value */
                            val(): any;

                            /** Get or set generic metadata (used by exporters) */
                            meta(key: string, value?: any): Workplane | any;

                            /** Set infill density for 3MF export (e.g., 5 for 5%) */
                            infillDensity(percent: number): Workplane;

                            /** Set infill pattern for 3MF export */
                            infillPattern(pattern: 'grid' | 'gyroid' | 'honeycomb' | 'triangles' | 'cubic' | 'line' | 'concentric'): Workplane;

                            /** Set part name for 3MF export */
                            partName(name: string): Workplane;
                        }

                        /** Assembly of multiple parts */
                        declare class Assembly {
                            constructor();
                            /** Add a part to the assembly */
                            add(part: Workplane): Assembly;
                            /** Check if this is an assembly */
                            readonly isAssembly: boolean;
                            /** Convert assembly to mesh data */
                            toMesh(linearDeflection?: number, angularDeflection?: number): Array<{ vertices: Float32Array; indices: Uint32Array; normals: Float32Array; color?: string }>;
                            /** Export assembly to STL */
                            toSTL(linearDeflection?: number, angularDeflection?: number): Blob;
                            /** Export assembly to 3MF (Bambu Lab compatible) */
                            to3MF(linearDeflection?: number, angularDeflection?: number): Promise<Blob>;
                        }

                        /** Performance profiler */
                        declare class Profiler {
                            constructor(name?: string);
                            /** Record a checkpoint with a label */
                            checkpoint(label: string): Profiler;
                            /** Finish profiling and log results */
                            finished(): Profiler;
                            /** Get elapsed time since profiler started */
                            elapsed(): number;
                        }

                        /** Load a font for 3D text */
                        declare function loadFont(url: string, name: string): Promise<void>;

                        /** Get the default font name */
                        declare function getDefaultFont(): string | null;
                    `;

                    monaco.languages.typescript.javascriptDefaults.addExtraLib(cadLibDefs, 'cad-library.d.ts');

                    // Configure JS to be more lenient and suggest our completions first
                    monaco.languages.typescript.javascriptDefaults.setCompilerOptions({
                        target: monaco.languages.typescript.ScriptTarget.ES2020,
                        allowNonTsExtensions: true,
                        checkJs: false,
                        noSemanticValidation: true,
                    });

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
                            value: '// Loading...',
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

    // Create a worker instance and return promise when initialized
    _createWorkerInstance(isMainWorker = true) {
        return new Promise((resolve, reject) => {
            const worker = new Worker('/static/cad-worker.js', { type: 'module' });

            worker.onmessage = (e) => {
                const { type, status, message, error, meshData, id } = e.data;

                switch (type) {
                    case 'loaded':
                        worker.postMessage({ type: 'init', id: 0 });
                        break;

                    case 'initialized':
                        resolve(worker);
                        break;

                    case 'status':
                        if (isMainWorker) {
                            this._setStatus(status === 'ready' ? 'ready' : 'loading', message);
                        }
                        break;

                    case 'error':
                        console.error('[Worker Error]', error);
                        if (isMainWorker) {
                            this._setStatus('error', 'Error');
                            this._showError(error);
                            this.viewer.showError();
                            this._isRendering = false;
                            this._checkPendingRender();
                        }
                        break;

                    case 'renderComplete':
                        if (isMainWorker) {
                            this._handleRenderComplete(meshData, id);
                        }
                        break;

                    case 'renderError':
                        if (isMainWorker) {
                            this._setStatus('error', 'Error');
                            this._showError(error);
                            this.viewer.showError();
                            this._isRendering = false;
                            this._checkPendingRender();
                        }
                        break;

                    case 'busy':
                        if (isMainWorker) {
                            this._isDirty = true;
                        }
                        break;

                    case 'exportSTLComplete':
                        if (isMainWorker) {
                            this._handleExportSTLComplete(e.data.buffer);
                        }
                        break;

                    case 'exportSTLError':
                        if (isMainWorker) {
                            this._handleExportError('STL', error);
                        }
                        break;

                    case 'export3MFComplete':
                        if (isMainWorker) {
                            this._handleExport3MFComplete(e.data.buffer);
                        }
                        break;

                    case 'export3MFError':
                        if (isMainWorker) {
                            this._handleExportError('3MF', error);
                        }
                        break;
                }
            };

            worker.onerror = (e) => {
                console.error('[Worker Fatal Error]', e);
                reject(new Error('Worker failed to load: ' + e.message));
            };
        });
    }

    // Attach the main worker message handlers to a worker
    _attachWorkerHandlers(worker) {
        worker.onmessage = (e) => {
            const { type, status, message, error, meshData, id } = e.data;

            switch (type) {
                case 'loaded':
                    worker.postMessage({ type: 'init', id: 0 });
                    break;

                case 'initialized':
                    this._workerReady = true;
                    break;

                case 'status':
                    this._setStatus(status === 'ready' ? 'ready' : 'loading', message);
                    break;

                case 'error':
                    console.error('[Worker Error]', error);
                    this._setStatus('error', 'Error');
                    this._showError(error);
                    this.viewer.showError();
                    this._isRendering = false;
                    this._checkPendingRender();
                    break;

                case 'renderComplete':
                    this._handleRenderComplete(meshData, id);
                    break;

                case 'renderError':
                    this._setStatus('error', 'Error');
                    this._showError(error);
                    this.viewer.showError();
                    this._isRendering = false;
                    this._checkPendingRender();
                    break;

                case 'busy':
                    this._isDirty = true;
                    break;

                case 'exportSTLComplete':
                    this._handleExportSTLComplete(e.data.buffer);
                    break;

                case 'exportSTLError':
                    this._handleExportError('STL', error);
                    break;

                case 'export3MFComplete':
                    this._handleExport3MFComplete(e.data.buffer);
                    break;

                case 'export3MFError':
                    this._handleExportError('3MF', error);
                    break;

                case 'console':
                    this._appendConsole(e.data.level, e.data.message);
                    break;
            }
        };
    }

    async _initWorker() {
        this._setStatus('loading', 'Starting CAD engine...');

        // Initialize both main and spare workers in parallel
        const [mainWorker, spareWorker] = await Promise.all([
            this._createWorkerInstance(true),
            this._createWorkerInstance(false)
        ]);

        this._worker = mainWorker;
        this._workerReady = true;
        this._attachWorkerHandlers(this._worker);

        this._spareWorker = spareWorker;
        this._spareWorkerReady = true;
        console.log('[CAD] Both main and spare workers initialized');
    }

    _handleRenderComplete(meshData, requestId) {
        // Ignore stale render results
        if (requestId !== this._renderRequestId) {
            console.log('Ignoring stale render result');
            return;
        }

        this._isRendering = false;
        this._hideError();

        try {
            if (meshData.isAssembly) {
                // Assembly - display all meshes
                if (meshData.meshes && meshData.meshes.length > 0) {
                    this.viewer.displayMesh(meshData.meshes);
                    this._setStatus('ready', 'Ready');
                    this._downloadSTLBtn.disabled = false;
                    this._download3MFBtn.disabled = false;
                    this._saveFile();
                } else {
                    throw new Error('Assembly has no valid parts');
                }
            } else {
                // Single shape
                if (meshData.mesh) {
                    this.viewer.displayMesh(meshData.mesh);
                    this._setStatus('ready', 'Ready');
                    this._downloadSTLBtn.disabled = false;
                    this._download3MFBtn.disabled = false;
                    this._saveFile();
                } else {
                    throw new Error('Failed to generate mesh');
                }
            }
        } catch (error) {
            this._setStatus('error', 'Error');
            this._showError(error.message);
            this.viewer.showError();
        }

        // Check if there's a pending render
        this._checkPendingRender();
    }

    _checkPendingRender() {
        if (this._isDirty && this._pendingCode !== null) {
            this._isDirty = false;
            const code = this._pendingCode;
            this._pendingCode = null;
            this._startRender(code);
        }
    }

    async _initOpenCascade() {
        // Main thread OpenCascade for testing and direct API calls
        // Worker handles the actual rendering for better performance
        this._setStatus('loading', 'Loading CAD engine...');

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
            window.Gridfinity = Gridfinity;

            this.isReady = true;
            this._setStatus('ready', 'Ready');
            this._hideLoading();

        } catch (error) {
            console.warn('Failed to initialize main-thread OpenCascade (worker will still handle rendering):', error);
            // Still set ready if worker is available
            if (this._workerReady) {
                this.isReady = true;
                this._setStatus('ready', 'Ready');
                this._hideLoading();
            }
        }
    }

    async _loadDefaultFile() {
        try {
            // Priority 1: Check URL path for model name (e.g., /anker_holder → anker_holder.js)
            const pathModel = this._getModelFromPath();

            // Priority 2: Check localStorage for last edited file
            const lastFile = localStorage.getItem('cad-editor-last-file');

            // Determine which file to load (URL path takes precedence)
            const targetFile = pathModel || lastFile;

            // If we have a target file, try to load it
            if (targetFile) {
                try {
                    const fileResponse = await fetch(`/api/models/${targetFile}`);
                    if (fileResponse.ok) {
                        const fileData = await fileResponse.json();
                        this._currentFile = fileData.filename;
                        this._fileMtime = fileData.mtime;
                        this.editor.setValue(fileData.content);
                        this._updateFilenameDisplay();
                        // Update localStorage and URL
                        localStorage.setItem('cad-editor-last-file', this._currentFile);
                        this._updateUrlWithModel();
                        return; // Successfully loaded target file
                    }
                } catch (e) {
                    console.warn(`Could not load file ${targetFile}, falling back to default`);
                }
            }

            // Fall back to default file
            const response = await fetch('/api/models');
            if (!response.ok) throw new Error('Failed to list models');

            const data = await response.json();
            const filename = data.default || 'default.js';

            const fileResponse = await fetch(`/api/models/${filename}`);
            if (!fileResponse.ok) throw new Error(`Failed to load ${filename}`);

            const fileData = await fileResponse.json();
            this._currentFile = fileData.filename;
            this._fileMtime = fileData.mtime;
            this.editor.setValue(fileData.content);
            this._updateFilenameDisplay();
            localStorage.setItem('cad-editor-last-file', this._currentFile);
            this._updateUrlWithModel();

        } catch (error) {
            console.warn('Failed to load default file from server:', error);
            this.editor.setValue(FALLBACK_CODE);
            this._currentFile = 'default.js';
            this._fileMtime = null;
            this._updateFilenameDisplay();
        }
    }

    _getModelFromPath() {
        // Extract model name from URL path (e.g., /anker_holder → anker_holder.js)
        const path = window.location.pathname;
        if (path && path !== '/') {
            // Remove leading slash and add .js if needed
            let modelName = path.substring(1);
            if (!modelName.endsWith('.js')) {
                modelName += '.js';
            }
            return modelName;
        }
        return null;
    }

    _updateUrlWithModel() {
        if (!this._currentFile) return;

        // Use path-based URL (e.g., /anker_holder instead of /?model=anker_holder.js)
        const modelPath = '/' + this._currentFile.replace('.js', '');

        // Use replaceState to update URL without adding to history
        window.history.replaceState({}, '', modelPath);
    }

    _updateFilenameDisplay() {
        const el = document.getElementById('filename-display');
        if (el && this._currentFile) {
            el.textContent = this._currentFile;
        }
        // Check if this file has a resettable template
        this._checkHasTemplate();
    }

    async _checkHasTemplate() {
        if (!this._currentFile || !this._resetFileBtn) {
            this._hasTemplate = false;
            return;
        }

        try {
            const response = await fetch(`/api/models/${this._currentFile}/has-template`);
            if (response.ok) {
                const data = await response.json();
                this._hasTemplate = data.has_template;
                this._resetFileBtn.style.display = this._hasTemplate ? 'flex' : 'none';
            }
        } catch (error) {
            this._hasTemplate = false;
            this._resetFileBtn.style.display = 'none';
        }
    }

    async _resetFile() {
        if (!this._currentFile || !this._hasTemplate) return;

        if (!confirm(`Reset "${this._currentFile}" to its original template? This will overwrite your changes.`)) {
            return;
        }

        try {
            const response = await fetch(`/api/models/${this._currentFile}/reset`, {
                method: 'POST'
            });

            if (!response.ok) {
                throw new Error('Failed to reset file');
            }

            const data = await response.json();
            this._fileMtime = data.mtime;

            // Update editor without triggering save
            this._skipSave = true;
            this.editor.setValue(data.content);

            // Clear any pending debounce and render immediately
            if (this.debounceTimer) {
                clearTimeout(this.debounceTimer);
                this.debounceTimer = null;
            }
            this._render();

            console.log(`Reset ${this._currentFile} to original template`);
        } catch (error) {
            console.error('Failed to reset file:', error);
            this._showError(`Failed to reset file: ${error.message}`);
        }
    }

    _startFileWatcher() {
        // Poll for file changes every 2 seconds
        this._fileWatchInterval = setInterval(() => {
            this._checkFileChanged();
        }, 2000);
    }

    async _checkFileChanged() {
        if (!this._currentFile || this._fileMtime === null) return;

        // Don't check if we just saved (within last 3 seconds)
        if (Date.now() - this._lastSaveTime < 3000) return;

        // Don't check if currently rendering or processing chat
        if (this._isRendering || this._isProcessing) return;

        try {
            const response = await fetch(`/api/models/${this._currentFile}/mtime`);
            if (!response.ok) return;

            const data = await response.json();
            if (data.mtime !== this._fileMtime) {
                console.log(`File ${this._currentFile} changed externally, reloading...`);
                await this._reloadCurrentFile();
            }
        } catch (error) {
            // Ignore errors during polling
        }
    }

    async _reloadCurrentFile() {
        if (!this._currentFile) return;

        try {
            const response = await fetch(`/api/models/${this._currentFile}`);
            if (!response.ok) return;

            const data = await response.json();
            this._fileMtime = data.mtime;

            // Update editor without triggering save
            this._skipSave = true;
            this.editor.setValue(data.content);

            // Clear any pending debounce and render immediately
            if (this.debounceTimer) {
                clearTimeout(this.debounceTimer);
                this.debounceTimer = null;
            }
            this._render();

            console.log(`Reloaded ${this._currentFile}`);
        } catch (error) {
            console.warn('Failed to reload file:', error);
        }
    }

    _initFileManager() {
        this._fileSelectorBtn = document.getElementById('file-selector-btn');
        this._fileDropdown = document.getElementById('file-dropdown');
        this._fileList = document.getElementById('file-list');
        this._newFileInput = document.getElementById('new-file-input');
        this._createFileBtn = document.getElementById('create-file-btn');
        this._resetFileBtn = document.getElementById('reset-file-btn');

        // Toggle dropdown on button click
        this._fileSelectorBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this._toggleFileDropdown();
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!this._fileDropdown.contains(e.target) && !this._fileSelectorBtn.contains(e.target)) {
                this._closeFileDropdown();
            }
        });

        // Create new file
        this._createFileBtn.addEventListener('click', () => this._createNewFile());
        this._newFileInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                this._createNewFile();
            }
        });

        // Reset file to template
        this._resetFileBtn.addEventListener('click', () => this._resetFile());
    }

    _toggleFileDropdown() {
        const isOpen = this._fileDropdown.classList.contains('open');
        if (isOpen) {
            this._closeFileDropdown();
        } else {
            this._openFileDropdown();
        }
    }

    async _openFileDropdown() {
        this._fileSelectorBtn.classList.add('open');
        this._fileDropdown.classList.add('open');
        await this._loadFileList();
    }

    _closeFileDropdown() {
        this._fileSelectorBtn.classList.remove('open');
        this._fileDropdown.classList.remove('open');
    }

    async _loadFileList() {
        try {
            const response = await fetch('/api/models');
            if (!response.ok) throw new Error('Failed to list models');

            const data = await response.json();
            this._availableFiles = data.files || [];

            // Render file list
            this._fileList.innerHTML = '';
            for (const filename of this._availableFiles) {
                const item = document.createElement('div');
                item.className = 'file-item' + (filename === this._currentFile ? ' active' : '');
                item.innerHTML = `
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                        <polyline points="14 2 14 8 20 8"></polyline>
                    </svg>
                    <span>${filename}</span>
                `;
                item.addEventListener('click', () => this._selectFile(filename));
                this._fileList.appendChild(item);
            }
        } catch (error) {
            console.error('Failed to load file list:', error);
            this._fileList.innerHTML = '<div class="file-item">Error loading files</div>';
        }
    }

    async _selectFile(filename) {
        if (filename === this._currentFile) {
            this._closeFileDropdown();
            return;
        }

        try {
            const response = await fetch(`/api/models/${filename}`);
            if (!response.ok) throw new Error(`Failed to load ${filename}`);

            const data = await response.json();
            this._currentFile = data.filename;
            this._fileMtime = data.mtime;
            this.editor.setValue(data.content);
            this._updateFilenameDisplay();
            this._closeFileDropdown();

            // Save to localStorage and update URL for persistence
            localStorage.setItem('cad-editor-last-file', this._currentFile);
            this._updateUrlWithModel();

            // Trigger re-render
            this._render();
        } catch (error) {
            console.error('Failed to load file:', error);
            this._showError(`Failed to load ${filename}: ${error.message}`);
        }
    }

    async _createNewFile() {
        let filename = this._newFileInput.value.trim();
        if (!filename) return;

        // Ensure .js extension
        if (!filename.endsWith('.js')) {
            filename += '.js';
        }

        // Check for invalid characters
        if (!/^[a-zA-Z0-9_-]+\.js$/.test(filename)) {
            this._showError('Invalid filename. Use only letters, numbers, dashes, and underscores.');
            return;
        }

        // Check if file already exists
        if (this._availableFiles.includes(filename)) {
            this._selectFile(filename);
            return;
        }

        try {
            // Create new file with template content
            const templateContent = `// ${filename.replace('.js', '')}
// New CAD model - edit this code to create 3D shapes

const result = new Workplane("XY").box(20, 20, 20);
result;
`;

            const response = await fetch(`/api/models/${filename}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content: templateContent })
            });

            if (!response.ok) throw new Error('Failed to create file');

            // Load the new file
            this._currentFile = filename;
            this.editor.setValue(templateContent);
            this._updateFilenameDisplay();
            this._newFileInput.value = '';
            this._closeFileDropdown();

            // Save to localStorage and update URL for persistence
            localStorage.setItem('cad-editor-last-file', this._currentFile);
            this._updateUrlWithModel();

            // Trigger re-render
            this._render();
        } catch (error) {
            console.error('Failed to create file:', error);
            this._showError(`Failed to create ${filename}: ${error.message}`);
        }
    }

    async _saveFile() {
        if (!this._currentFile) return;

        // Skip save if file update came from agent
        if (this._skipSave) {
            this._skipSave = false;
            return;
        }

        try {
            const content = this.editor.getValue();
            this._lastSaveTime = Date.now();
            const response = await fetch(`/api/models/${this._currentFile}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content })
            });

            if (response.ok) {
                // Update our known mtime to avoid triggering hot reload
                const mtimeResponse = await fetch(`/api/models/${this._currentFile}/mtime`);
                if (mtimeResponse.ok) {
                    const data = await mtimeResponse.json();
                    this._fileMtime = data.mtime;
                }
            } else {
                console.warn('Failed to save file:', response.statusText);
            }
        } catch (error) {
            console.warn('Failed to save file:', error);
        }
    }

    _onCodeChange() {
        // Clear previous timer
        if (this.debounceTimer) {
            clearTimeout(this.debounceTimer);
        }

        // If currently rendering, cancel immediately
        if (this._isRendering) {
            this._cancelRender();
        }

        // Set new timer - don't show "Compiling" until we actually start
        this.debounceTimer = setTimeout(() => {
            this._render();
        }, this.debounceDelay);
    }

    _cancelRender() {
        // Terminate the worker to cancel any in-progress render
        if (this._worker) {
            console.log('Cancelling render - terminating worker');
            this._worker.terminate();
            this._isRendering = false;
            this._isDirty = false;
            this._pendingCode = null;

            // Swap to spare worker if available (instant)
            if (this._spareWorker && this._spareWorkerReady) {
                console.log('[CAD] Swapping to spare worker (instant)');
                this._worker = this._spareWorker;
                this._workerReady = true;
                this._attachWorkerHandlers(this._worker);
                this._spareWorker = null;
                this._spareWorkerReady = false;

                // Start creating a new spare in the background
                this._initSpareWorker();
            } else {
                // No spare available, need to wait for new worker
                console.log('[CAD] No spare worker available, creating new one');
                this._worker = null;
                this._workerReady = false;
                this._setStatus('loading', 'Restarting...');
                this._recreateWorker();
            }
        }
    }

    // Create a new spare worker in the background
    async _initSpareWorker() {
        try {
            console.log('[CAD] Starting spare worker initialization in background');
            this._spareWorker = await this._createWorkerInstance(false);
            this._spareWorkerReady = true;
            console.log('[CAD] Spare worker ready');
        } catch (error) {
            console.error('[CAD] Failed to create spare worker:', error);
            this._spareWorker = null;
            this._spareWorkerReady = false;
        }
    }

    // Fallback: create new main worker when no spare available
    async _recreateWorker() {
        try {
            console.log('[CAD] Creating new main worker');
            const worker = await this._createWorkerInstance(true);
            this._worker = worker;
            this._workerReady = true;
            this._attachWorkerHandlers(this._worker);
            this.isReady = true;
            this._setStatus('ready', 'Ready');

            // Also create a spare now
            this._initSpareWorker();
        } catch (error) {
            console.error('Failed to recreate worker:', error);
        }
    }

    _render() {
        if (!this._workerReady) return;

        const code = this.editor.getValue();
        this._hideError();
        this._downloadSTLBtn.disabled = true;
        this._download3MFBtn.disabled = true;

        // If already rendering, mark dirty and save the pending code
        if (this._isRendering) {
            this._isDirty = true;
            this._pendingCode = code;
            return;
        }

        this._startRender(code);
    }

    _startRender(code) {
        if (!this._workerReady || this._isRendering) return;

        this._isRendering = true;
        this._renderRequestId++;
        this._clearConsole(); // Clear console for new render
        this._setStatus('loading', 'Compiling...');

        // Send code to worker for rendering
        this._worker.postMessage({
            type: 'render',
            code: code,
            id: this._renderRequestId
        });
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
        if (!this._workerReady) {
            this._showError('CAD engine not ready');
            return;
        }

        this._setStatus('loading', 'Exporting STL...');
        const code = this.editor.getValue();
        this._worker.postMessage({ type: 'exportSTL', code, id: Date.now() });
    }

    _download3MF() {
        if (!this._workerReady) {
            this._showError('CAD engine not ready');
            return;
        }

        this._setStatus('loading', 'Exporting 3MF...');
        const code = this.editor.getValue();
        this._worker.postMessage({ type: 'export3MF', code, id: Date.now() });
    }

    _handleExportSTLComplete(buffer) {
        const blob = new Blob([buffer], { type: 'application/sla' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = (this._currentFile || 'model').replace('.js', '') + '.stl';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        this._setStatus('ready', 'Ready');
    }

    _handleExport3MFComplete(buffer) {
        const blob = new Blob([buffer], { type: 'application/vnd.ms-package.3dmanufacturing-3dmodel+xml' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = (this._currentFile || 'model').replace('.js', '') + '.3mf';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        this._setStatus('ready', 'Ready');
    }

    _handleExportError(format, error) {
        console.error(`${format} export failed:`, error);
        this._setStatus('error', 'Export failed');
        this._showError(`${format} export failed: ${error}`);
    }

    _initOpacitySlider() {
        const slider = document.getElementById('opacity-slider');
        const valueDisplay = document.getElementById('opacity-value');

        if (slider && valueDisplay) {
            // Set initial value from viewer
            slider.value = this.viewer.getOpacity() * 100;
            valueDisplay.textContent = slider.value + '%';

            slider.addEventListener('input', () => {
                const opacity = parseInt(slider.value) / 100;
                this.viewer.setOpacity(opacity);
                valueDisplay.textContent = slider.value + '%';
            });
        }
    }

    _initConsole() {
        this._consoleOutput = document.getElementById('console-output');
        this._consoleClearBtn = document.getElementById('console-clear-btn');

        if (this._consoleClearBtn) {
            this._consoleClearBtn.addEventListener('click', () => {
                this._clearConsole();
            });
        }
    }

    _appendConsole(level, message) {
        if (!this._consoleOutput) return;

        const line = document.createElement('div');
        line.className = `console-line ${level}`;
        line.textContent = message;
        this._consoleOutput.appendChild(line);

        // Auto-scroll to bottom
        this._consoleOutput.scrollTop = this._consoleOutput.scrollHeight;
    }

    _clearConsole() {
        if (this._consoleOutput) {
            this._consoleOutput.innerHTML = '';
        }
    }

    _initChat() {
        this._chatInput = document.getElementById('chat-input');
        this._chatSendBtn = document.getElementById('chat-send-btn');
        this._chatMessages = document.getElementById('chat-messages');

        // Enter key to send
        this._chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this._sendChatMessage();
            }
        });

        // Send button click
        this._chatSendBtn.addEventListener('click', () => {
            this._sendChatMessage();
        });
    }

    _enableChat() {
        this._chatInput.disabled = false;
        this._chatSendBtn.disabled = false;
        this._chatInput.placeholder = 'Ask to modify the model...';
    }

    _disableChat() {
        this._chatInput.disabled = true;
        this._chatSendBtn.disabled = true;
    }

    _lockEditor() {
        if (this.editor) {
            this.editor.updateOptions({ readOnly: true });
        }
    }

    _unlockEditor() {
        if (this.editor) {
            this.editor.updateOptions({ readOnly: false });
        }
    }

    _addChatMessage(role, content) {
        const messageEl = document.createElement('div');
        messageEl.className = `chat-message ${role}`;
        messageEl.textContent = content;
        this._chatMessages.appendChild(messageEl);
        this._chatMessages.scrollTop = this._chatMessages.scrollHeight;
    }

    _showTypingIndicator() {
        const indicator = document.createElement('div');
        indicator.className = 'chat-typing';
        indicator.id = 'chat-typing-indicator';
        indicator.innerHTML = '<span class="chat-typing-dot"></span><span class="chat-typing-dot"></span><span class="chat-typing-dot"></span>';
        this._chatMessages.appendChild(indicator);
        this._chatMessages.scrollTop = this._chatMessages.scrollHeight;
    }

    _hideTypingIndicator() {
        const indicator = document.getElementById('chat-typing-indicator');
        if (indicator) {
            indicator.remove();
        }
    }

    async _waitForRenderComplete() {
        // Wait for any pending render to complete
        while (this._isRendering) {
            await new Promise(resolve => setTimeout(resolve, 50));
        }
        // Also wait for debounce timer to clear
        if (this.debounceTimer) {
            await new Promise(resolve => setTimeout(resolve, this.debounceDelay + 100));
        }
    }

    async _sendChatMessage() {
        const message = this._chatInput.value.trim();
        if (!message || this._isProcessing) return;

        // Wait for any pending render
        await this._waitForRenderComplete();

        // Set processing state
        this._isProcessing = true;
        this._disableChat();
        this._lockEditor();

        // Show user message
        this._addChatMessage('user', message);
        this._chatInput.value = '';

        // Show typing indicator
        this._showTypingIndicator();

        try {
            const response = await fetch('/api/chat/message', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: message,
                    current_file: this._currentFile,
                    current_code: this.editor.getValue()
                })
            });

            if (!response.ok) {
                throw new Error(`Server error: ${response.status}`);
            }

            const data = await response.json();

            // Hide typing indicator
            this._hideTypingIndicator();

            // Show assistant response
            if (data.response) {
                this._addChatMessage('assistant', data.response);
            }

            // If file was changed by agent, update editor
            if (data.file_changed && data.new_content) {
                this._skipSave = true; // Don't save this change (agent already did)
                this.editor.setValue(data.new_content);
                // Render will be triggered by onDidChangeModelContent
            }

        } catch (error) {
            this._hideTypingIndicator();
            this._addChatMessage('error', `Error: ${error.message}`);
        } finally {
            // Restore normal state
            this._isProcessing = false;
            this._enableChat();
            this._unlockEditor();
            this._chatInput.focus();
        }
    }

    _initProperties() {
        this._propertiesList = document.getElementById('properties-list');
    }

    _parseAndRenderProperties() {
        const code = this.editor ? this.editor.getValue() : '';
        this._properties = this._parseNumericVariables(code);
        this._renderProperties();
    }

    _parseNumericVariables(code) {
        const properties = [];

        try {
            const ast = acorn.parse(code, {
                ecmaVersion: 2022,
                sourceType: 'module',
                locations: true,
                ranges: true
            });

            // Walk the AST to find numeric variable declarations
            for (const node of ast.body) {
                if (node.type === 'VariableDeclaration') {
                    for (const declarator of node.declarations) {
                        if (declarator.id.type === 'Identifier' &&
                            declarator.init &&
                            declarator.init.type === 'Literal' &&
                            typeof declarator.init.value === 'number') {

                            properties.push({
                                name: declarator.id.name,
                                value: declarator.init.value,
                                start: declarator.init.start,
                                end: declarator.init.end
                            });
                        }
                    }
                }
            }
        } catch (e) {
            // Parsing failed - code may be invalid, just return empty
            console.log('Property parsing skipped (invalid code):', e.message);
        }

        return properties;
    }

    _renderProperties() {
        if (!this._propertiesList) return;

        if (this._properties.length === 0) {
            this._propertiesList.innerHTML = '<div class="properties-empty">No numeric properties found</div>';
            return;
        }

        this._propertiesList.innerHTML = '';

        for (const prop of this._properties) {
            const item = document.createElement('div');
            item.className = 'property-item';

            // Determine slider range based on current value
            const absValue = Math.abs(prop.value);
            let min, max, step;
            if (absValue === 0) {
                min = -100;
                max = 100;
                step = 1;
            } else if (Number.isInteger(prop.value) && absValue < 1000) {
                min = Math.floor(prop.value - absValue * 2);
                max = Math.ceil(prop.value + absValue * 2);
                step = 1;
            } else {
                min = prop.value - absValue * 2;
                max = prop.value + absValue * 2;
                step = absValue / 100;
            }

            item.innerHTML = `
                <span class="property-name">${prop.name}</span>
                <input type="range" class="property-slider"
                       min="${min}" max="${max}" step="${step}"
                       value="${prop.value}"
                       data-prop-name="${prop.name}">
                <input type="number" class="property-value"
                       value="${prop.value}" step="${step}"
                       data-prop-name="${prop.name}">
            `;

            const slider = item.querySelector('.property-slider');
            const numberInput = item.querySelector('.property-value');

            // Sync slider and number input
            slider.addEventListener('input', () => {
                const newValue = parseFloat(slider.value);
                numberInput.value = newValue;
                this._updatePropertyInCode(prop.name, newValue);
            });

            numberInput.addEventListener('input', () => {
                const newValue = parseFloat(numberInput.value);
                if (!isNaN(newValue)) {
                    slider.value = newValue;
                    this._updatePropertyInCode(prop.name, newValue);
                }
            });

            this._propertiesList.appendChild(item);
        }
    }

    _updatePropertyInCode(propName, newValue) {
        const code = this.editor.getValue();

        try {
            const ast = acorn.parse(code, {
                ecmaVersion: 2022,
                sourceType: 'module',
                locations: true,
                ranges: true
            });

            // Find the property in the AST
            let targetNode = null;
            for (const node of ast.body) {
                if (node.type === 'VariableDeclaration') {
                    for (const declarator of node.declarations) {
                        if (declarator.id.type === 'Identifier' &&
                            declarator.id.name === propName &&
                            declarator.init &&
                            declarator.init.type === 'Literal' &&
                            typeof declarator.init.value === 'number') {
                            targetNode = declarator.init;
                            break;
                        }
                    }
                }
                if (targetNode) break;
            }

            if (targetNode) {
                // Replace the value in the code string directly
                // This preserves formatting better than regenerating entire AST
                const before = code.substring(0, targetNode.start);
                const after = code.substring(targetNode.end);
                const newCode = before + String(newValue) + after;

                this._sliderTriggeredChange = true;
                this.editor.setValue(newCode);
            }
        } catch (e) {
            console.error('Failed to update property:', e);
        }
    }
}

// Start the application
window.cadEditor = new CADEditor();
