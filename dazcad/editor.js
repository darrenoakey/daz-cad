// Code editor functionality using CodeMirror

// Global code editor instance
let codeEditor = null;

// Initialize the code editor
function initCodeEditor() {
    const editorElement = document.getElementById('codeEditor');
    if (!editorElement) {
        console.error('Code editor container not found');
        return;
    }

    // Initialize CodeMirror editor
    codeEditor = CodeMirror(editorElement, {
        mode: 'python',
        theme: 'monokai',
        lineNumbers: true,
        matchBrackets: true,
        autoCloseBrackets: true,
        styleActiveLine: true,
        indentUnit: 4,
        indentWithTabs: false,
        lineWrapping: true,
        value: `import cadquery as cq

# Create an assembly for 3D printing - positioned to sit on build plate (z=0)
asm = cq.Assembly()

# Create boxes that sit on the build plate
b1 = cq.Workplane("XY").workplane(offset=2.5).box(5, 5, 5)
asm.add(b1, name="Red", color=cq.Color("red"))

b2 = cq.Workplane("XY").workplane(offset=2.5).box(5, 5, 5) 
asm.add(b2, name="Green", loc=cq.Location((10, 0, 0)), color=cq.Color("green"))

show_object(asm, "Test")`
    });

    // Make editor globally accessible
    window.codeEditor = codeEditor;
    
    console.log('Code editor initialized successfully');
}

// Get current code from editor
function getCode() {
    if (codeEditor) {
        return codeEditor.getValue();
    }
    return '';
}

// Set code in editor
function setCode(code) {
    if (codeEditor) {
        codeEditor.setValue(code);
    }
}

// Run the code in the editor
async function runCode() {
    if (!codeEditor) {
        console.error('Code editor not initialized');
        return;
    }

    const code = codeEditor.getValue();
    const outputDiv = document.getElementById('output');
    
    if (outputDiv) {
        outputDiv.innerHTML = '<span class="info-output">Running code...</span>';
    }

    try {
        const response = await fetch('/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code: code })
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Clear existing 3D objects
            if (window.clearScene) {
                window.clearScene();
            }
            
            // Load new 3D objects
            if (result.objects) {
                result.objects.forEach(obj => {
                    if (window.loadSTL) {
                        window.loadSTL(obj.stl, obj.name, obj.color, obj.transform);
                    }
                });
            }
            
            // Display success message
            if (outputDiv) {
                outputDiv.innerHTML = `<span class="success-output">Code executed successfully!</span>\n${result.output || ''}`;
            }
        } else {
            // Display error message
            let errorMessage = `<span class="error-output">Error: ${result.error}</span>`;
            if (result.traceback) {
                errorMessage += `\n\n<span class="traceback-output">Stack trace:\n${result.traceback}</span>`;
            }
            if (outputDiv) {
                outputDiv.innerHTML = errorMessage;
            }
        }
    } catch (error) {
        console.error('Network error:', error);
        if (outputDiv) {
            outputDiv.innerHTML = `<span class="error-output">Network error: ${error.message}</span>`;
        }
    }
}

// Export functions for global access
window.initCodeEditor = initCodeEditor;
window.getCode = getCode;
window.setCode = setCode;
window.runCode = runCode;
