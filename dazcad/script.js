// Main application initialization
document.addEventListener('DOMContentLoaded', function() {
    initViewer();
    initCodeEditor();
    initChat();
    initLibrary();
    
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
        setupAutoSave();
    }, 500);
});

// Download model in specified format
async function downloadModel(format) {
    const nameInput = document.getElementById('modelName');
    const modelName = nameInput.value.trim() || 'example';
    
    // Validate the model name (remove invalid characters)
    const sanitizedName = modelName.replace(/[^a-zA-Z0-9_-]/g, '_');
    
    // Show download indicator - handle different button naming conventions
    let buttonId;
    if (format === '3mf') {
        buttonId = 'download3mfButton';
    } else {
        buttonId = `download${format.charAt(0).toUpperCase() + format.slice(1)}Button`;
    }
    
    const button = document.getElementById(buttonId);
    if (!button) {
        console.error(`Download button for format ${format} not found`);
        showDownloadError('Download button not found');
        return;
    }
    
    const originalText = button.textContent;
    button.textContent = 'Downloading...';
    button.disabled = true;
    
    try {
        // Create download URL
        const downloadUrl = `/download/${format}?name=${encodeURIComponent(sanitizedName)}`;
        
        // First, check if the download would succeed
        const response = await fetch(downloadUrl, { method: 'HEAD' });
        
        if (!response.ok) {
            // Get the error message
            const errorResponse = await fetch(downloadUrl);
            const errorData = await errorResponse.json();
            showDownloadError(errorData.error || 'Download failed');
            return;
        }
        
        // If successful, trigger the actual download
        const link = document.createElement('a');
        link.href = downloadUrl;
        link.download = `${sanitizedName}.${format}`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        // Show success message briefly
        button.textContent = '✓ Downloaded';
        setTimeout(() => {
            button.textContent = originalText;
        }, 1500);
        
    } catch (error) {
        console.error('Download error:', error);
        showDownloadError('Network error during download');
    } finally {
        // Reset button
        setTimeout(() => {
            button.textContent = originalText;
            button.disabled = false;
        }, 2000);
    }
}

// Show download error message to user
function showDownloadError(message) {
    const outputDiv = document.getElementById('output');
    if (outputDiv) {
        outputDiv.innerHTML = `<span class="error-output">Download Error: ${message}</span>`;
        
        // If no objects, suggest running code first
        if (message.includes('No objects to export')) {
            outputDiv.innerHTML += `<br><span class="info-output">💡 Tip: Run some CadQuery code first to generate 3D objects to download.</span>`;
        }
    }
}

// Check if 3MF format is supported by making a test request
async function check3MFSupport() {
    try {
        const response = await fetch('/download/3mf?name=test', { method: 'HEAD' });
        const threeMfButton = document.getElementById('download3mfButton');
        
        if (response.status === 400 && threeMfButton) {
            // 3MF not supported, hide the button
            threeMfButton.style.display = 'none';
            console.log('3MF format not supported in this CadQuery version');
        }
    } catch (error) {
        console.log('Could not check 3MF support:', error);
    }
}

// Check 3MF support after page loads (optional feature detection)
// Uncomment this line if you want automatic 3MF button hiding when not supported
// setTimeout(check3MFSupport, 2000);
