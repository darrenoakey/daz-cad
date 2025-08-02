// Library core functionality - main initialization and coordination

function initLibrary() {
    console.log("🔄 Starting initLibrary()");
    
    // Initialize UI components
    console.log("🎨 Initializing library UI components...");
    window.libraryUI.initLibraryUI();
    
    // Load library files
    console.log("📚 Loading library files...");
    window.libraryFileOps.loadLibraryFiles();
    
    console.log("✅ initLibrary() completed");
}

// Export main functions for backward compatibility
window.initLibrary = initLibrary;
window.setupAutoSave = window.libraryFileOps.setupAutoSave;
window.saveCurrentFile = window.libraryFileOps.saveCurrentFile;

console.log("📚 Library core module loaded");
