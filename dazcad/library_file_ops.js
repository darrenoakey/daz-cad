// Library file operations - loading, saving, creating files

async function loadLibraryFiles() {
    try {
        const response = await fetch('/library/list');
        const data = await response.json();
        
        if (data.success) {
            window.libraryUI.setLibraryFiles(data.files);
            window.libraryUI.renderLibraryList();
            await loadFile('example', 'builtin');
        }
    } catch (error) {
        console.error('Failed to load library files:', error);
    }
}

async function loadFile(name, type) {
    const outputDiv = document.getElementById('output');
    
    // Show loading indicator with spinner - make it more prominent
    if (outputDiv) {
        outputDiv.innerHTML = '<div class="loading-output" style="font-size: 1.2em; color: #007acc;">⏳ Loading file... Please wait</div>';
    }
    
    // Also add visual feedback to the library list
    const libraryItems = document.querySelectorAll('.library-item');
    libraryItems.forEach(item => {
        if (item.textContent.includes(name)) {
            item.style.opacity = '0.5';
            item.style.cursor = 'wait';
        }
    });
    
    try {
        const response = await fetch(`/library/get/${type}/${encodeURIComponent(name)}`);
        const data = await response.json();
        
        if (data.success) {
            window.libraryUI.setCurrentFile({ name, type });
            
            if (window.codeEditor) {
                window.codeEditor.setValue(data.content);
                window.autoSave.setLastSavedContent(data.content);
                // Also save the current file name
                window.autoSave.setLastSavedName(name);
            }
            
            const nameInput = document.getElementById('modelName');
            if (nameInput) nameInput.value = name;
            
            window.libraryUI.renderLibraryList();
            
            // Keep the loading message a bit longer for better UX
            if (outputDiv) {
                outputDiv.innerHTML = '<div class="info-output">📄 File loaded. Running code...</div>';
            }
            
            // Small delay before running to ensure user sees the loading message
            await new Promise(resolve => setTimeout(resolve, 300));
            
            if (window.runCode) await autoRunCode();
        } else {
            console.error('Failed to load file:', data.error);
            if (outputDiv) {
                outputDiv.innerHTML = `<span class="error-output">Failed to load file: ${data.error || 'Unknown error'}</span>`;
            }
        }
    } catch (error) {
        console.error('Error loading file:', error);
        if (outputDiv) {
            outputDiv.innerHTML = `<span class="error-output">Failed to load file: ${error.message}</span>`;
        }
    } finally {
        // Restore library items visual state
        libraryItems.forEach(item => {
            item.style.opacity = '1';
            item.style.cursor = 'pointer';
        });
    }
}

async function autoRunCode() {
    const code = window.codeEditor.getValue();
    const outputDiv = document.getElementById('output');
    
    try {
        const response = await fetch('/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code: code })
        });
        
        const result = await response.json();
        
        if (result.success) {
            if (window.clearScene) window.clearScene();
            
            result.objects.forEach(obj => {
                if (window.loadSTL) {
                    window.loadSTL(obj.stl, obj.name, obj.color, obj.transform);
                }
            });
            
            let outputContent = '<span class="success-output">✓ Code executed successfully!</span>';
            if (result.output && result.output.trim()) {
                outputContent += '\n' + result.output;
            }
            outputDiv.innerHTML = outputContent;
        } else {
            let errorMessage = `<span class="error-output">Auto-run Error: ${result.error}</span>`;
            if (result.traceback) {
                errorMessage += `\n\n<span class="traceback-output">Stack trace:\n${result.traceback}</span>`;
            }
            outputDiv.innerHTML = errorMessage;
        }
    } catch (error) {
        outputDiv.innerHTML = `<span class="error-output">Auto-run Network error: ${error.message}</span>`;
    }
}

// Export to global namespace
window.libraryFileOps = {
    loadLibraryFiles,
    loadFile,
    saveCurrentFile: () => window.librarySaveOps?.saveCurrentFile(),
    handleNameChange: (event) => window.librarySaveOps?.handleNameChange(event),
    createNewFile: () => window.librarySaveOps?.createNewFile(),
    setupAutoSave: window.autoSave.setupAutoSave
};
