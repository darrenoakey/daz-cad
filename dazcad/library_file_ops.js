// Library file operations - loading, saving, creating files

async function loadLibraryFiles() {
    try {
        const response = await fetch('/library/list');
        const data = await response.json();
        
        if (data.success) {
            window.libraryUI.setLibraryFiles(data.files);
            window.libraryUI.renderLibraryList();
            
            // Load the default example file
            await loadFile('example', 'builtin');
        }
    } catch (error) {
        console.error('Failed to load library files:', error);
    }
}

async function loadFile(name, type) {
    try {
        const response = await fetch(`/library/get/${type}/${encodeURIComponent(name)}`);
        const data = await response.json();
        
        if (data.success) {
            // Update current file
            const newFile = { name, type };
            window.libraryUI.setCurrentFile(newFile);
            
            // Update editor
            if (window.codeEditor) {
                window.codeEditor.setValue(data.content);
            }
            
            // Update name field
            const nameInput = document.getElementById('modelName');
            if (nameInput) {
                nameInput.value = name;
            }
            
            // Update active state in list
            window.libraryUI.renderLibraryList();
            
            // Run the code and handle errors properly
            if (window.runCode) {
                await autoRunCode();
            }
        } else {
            console.error('Failed to load file:', data.error);
        }
    } catch (error) {
        console.error('Error loading file:', error);
    }
}

async function autoRunCode() {
    // Auto-run version that properly shows errors like manual run
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
            if (window.clearScene) {
                window.clearScene();
            }
            result.objects.forEach(obj => {
                if (window.loadSTL) {
                    window.loadSTL(obj.stl, obj.name, obj.color, obj.transform);
                }
            });
            outputDiv.innerHTML = `<span class="success-output">Auto-run completed!</span>\n${result.output || ''}`;
        } else {
            // Show full error with traceback if available, same as manual run
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

async function saveCurrentFile() {
    if (!window.codeEditor) return;
    
    const content = window.codeEditor.getValue();
    const nameInput = document.getElementById('modelName');
    const currentFile = window.libraryUI.currentFile;
    const name = nameInput ? nameInput.value.trim() : currentFile.name;
    
    if (!name) {
        console.error('No file name specified');
        return;
    }
    
    try {
        const response = await fetch('/library/save', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                name: name,
                content: content,
                old_name: currentFile.name !== name ? currentFile.name : null,
                type: currentFile.type
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Update current file name if changed
            if (currentFile.name !== name) {
                window.libraryUI.setCurrentFile({ name, type: currentFile.type });
                // Reload library list
                await loadLibraryFiles();
            }
            
            // Show success feedback
            const output = document.getElementById('output');
            if (output) {
                output.innerHTML = `<div class="success-output">✓ ${data.message}</div>`;
            }
            
            // Update the 3D view if run was successful
            if (data.run_result && data.run_result.success && window.updateViewer) {
                window.updateViewer(data.run_result.objects);
            } else if (data.run_result && !data.run_result.success) {
                // Show save errors with traceback if available
                let errorMessage = `<span class="error-output">Save Error: ${data.run_result.error}</span>`;
                if (data.run_result.traceback) {
                    errorMessage += `\n\n<span class="traceback-output">Stack trace:\n${data.run_result.traceback}</span>`;
                }
                output.innerHTML = errorMessage;
            }
        } else {
            console.error('Failed to save file:', data.error);
            const output = document.getElementById('output');
            if (output) {
                output.innerHTML = `<div class="error-output">Error: ${data.error}</div>`;
            }
        }
    } catch (error) {
        console.error('Error saving file:', error);
    }
}

async function handleNameChange(event) {
    const newName = event.target.value.trim();
    const currentFile = window.libraryUI.currentFile;
    
    if (!newName || newName === currentFile.name) {
        // Reset to current name if empty
        if (!newName) {
            event.target.value = currentFile.name;
        }
        return;
    }
    
    // Save with new name (this will handle rename)
    await saveCurrentFile();
}

async function createNewFile() {
    const name = prompt('Enter name for new file:');
    if (!name) return;
    
    // Sanitize name
    const sanitizedName = name.replace(/[^a-zA-Z0-9_-]/g, '_');
    
    try {
        const response = await fetch('/library/create', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ name: sanitizedName })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Reload library and open the new file
            await loadLibraryFiles();
            await loadFile(sanitizedName, 'user');
        } else {
            alert(`Failed to create file: ${data.error || data.message}`);
        }
    } catch (error) {
        console.error('Error creating file:', error);
        alert('Failed to create file');
    }
}

// Auto-save functionality
let saveTimeout = null;

function setupAutoSave() {
    if (window.codeEditor) {
        window.codeEditor.on('change', () => {
            // Clear existing timeout
            if (saveTimeout) {
                clearTimeout(saveTimeout);
            }
            
            // Set new timeout for auto-save
            saveTimeout = setTimeout(() => {
                saveCurrentFile();
            }, 2000); // Save 2 seconds after last change
        });
    }
}

// Export to global namespace
window.libraryFileOps = {
    loadLibraryFiles,
    loadFile,
    saveCurrentFile,
    handleNameChange,
    createNewFile,
    setupAutoSave
};
