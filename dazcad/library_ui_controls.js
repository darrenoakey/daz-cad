// Library UI controls - panel management, initialization, and interactions
let isLibraryVisible = true;

function toggleLibraryPanel() {
    console.log("\ud83d\udd04 Toggling library panel");
    const libraryPanel = document.querySelector('.library-panel');
    const mainContent = document.querySelector('.main-content');
    const toggleBtn = document.getElementById('libraryToggle');
    
    if (libraryPanel && mainContent && toggleBtn) {
        isLibraryVisible = !isLibraryVisible;
        console.log(`\ud83d\udccb Library panel visible: ${isLibraryVisible}`);
        
        if (isLibraryVisible) {
            libraryPanel.classList.remove('collapsed');
            mainContent.classList.remove('library-collapsed');
            toggleBtn.innerHTML = '\u2630';
        } else {
            libraryPanel.classList.add('collapsed');
            mainContent.classList.add('library-collapsed');
            toggleBtn.innerHTML = '\u2192';
        }
    } else {
        console.error("\u274c Could not find library panel elements");
    }
}

function initLibraryUI() {
    console.log("\ud83d\udd04 Initializing library UI");
    
    // Create toggle button for library panel
    const toggleBtn = document.createElement('button');
    toggleBtn.id = 'libraryToggle';
    toggleBtn.className = 'library-toggle';
    toggleBtn.innerHTML = '\u2630';
    toggleBtn.onclick = toggleLibraryPanel;
    document.body.appendChild(toggleBtn);
    console.log("\u2705 Created library toggle button");
    
    // Set up filter input handler
    const filterInput = document.getElementById('libraryFilter');
    if (filterInput) {
        filterInput.addEventListener('input', window.libraryUIRendering?.filterLibraryList);
        console.log("\u2705 Set up filter input handler");
    } else {
        console.warn("\u26a0\ufe0f Library filter input not found");
    }
    
    // Set up add button handler
    const addBtn = document.getElementById('addLibraryFile');
    if (addBtn) {
        addBtn.addEventListener('click', window.libraryFileOps?.createNewFile);
        console.log("\u2705 Set up add button handler");
    } else {
        console.warn("\u26a0\ufe0f Add library file button not found");
    }
    
    // Handle name field changes
    const nameInput = document.getElementById('modelName');
    if (nameInput) {
        nameInput.addEventListener('blur', window.libraryFileOps?.handleNameChange);
        console.log("\u2705 Set up name input handler");
    } else {
        console.warn("\u26a0\ufe0f Model name input not found");
    }
    
    console.log("\u2705 Library UI initialized");
}

// Export to global namespace
window.libraryUIControls = {
    isLibraryVisible,
    toggleLibraryPanel,
    initLibraryUI,
    
    // Setter for state
    setLibraryVisible: (visible) => { 
        console.log("\ud83d\udc41\ufe0f Setting library visibility:", visible);
        isLibraryVisible = visible; 
    }
};

console.log("\ud83d\udd27 Library UI controls module loaded");
