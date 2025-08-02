// Library UI coordination module - combines rendering and controls
// Import the specialized modules (will be loaded before this file in index.html)
// library_ui_rendering.js and library_ui_controls.js should be loaded first

// Export unified API that maintains backward compatibility
window.libraryUI = {
    // Expose state from rendering module
    get currentFile() { return window.libraryUIRendering?.currentFile; },
    get libraryFiles() { return window.libraryUIRendering?.libraryFiles; },
    get isLibraryVisible() { return window.libraryUIControls?.isLibraryVisible; },
    
    // Rendering functions
    renderLibraryList: () => window.libraryUIRendering?.renderLibraryList(),
    createLibraryItem: (file, type) => window.libraryUIRendering?.createLibraryItem(file, type),
    filterLibraryList: () => window.libraryUIRendering?.filterLibraryList(),
    
    // Control functions
    toggleLibraryPanel: () => window.libraryUIControls?.toggleLibraryPanel(),
    initLibraryUI: () => window.libraryUIControls?.initLibraryUI(),
    
    // Setters for state - delegate to appropriate modules
    setCurrentFile: (file) => window.libraryUIRendering?.setCurrentFile(file),
    setLibraryFiles: (files) => window.libraryUIRendering?.setLibraryFiles(files),
    setLibraryVisible: (visible) => window.libraryUIControls?.setLibraryVisible(visible)
};

console.log("\ud83c\udfa8 Library UI coordination module loaded");
