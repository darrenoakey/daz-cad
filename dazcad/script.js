// Main application initialization
document.addEventListener('DOMContentLoaded', function() {
    initViewer();
    initCodeEditor();
    initChat();
    document.getElementById('runButton').addEventListener('click', runCode);
    
    // Add download button event listeners
    document.getElementById('downloadStlButton').addEventListener('click', () => downloadModel('stl'));
    document.getElementById('downloadStepButton').addEventListener('click', () => downloadModel('step'));
    
    // Auto-run the code when the page first loads
    setTimeout(() => {
        runCode();
    }, 1000); // Wait 1 second for everything to be initialized
});

// Download model in specified format
function downloadModel(format) {
    const nameInput = document.getElementById('modelName');
    const modelName = nameInput.value.trim() || 'example';
    
    // Validate the model name (remove invalid characters)
    const sanitizedName = modelName.replace(/[^a-zA-Z0-9_-]/g, '_');
    
    // Show download indicator
    const button = document.getElementById(`download${format.charAt(0).toUpperCase() + format.slice(1)}Button`);
    const originalText = button.textContent;
    button.textContent = 'Downloading...';
    button.disabled = true;
    
    // Create download URL
    const downloadUrl = `/download/${format}?name=${encodeURIComponent(sanitizedName)}`;
    
    // Create hidden download link and trigger download
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = `${sanitizedName}.${format}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    // Reset button after a short delay
    setTimeout(() => {
        button.textContent = originalText;
        button.disabled = false;
    }, 2000);
}
