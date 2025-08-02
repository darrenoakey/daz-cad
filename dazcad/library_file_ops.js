// Library file operations - coordination module that combines loading and execution

// Import the specialized modules (will be loaded before this file in index.html)
// library_file_loader.js and library_code_executor.js should be loaded first

// Helper function to refresh library list without auto-loading files
async function refreshLibraryList() {
    return window.libraryFileLoader?.loadLibraryFiles(false);
}

// Export unified API that maintains backward compatibility
window.libraryFileOps = {
    loadLibraryFiles: (autoLoadFirst = true) => window.libraryFileLoader?.loadLibraryFiles(autoLoadFirst),
    refreshLibraryList: refreshLibraryList,
    loadFile: (name, type) => window.libraryFileLoader?.loadFile(name, type),
    autoRunCode: () => window.libraryCodeExecutor?.autoRunCode(),
    saveCurrentFile: () => window.librarySaveOps?.saveCurrentFile(),
    handleNameChange: (event) => window.librarySaveOps?.handleNameChange(event),
    createNewFile: () => window.librarySaveOps?.createNewFile(),
    setupAutoSave: () => window.autoSave?.setupAutoSave()
};

console.log("📚 Library file operations coordination module loaded");
