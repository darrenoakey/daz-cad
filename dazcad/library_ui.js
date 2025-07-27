// Library UI management - DOM manipulation and rendering
let currentFile = { name: 'example', type: 'builtin' };
let libraryFiles = { builtin: [], user: [] };
let isLibraryVisible = true;

function renderLibraryList() {
    const filterValue = document.getElementById('libraryFilter')?.value.toLowerCase() || '';
    const listContainer = document.getElementById('libraryList');
    
    if (!listContainer) return;
    
    listContainer.innerHTML = '';
    
    // Render builtin files
    if (libraryFiles.builtin.length > 0) {
        const builtinHeader = document.createElement('div');
        builtinHeader.className = 'library-section-header';
        builtinHeader.textContent = 'Examples';
        listContainer.appendChild(builtinHeader);
        
        libraryFiles.builtin.forEach(file => {
            if (!filterValue || file.name.toLowerCase().includes(filterValue)) {
                const item = createLibraryItem(file, 'builtin');
                listContainer.appendChild(item);
            }
        });
    }
    
    // Render user files
    if (libraryFiles.user.length > 0) {
        const userHeader = document.createElement('div');
        userHeader.className = 'library-section-header';
        userHeader.textContent = 'My Library';
        listContainer.appendChild(userHeader);
        
        libraryFiles.user.forEach(file => {
            if (!filterValue || file.name.toLowerCase().includes(filterValue)) {
                const item = createLibraryItem(file, 'user');
                listContainer.appendChild(item);
            }
        });
    }
}

function createLibraryItem(file, type) {
    const item = document.createElement('div');
    item.className = 'library-item';
    if (currentFile.name === file.name && currentFile.type === type) {
        item.classList.add('active');
    }
    
    const nameSpan = document.createElement('span');
    nameSpan.textContent = file.name;
    nameSpan.onclick = () => window.libraryFileOps.loadFile(file.name, type);
    
    item.appendChild(nameSpan);
    
    return item;
}

function filterLibraryList() {
    renderLibraryList();
}

function toggleLibraryPanel() {
    const libraryPanel = document.querySelector('.library-panel');
    const mainContent = document.querySelector('.main-content');
    const toggleBtn = document.getElementById('libraryToggle');
    
    if (libraryPanel && mainContent && toggleBtn) {
        isLibraryVisible = !isLibraryVisible;
        
        if (isLibraryVisible) {
            libraryPanel.classList.remove('collapsed');
            mainContent.classList.remove('library-collapsed');
            toggleBtn.innerHTML = '☰';
        } else {
            libraryPanel.classList.add('collapsed');
            mainContent.classList.add('library-collapsed');
            toggleBtn.innerHTML = '→';
        }
    }
}

function initLibraryUI() {
    // Create toggle button for library panel
    const toggleBtn = document.createElement('button');
    toggleBtn.id = 'libraryToggle';
    toggleBtn.className = 'library-toggle';
    toggleBtn.innerHTML = '☰';
    toggleBtn.onclick = toggleLibraryPanel;
    document.body.appendChild(toggleBtn);
    
    // Set up filter input handler
    const filterInput = document.getElementById('libraryFilter');
    if (filterInput) {
        filterInput.addEventListener('input', filterLibraryList);
    }
    
    // Set up add button handler
    const addBtn = document.getElementById('addLibraryFile');
    if (addBtn) {
        addBtn.addEventListener('click', window.libraryFileOps.createNewFile);
    }
    
    // Handle name field changes
    const nameInput = document.getElementById('modelName');
    if (nameInput) {
        nameInput.addEventListener('blur', window.libraryFileOps.handleNameChange);
    }
}

// Export to global namespace
window.libraryUI = {
    currentFile,
    libraryFiles,
    isLibraryVisible,
    renderLibraryList,
    createLibraryItem,
    filterLibraryList,
    toggleLibraryPanel,
    initLibraryUI,
    
    // Setters for state
    setCurrentFile: (file) => { currentFile = file; },
    setLibraryFiles: (files) => { libraryFiles = files; },
    setLibraryVisible: (visible) => { isLibraryVisible = visible; }
};
