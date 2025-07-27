// Library core functionality - main initialization and coordination

function initLibrary() {
    // Initialize UI components
    window.libraryUI.initLibraryUI();
    
    // Load library files
    window.libraryFileOps.loadLibraryFiles();
}

// Export main functions for backward compatibility
window.initLibrary = initLibrary;
window.setupAutoSave = window.libraryFileOps.setupAutoSave;
window.saveCurrentFile = window.libraryFileOps.saveCurrentFile;
