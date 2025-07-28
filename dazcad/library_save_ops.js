// Library save operations - saving, renaming, creating files

async function saveCurrentFile() {
    if (!window.codeEditor) return;
    
    const content = window.codeEditor.getValue();
    const nameInput = document.getElementById('modelName');
    const currentFile = window.libraryUI.currentFile;
    const name = nameInput ? nameInput.value.trim() : currentFile.name;
    
    if (!name) return;
    
    // Check if content or name has actually changed
    if (!window.autoSave.hasContentChanged(content, name)) {
        return;
    }
    
    try {
        const response = await fetch('/library/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: name,
                content: content,
                old_name: currentFile.name !== name ? currentFile.name : null,
                type: currentFile.type
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            window.autoSave.setLastSavedContent(content);
            window.autoSave.setLastSavedName(name);
            
            if (currentFile.name !== name) {
                window.libraryUI.setCurrentFile({ name, type: currentFile.type });
                await window.libraryFileOps.loadLibraryFiles();
            }
            
            const output = document.getElementById('output');
            if (output) {
                const currentOutput = output.innerHTML;
                
                // Only show save message if there's no test output
                // Preserve test results if they exist
                if (currentOutput.includes('Test Summary:') || 
                    currentOutput.includes('Tests:') || 
                    currentOutput.includes('FAILED') ||
                    currentOutput.includes('PASSED')) {
                    // Keep the test output and just add a small save indicator
                    const saveIndicator = document.createElement('div');
                    saveIndicator.className = 'save-indicator';
                    saveIndicator.style.cssText = 'position: absolute; top: 10px; right: 10px; ' +
                                                 'background: #4CAF50; color: white; padding: 5px 10px; ' +
                                                 'border-radius: 3px; font-size: 12px;';
                    saveIndicator.textContent = '✓ Saved';
                    output.parentElement.style.position = 'relative';
                    output.parentElement.appendChild(saveIndicator);
                    
                    // Remove the indicator after 2 seconds
                    setTimeout(() => {
                        if (saveIndicator.parentElement) {
                            saveIndicator.remove();
                        }
                    }, 2000);
                } else {
                    // No test output, show normal save message
                    output.innerHTML = `<div class="success-output">✓ ${data.message}</div>`;
                    if (currentOutput && !currentOutput.includes('Saved')) {
                        output.innerHTML += '\n' + currentOutput;
                    }
                }
            }
            
            if (data.run_result && data.run_result.success && window.updateViewer) {
                window.updateViewer(data.run_result.objects);
            } else if (data.run_result && !data.run_result.success) {
                let errorMessage = `<span class="error-output">Save Error: ${data.run_result.error}</span>`;
                if (data.run_result.traceback) {
                    errorMessage += `\n\n<span class="traceback-output">Stack trace:\n${data.run_result.traceback}</span>`;
                }
                output.innerHTML = errorMessage;
            }
        } else {
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
        if (!newName) event.target.value = currentFile.name;
        return;
    }
    
    await saveCurrentFile();
}

async function createNewFile() {
    const name = prompt('Enter name for new file:');
    if (!name) return;
    
    const sanitizedName = name.replace(/[^a-zA-Z0-9_-]/g, '_');
    
    try {
        const response = await fetch('/library/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: sanitizedName })
        });
        
        const data = await response.json();
        
        if (data.success) {
            await window.libraryFileOps.loadLibraryFiles();
            await window.libraryFileOps.loadFile(sanitizedName, 'user');
        } else {
            alert(`Failed to create file: ${data.error || data.message}`);
        }
    } catch (error) {
        console.error('Error creating file:', error);
        alert('Failed to create file');
    }
}

// Export to global namespace
window.librarySaveOps = {
    saveCurrentFile,
    handleNameChange,
    createNewFile
};
