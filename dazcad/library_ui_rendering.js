// Library UI rendering - list rendering and item creation
let currentFile = { name: 'example', type: 'builtin' };
let libraryFiles = { builtin: [], user: [] };

function renderLibraryList() {
    console.log("\ud83d\udd04 Starting renderLibraryList()");
    console.log("\ud83d\udcda Current library files:", libraryFiles);
    
    const filterValue = document.getElementById('libraryFilter')?.value.toLowerCase() || '';
    const listContainer = document.getElementById('libraryList');
    
    console.log("\ud83d\udd0d Filter value:", filterValue);
    console.log("\ud83d\udce6 List container:", listContainer);
    
    if (!listContainer) {
        console.error("\u274c Library list container not found!");
        return;
    }
    
    listContainer.innerHTML = '';
    
    // Check if libraryFiles is properly initialized
    if (!libraryFiles || typeof libraryFiles !== 'object') {
        console.error('\u274c Library files not properly initialized');
        libraryFiles = { builtin: [], user: [] };
    }
    
    // Ensure arrays exist
    if (!Array.isArray(libraryFiles.builtin)) {
        console.warn('\u26a0\ufe0f Builtin files is not an array, fixing...');
        libraryFiles.builtin = [];
    }
    if (!Array.isArray(libraryFiles.user)) {
        console.warn('\u26a0\ufe0f User files is not an array, fixing...');
        libraryFiles.user = [];
    }
    
    console.log(`\ud83d\udccb Builtin files: ${libraryFiles.builtin.length} items`);
    console.log(`\ud83d\udccb User files: ${libraryFiles.user.length} items`);
    
    // Render builtin files
    if (libraryFiles.builtin.length > 0) {
        console.log("\ud83c\udfa8 Rendering builtin files section");
        const builtinHeader = document.createElement('div');
        builtinHeader.className = 'library-section-header';
        builtinHeader.textContent = 'Examples';
        listContainer.appendChild(builtinHeader);
        
        let builtinRendered = 0;
        libraryFiles.builtin.forEach((file, index) => {
            const fileName = typeof file === 'string' ? file : file.name || `file_${index}`;
            console.log(`\ud83d\udcc4 Processing builtin file ${index}: ${fileName}`);
            
            if (!filterValue || fileName.toLowerCase().includes(filterValue)) {
                const item = createLibraryItem({ name: fileName }, 'builtin');
                listContainer.appendChild(item);
                builtinRendered++;
            }
        });
        console.log(`\u2705 Rendered ${builtinRendered} builtin files`);
    } else {
        console.log("\ud83d\udced No builtin files to render");
    }
    
    // Render user files
    if (libraryFiles.user.length > 0) {
        console.log("\ud83c\udfa8 Rendering user files section");
        const userHeader = document.createElement('div');
        userHeader.className = 'library-section-header';
        userHeader.textContent = 'My Library';
        listContainer.appendChild(userHeader);
        
        let userRendered = 0;
        libraryFiles.user.forEach((file, index) => {
            const fileName = typeof file === 'string' ? file : file.name || `file_${index}`;
            console.log(`\ud83d\udcc4 Processing user file ${index}: ${fileName}`);
            
            if (!filterValue || fileName.toLowerCase().includes(filterValue)) {
                const item = createLibraryItem({ name: fileName }, 'user');
                listContainer.appendChild(item);
                userRendered++;
            }
        });
        console.log(`\u2705 Rendered ${userRendered} user files`);
    } else {
        console.log("\ud83d\udced No user files to render");
    }
    
    // If no files found, show a message
    if (libraryFiles.builtin.length === 0 && libraryFiles.user.length === 0) {
        console.log("\ud83d\udced No files found, showing empty message");
        const emptyMessage = document.createElement('div');
        emptyMessage.className = 'library-empty-message';
        emptyMessage.style.padding = '20px';
        emptyMessage.style.textAlign = 'center';
        emptyMessage.style.color = '#888';
        emptyMessage.textContent = 'No library files found. Please check server connection.';
        listContainer.appendChild(emptyMessage);
    }
    
    console.log("\u2705 renderLibraryList() completed");
}

function createLibraryItem(file, type) {
    console.log(`\ud83d\udd27 Creating library item: ${file.name} (${type})`);
    
    const item = document.createElement('div');
    item.className = 'library-item';
    if (currentFile.name === file.name && currentFile.type === type) {
        item.classList.add('active');
        console.log(`\ud83c\udfaf Marked ${file.name} as active`);
    }
    
    const nameSpan = document.createElement('span');
    nameSpan.textContent = file.name;
    nameSpan.onclick = () => {
        console.log(`\ud83d\uddb1\ufe0f Clicked on library item: ${file.name} (${type})`);
        window.libraryFileOps.loadFile(file.name, type);
    };
    
    item.appendChild(nameSpan);
    
    console.log(`\u2705 Created library item for: ${file.name}`);
    return item;
}

function filterLibraryList() {
    console.log("\ud83d\udd0d Filter triggered, re-rendering library list");
    renderLibraryList();
}

// Export to global namespace
window.libraryUIRendering = {
    currentFile,
    libraryFiles,
    renderLibraryList,
    createLibraryItem,
    filterLibraryList,
    
    // Setters for state
    setCurrentFile: (file) => { 
        console.log("\ud83d\udcdd Setting current file:", file);
        currentFile = file; 
    },
    setLibraryFiles: (files) => { 
        console.log("\ud83d\udcda Setting library files:", files);
        if (files && typeof files === 'object') {
            libraryFiles = files;
            // Ensure arrays exist
            if (!Array.isArray(libraryFiles.builtin)) {
                console.warn("\u26a0\ufe0f Converting builtin to array");
                libraryFiles.builtin = [];
            }
            if (!Array.isArray(libraryFiles.user)) {
                console.warn("\u26a0\ufe0f Converting user to array");
                libraryFiles.user = [];
            }
            console.log("\u2705 Library files set successfully");
        } else {
            console.error("\u274c Invalid files object provided to setLibraryFiles");
        }
    }
};

console.log("\ud83c\udfa8 Library UI rendering module loaded");
