// Main application initialization
document.addEventListener('DOMContentLoaded', function() {
    console.log("🚀 DOMContentLoaded event fired, starting application initialization");
    
    console.log("🎨 Initializing viewer...");
    initViewer();
    
    console.log("📝 Initializing code editor...");
    initCodeEditor();
    
    console.log("💬 Initializing chat...");  
    initChat();
    
    console.log("📚 Initializing library...");
    initLibrary();
    
    console.log("🔗 Setting up event listeners...");
    document.getElementById('runButton').addEventListener('click', runCode);
    
    // Add download button event listeners for all supported formats
    document.getElementById('downloadStlButton').addEventListener('click', () => downloadModel('stl'));
    document.getElementById('downloadStepButton').addEventListener('click', () => downloadModel('step'));
    
    // Check if 3MF button exists before adding listener (may not be supported)
    const threeMfButton = document.getElementById('download3mfButton');
    if (threeMfButton) {
        threeMfButton.addEventListener('click', () => downloadModel('3mf'));
    }
    
    // Setup auto-save after editor is initialized
    setTimeout(() => {
        console.log("💾 Setting up auto-save...");
        setupAutoSave();
    }, 500);
    
    console.log("✅ Application initialization completed");
});

// Download model in specified format
async function downloadModel(format) {
    console.log(`📥 Starting download for format: ${format}`);
    const nameInput = document.getElementById('modelName');
    const modelName = nameInput.value.trim() || 'example';
    
    // Validate the model name (remove invalid characters)
    const sanitizedName = modelName.replace(/[^a-zA-Z0-9_-]/g, '_');
    console.log(`📝 Sanitized model name: ${sanitizedName}`);
    
    // Show download indicator - handle different button naming conventions
    let buttonId;
    if (format === '3mf') {
        buttonId = 'download3mfButton';
    } else {
        buttonId = `download${format.charAt(0).toUpperCase() + format.slice(1)}Button`;
    }
    
    const button = document.getElementById(buttonId);
    if (!button) {
        console.error(`❌ Download button for format ${format} not found`);
        showDownloadError('Download button not found');
        return;
    }
    
    const originalText = button.textContent;
    button.textContent = 'Downloading...';
    button.disabled = true;
    console.log(`🔘 Button state changed to downloading`);
    
    try {
        // Get the current code from the editor
        const currentCode = getCode();
        console.log(`📄 Current code length: ${currentCode ? currentCode.length : 'N/A'}`);
        
        // Create download URL
        const downloadUrl = `/download/${format}?name=${encodeURIComponent(sanitizedName)}`;
        console.log(`🌐 Download URL: ${downloadUrl}`);
        
        // First, send a POST request with the code to ensure objects are generated
        console.log("📡 Sending POST request to generate objects...");
        const postResponse = await fetch(downloadUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code: currentCode })
        });
        
        console.log("📨 POST response received:", postResponse.status);
        
        if (!postResponse.ok) {
            // Get the error message
            console.log("❌ POST response not OK, getting error data...");
            const errorData = await postResponse.json();
            console.log("📦 Error data:", errorData);
            showDownloadError(errorData.error || 'Download failed');
            
            // Reset button immediately on error
            button.textContent = originalText;
            button.disabled = false;
            return;
        }
        
        // If successful, get the file data
        console.log("✅ POST successful, getting blob data...");
        const blob = await postResponse.blob();
        console.log(`📦 Blob received, size: ${blob.size} bytes`);
        
        // Create download link
        console.log("🔗 Creating download link...");
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `${sanitizedName}.${format}`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(link.href);
        
        // Show success message briefly
        button.textContent = '✓ Downloaded';
        setTimeout(() => {
            button.textContent = originalText;
            button.disabled = false;
            console.log("🔘 Button state reset to original");
        }, 1500);
        
        console.log(`✅ Download completed for ${sanitizedName}.${format}`);
        
    } catch (error) {
        console.error('❌ Download error:', error);
        console.error('📍 Error stack:', error.stack);
        showDownloadError('Network error during download');
        
        // Reset button immediately on error
        button.textContent = originalText;
        button.disabled = false;
    }
}

// Show download error message to user
function showDownloadError(message) {
    console.log(`❌ Showing download error: ${message}`);
    const outputDiv = document.getElementById('output');
    if (outputDiv) {
        outputDiv.innerHTML = `<span class="error-output">Download Error: ${message}</span>`;
        
        // If no objects, suggest running code first with more specific instructions
        if (message.includes('No objects to export')) {
            outputDiv.innerHTML += `<br><span class="info-output">💡 Tip: Click the "Run" button to execute your CadQuery code and generate 3D objects before downloading.</span>`;
        }
    }
}

// Check if 3MF format is supported by making a test request
async function check3MFSupport() {
    console.log("🔍 Checking 3MF format support...");
    try {
        const response = await fetch('/download/3mf?name=test', { method: 'HEAD' });
        const threeMfButton = document.getElementById('download3mfButton');
        
        console.log(`📨 3MF check response: ${response.status}`);
        
        if (response.status === 400 && threeMfButton) {
            // 3MF not supported, hide the button
            threeMfButton.style.display = 'none';
            console.log('❌ 3MF format not supported in this CadQuery version');
        } else {
            console.log('✅ 3MF format appears to be supported');
        }
    } catch (error) {
        console.log('⚠️ Could not check 3MF support:', error);
    }
}

// Check 3MF support after page loads (optional feature detection)
// Uncomment this line if you want automatic 3MF button hiding when not supported
// setTimeout(check3MFSupport, 2000);

console.log("📄 Main script loaded");
