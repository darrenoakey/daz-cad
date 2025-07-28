// Auto-save functionality for the editor

let saveTimeout = null;
let lastSavedContent = '';
let lastSavedName = '';

function getLastSavedContent() {
    return lastSavedContent;
}

function setLastSavedContent(content) {
    lastSavedContent = content;
}

function getLastSavedName() {
    return lastSavedName;
}

function setLastSavedName(name) {
    lastSavedName = name;
}

function hasContentChanged(currentContent, currentName) {
    return currentContent !== lastSavedContent || currentName !== lastSavedName;
}

function setupAutoSave() {
    if (window.codeEditor) {
        window.codeEditor.on('change', () => {
            if (saveTimeout) {
                clearTimeout(saveTimeout);
            }
            
            saveTimeout = setTimeout(() => {
                if (window.libraryFileOps && window.libraryFileOps.saveCurrentFile) {
                    window.libraryFileOps.saveCurrentFile();
                }
            }, 2000);
        });
    }
}

// Export to global namespace
window.autoSave = {
    getLastSavedContent,
    setLastSavedContent,
    getLastSavedName,
    setLastSavedName,
    hasContentChanged,
    setupAutoSave
};
