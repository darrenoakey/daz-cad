// Individual file loading operations

async function loadFile(name, type) {
    console.log(`🔄 Starting loadFile(${name}, ${type})`);
    const outputDiv = document.getElementById('output');
    
    // Show loading indicator with spinner - make it more prominent
    if (outputDiv) {
        outputDiv.innerHTML = '<div class="loading-output" style="font-size: 1.2em; color: #007acc;">⏳ Loading file... Please wait</div>';
    }
    
    // Also add visual feedback to the library list
    const libraryItems = document.querySelectorAll('.library-item');
    libraryItems.forEach(item => {
        if (item.textContent.includes(name)) {
            item.style.opacity = '0.5';
            item.style.cursor = 'wait';
        }
    });
    
    try {
        const url = `/library/get/${type}/${encodeURIComponent(name)}`;
        console.log(`📡 Making request to: ${url}`);
        
        const response = await fetch(url);
        console.log("📨 Load file response received:", response);
        console.log("📊 Response status:", response.status);
        
        if (!response.ok) {
            throw new Error(`Server returned ${response.status}: ${response.statusText}`);
        }
        
        console.log("🔍 Parsing JSON response...");
        const data = await response.json();
        console.log("📦 Load file response data:", data);
        console.log("📦 Data success:", data.success);
        
        if (data.success) {
            console.log(`✅ File ${name} loaded successfully`);
            console.log("📄 Content length:", data.content ? data.content.length : 'N/A');
            
            window.libraryUI.setCurrentFile({ name, type });
            
            if (window.codeEditor) {
                console.log("📝 Setting code editor content...");
                window.codeEditor.setValue(data.content);
                window.autoSave.setLastSavedContent(data.content);
                // Also save the current file name
                window.autoSave.setLastSavedName(name);
            } else {
                console.warn("⚠️ Code editor not available");
            }
            
            const nameInput = document.getElementById('modelName');
            if (nameInput) {
                nameInput.value = name;
                console.log("📝 Set model name input to:", name);
            }
            
            console.log("🖼️ Re-rendering library list...");
            window.libraryUI.renderLibraryList();
            
            // Keep the loading message a bit longer for better UX
            if (outputDiv) {
                outputDiv.innerHTML = '<div class="info-output">📄 File loaded. Running code...</div>';
            }
            
            // Small delay before running to ensure user sees the loading message
            await new Promise(resolve => setTimeout(resolve, 300));
            
            console.log("🏃 Auto-running code...");
            if (window.libraryCodeExecutor && window.libraryCodeExecutor.autoRunCode) {
                await window.libraryCodeExecutor.autoRunCode();
            }
        } else {
            console.error('❌ Failed to load file:', data.error);
            if (outputDiv) {
                outputDiv.innerHTML = `<span class="error-output">Failed to load file: ${data.error || 'Unknown error'}</span>`;
            }
        }
    } catch (error) {
        console.error('❌ Error loading file:', error);
        console.error('📍 Error stack:', error.stack);
        
        if (outputDiv) {
            outputDiv.innerHTML = `<span class="error-output">Failed to load file: ${error.message}</span>`;
        }
    } finally {
        // Restore library items visual state
        libraryItems.forEach(item => {
            item.style.opacity = '1';
            item.style.cursor = 'pointer';
        });
        
        console.log(`✅ loadFile(${name}, ${type}) completed`);
    }
}

// Export to global namespace
window.libraryFileOperations = {
    loadFile
};

console.log("📄 Library file operations module loaded");
