// Main application initialization
document.addEventListener('DOMContentLoaded', function() {
    initViewer();
    initCodeEditor();
    initChat();
    document.getElementById('runButton').addEventListener('click', runCode);
    
    // Auto-run the code when the page first loads
    setTimeout(() => {
        runCode();
    }, 1000); // Wait 1 second for everything to be initialized
});
