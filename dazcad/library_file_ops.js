// Library file operations - coordination module that combines loading and execution

// Import the specialized modules (will be loaded before this file in index.html)
// library_file_loader.js and library_code_executor.js should be loaded first

// Export unified API that maintains backward compatibility
window.libraryFileOps = {
    loadLibraryFiles: () => window.libraryFileLoader?.loadLibraryFiles(),
    loadFile: (name, type) => window.libraryFileLoader?.loadFile(name, type),
    autoRunCode: () => window.libraryCodeExecutor?.autoRunCode(),
    saveCurrentFile: () => window.librarySaveOps?.saveCurrentFile(),
    handleNameChange: (event) => window.librarySaveOps?.handleNameChange(event),
    createNewFile: () => window.librarySaveOps?.createNewFile(),
    setupAutoSave: () => window.autoSave?.setupAutoSave()
};

console.log("\ud83d\udcda Library file operations coordination module loaded");
