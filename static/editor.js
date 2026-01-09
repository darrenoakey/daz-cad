/**
 * CAD Editor - Main Application
 *
 * Integrates Monaco editor with CAD library and Three.js viewer
 * for live preview of CAD code.
 */

import { CADViewer } from './viewer.js';
import { initCAD, Workplane, Assembly, Profiler } from './cad.js';

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

        // File manager state
        this._fileSelectorBtn = null;
        this._fileDropdown = null;
        this._fileList = null;
        this._newFileInput = null;
        this._createFileBtn = null;
        this._availableFiles = [];

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
        });

        // Enable chat now that everything is ready
        this._enableChat();

        // Start file watcher for hot reload
        this._startFileWatcher();

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
            // Check localStorage for last edited file
            const lastFile = localStorage.getItem('cad-editor-last-file');

            // If we have a remembered file, try to load it first
            if (lastFile) {
                try {
                    const fileResponse = await fetch(`/api/models/${lastFile}`);
                    if (fileResponse.ok) {
                        const fileData = await fileResponse.json();
                        this._currentFile = fileData.filename;
                        this._fileMtime = fileData.mtime;
                        this.editor.setValue(fileData.content);
                        this._updateFilenameDisplay();
                        return; // Successfully loaded remembered file
                    }
                } catch (e) {
                    console.warn(`Could not load remembered file ${lastFile}, falling back to default`);
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

        } catch (error) {
            console.warn('Failed to load default file from server:', error);
            this.editor.setValue(FALLBACK_CODE);
            this._currentFile = 'default.js';
            this._fileMtime = null;
            this._updateFilenameDisplay();
        }
    }

    _updateFilenameDisplay() {
        const el = document.getElementById('filename-display');
        if (el && this._currentFile) {
            el.textContent = this._currentFile;
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

            // Save to localStorage for persistence
            localStorage.setItem('cad-editor-last-file', this._currentFile);

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

            // Save to localStorage for persistence
            localStorage.setItem('cad-editor-last-file', this._currentFile);

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
}

// Start the application
window.cadEditor = new CADEditor();
