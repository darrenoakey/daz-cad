// Library file loading operations - loading and parsing library files

async function loadLibraryFiles(autoLoadFirst = true) {
    console.log("🔄 Starting loadLibraryFiles()");
    const outputDiv = document.getElementById('output');
    
    try {
        console.log("📡 Making request to /library/list");
        const response = await fetch('/library/list');
        console.log("📨 Response received:", response);
        console.log("📊 Response status:", response.status);
        console.log("📋 Response headers:", [...response.headers.entries()]);
        
        if (!response.ok) {
            throw new Error(`Server returned ${response.status}: ${response.statusText}`);
        }
        
        console.log("🔍 Parsing JSON response...");
        const data = await response.json();
        console.log("📦 Raw response data:", data);
        console.log("📦 Data type:", typeof data);
        console.log("📦 Data keys:", Object.keys(data));
        
        if (data.success) {
            console.log("✅ Response marked as successful");
            console.log("📁 Files data:", data.files);
            console.log("📁 Files type:", typeof data.files);
            
            if (data.files) {
                console.log("📁 Files keys:", Object.keys(data.files));
                for (const [key, value] of Object.entries(data.files)) {
                    console.log(`📋 ${key}:`, value, `(length: ${Array.isArray(value) ? value.length : 'N/A'})`);
                }
            }
            
            // Handle both property name formats: built_in vs builtin
            let normalizedFiles = {};
            if (data.files) {
                // Support both built_in and builtin property names
                normalizedFiles.builtin = data.files.builtin || data.files.built_in || [];
                normalizedFiles.user = data.files.user || [];
                
                console.log("🔄 Normalized files:", normalizedFiles);
                console.log("📋 Builtin files:", normalizedFiles.builtin);
                console.log("📋 User files:", normalizedFiles.user);
            }
            
            console.log("🎨 Setting library files in UI...");
            window.libraryUI.setLibraryFiles(normalizedFiles);
            
            console.log("🖼️ Rendering library list...");
            window.libraryUI.renderLibraryList();
            
            // Only auto-load first file if explicitly requested (initial page load)
            if (autoLoadFirst && normalizedFiles.builtin && normalizedFiles.builtin.length > 0) {
                console.log(`📚 Found ${normalizedFiles.builtin.length} builtin files, loading first one...`);
                console.log("📄 Available builtin files:", normalizedFiles.builtin);
                
                // Load the first file, or 'example' if it exists
                const firstFile = normalizedFiles.builtin.includes('example.py') ? 'example.py' : normalizedFiles.builtin[0];
                console.log(`🎯 Loading file: ${firstFile}`);
                
                // Use the file operations module
                if (window.libraryFileOperations && window.libraryFileOperations.loadFile) {
                    await window.libraryFileOperations.loadFile(firstFile.replace('.py', ''), 'builtin');
                } else {
                    console.error("❌ Library file operations module not available");
                }
            } else if (autoLoadFirst) {
                console.warn('⚠️ No builtin library files found');
                console.log("📊 Builtin files array:", normalizedFiles.builtin);
                
                if (outputDiv) {
                    outputDiv.innerHTML = '<span class="warning-output">⚠️ No library files found. Please check the server installation.</span>';
                }
            } else {
                console.log("🔄 Auto-load skipped - just refreshing library list");
            }
        } else {
            console.error('❌ Server response marked as failed:', data.error);
            if (outputDiv) {
                outputDiv.innerHTML = `<span class="error-output">Failed to load library: ${data.error || 'Unknown error'}</span>`;
            }
            // Still render the UI to show the empty state
            window.libraryUI.renderLibraryList();
        }
    } catch (error) {
        console.error('❌ Exception in loadLibraryFiles:', error);
        console.error('📍 Error stack:', error.stack);
        
        if (outputDiv) {
            outputDiv.innerHTML = `<span class="error-output">Failed to connect to server: ${error.message}</span>`;
        }
        // Still render the UI to show the empty state
        window.libraryUI.renderLibraryList();
    }
    
    console.log("✅ loadLibraryFiles() completed");
}

// Legacy loadFile function for compatibility - delegates to new module
async function loadFile(name, type) {
    if (window.libraryFileOperations && window.libraryFileOperations.loadFile) {
        return await window.libraryFileOperations.loadFile(name, type);
    } else {
        console.error("❌ Library file operations module not available");
        throw new Error("Library file operations module not loaded");
    }
}

// Export to global namespace
window.libraryFileLoader = {
    loadLibraryFiles,
    loadFile  // Keep for backward compatibility
};

console.log("📚 Library file loader module loaded");
