/**
 * CAD Editor - Main Application
 *
 * Integrates Monaco editor with CAD library and Three.js viewer
 * for live preview of CAD code.
 */

import { CADViewer } from './viewer.js';
import { initCAD, Workplane, Assembly } from './cad.js';

// Fallback code in case server load fails
const FALLBACK_CODE = `// CAD Example
const result = new Workplane("XY").box(20, 20, 20);
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
        this._currentFile = null; // Current file being edited
        this._downloadSTLBtn = null;
        this._download3MFBtn = null;

        // Chat state
        this._isProcessing = false; // True when waiting for agent response
        this._isRendering = false; // True during render cycle
        this._skipSave = false; // True when file update came from agent
        this._chatInput = null;
        this._chatSendBtn = null;
        this._chatMessages = null;

        // File manager state
        this._fileSelectorBtn = null;
        this._fileDropdown = null;
        this._fileList = null;
        this._newFileInput = null;
        this._createFileBtn = null;
        this._availableFiles = [];

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

        // Initialize file manager
        this._initFileManager();

        // Initialize chat UI
        this._initChat();

        // Load Monaco editor
        await this._loadMonaco();

        // Initialize OpenCascade
        await this._initOpenCascade();

        // Load default file from server
        await this._loadDefaultFile();

        // Set up editor change listener
        this.editor.onDidChangeModelContent(() => {
            this._onCodeChange();
        });

        // Enable chat now that everything is ready
        this._enableChat();

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

    async _loadDefaultFile() {
        try {
            const response = await fetch('/api/models');
            if (!response.ok) throw new Error('Failed to list models');

            const data = await response.json();
            const filename = data.default || 'default.js';

            const fileResponse = await fetch(`/api/models/${filename}`);
            if (!fileResponse.ok) throw new Error(`Failed to load ${filename}`);

            const fileData = await fileResponse.json();
            this._currentFile = fileData.filename;
            this.editor.setValue(fileData.content);
            this._updateFilenameDisplay();

        } catch (error) {
            console.warn('Failed to load default file from server:', error);
            this.editor.setValue(FALLBACK_CODE);
            this._currentFile = 'default.js';
            this._updateFilenameDisplay();
        }
    }

    _updateFilenameDisplay() {
        const el = document.getElementById('filename-display');
        if (el && this._currentFile) {
            el.textContent = this._currentFile;
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
            this.editor.setValue(data.content);
            this._updateFilenameDisplay();
            this._closeFileDropdown();

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
            const response = await fetch(`/api/models/${this._currentFile}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content })
            });

            if (!response.ok) {
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

        // Show loading state
        this._setStatus('loading', 'Compiling...');

        // Set new timer
        this.debounceTimer = setTimeout(() => {
            this._render();
        }, this.debounceDelay);
    }

    _render() {
        if (!this.isReady) return;

        this._isRendering = true;
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
                    this._saveFile();
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
                    this._saveFile();
                } else {
                    throw new Error('Failed to generate mesh from shape');
                }
            } else if (result && typeof result === 'object' && result.vertices) {
                // Already mesh data - can't export to STL
                this.viewer.displayMesh(result);
                this._setStatus('ready', 'Ready');
                this._saveFile();
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
        } finally {
            this._isRendering = false;
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
new CADEditor();
