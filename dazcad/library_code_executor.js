// Library code execution operations - running CadQuery code and handling results

async function autoRunCode() {
    console.log("\ud83d\udd04 Starting autoRunCode()");
    const code = window.codeEditor.getValue();
    const outputDiv = document.getElementById('output');
    
    console.log("\ud83d\udcc4 Code length:", code ? code.length : 'N/A');
    
    try {
        console.log("\ud83d\udce1 Making request to /run");
        const response = await fetch('/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code: code })
        });
        
        console.log("\ud83d\udce8 Run code response received:", response);
        console.log("\ud83d\udcca Response status:", response.status);
        
        if (!response.ok) {
            throw new Error(`Server returned ${response.status}: ${response.statusText}`);
        }
        
        console.log("\ud83d\udd0d Parsing JSON response...");
        const result = await response.json();
        console.log("\ud83d\udce6 Run code result:", result);
        console.log("\ud83d\udce6 Result success:", result.success);
        
        if (result.success) {
            console.log(`\u2705 Code executed successfully`);
            console.log("\ud83d\udcca Objects count:", result.objects ? result.objects.length : 'N/A');
            
            if (window.clearScene) {
                console.log("\ud83e\uddf9 Clearing scene...");
                window.clearScene();
            }
            
            if (result.objects && result.objects.length > 0) {
                console.log("\ud83c\udfa8 Loading objects into scene...");
                result.objects.forEach((obj, index) => {
                    console.log(`\ud83d\udd37 Loading object ${index + 1}:`, obj.name, obj.color);
                    if (window.loadSTL) {
                        window.loadSTL(obj.stl, obj.name, obj.color, obj.transform);
                    }
                });
            }
            
            let outputContent = '<span class="success-output">\u2713 Code executed successfully!</span>';
            if (result.output && result.output.trim()) {
                outputContent += '\\n' + result.output;
            }
            outputDiv.innerHTML = outputContent;
        } else {
            console.error('\u274c Code execution failed:', result.error);
            let errorMessage = `<span class="error-output">Auto-run Error: ${result.error}</span>`;
            if (result.traceback) {
                errorMessage += `\\n\\n<span class="traceback-output">Stack trace:\\n${result.traceback}</span>`;
            }
            outputDiv.innerHTML = errorMessage;
        }
    } catch (error) {
        console.error('\u274c Error in autoRunCode:', error);
        console.error('\ud83d\udccd Error stack:', error.stack);
        outputDiv.innerHTML = `<span class="error-output">Auto-run Network error: ${error.message}</span>`;
    }
    
    console.log("\u2705 autoRunCode() completed");
}

// Export to global namespace
window.libraryCodeExecutor = {
    autoRunCode
};

console.log("\ud83d\udd0e Library code executor module loaded");
