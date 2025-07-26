let codeEditor;

function initCodeEditor() {
    codeEditor = CodeMirror(document.getElementById('codeEditor'), {
        mode: 'python',
        theme: 'monokai',
        lineNumbers: true,
        matchBrackets: true,
        autoCloseBrackets: true,
        styleActiveLine: true,
        indentUnit: 4,
        indentWithTabs: false,
        lineWrapping: true,
        foldGutter: true,
        gutters: ["CodeMirror-linenumbers", "CodeMirror-foldgutter"],
        extraKeys: {
            "Ctrl-Enter": runCode,
            "Tab": function(cm) {
                if (cm.somethingSelected()) {
                    cm.indentSelection("add");
                } else {
                    cm.replaceSelection(Array(cm.getOption("indentUnit") + 1).join(" "), "end", "+input");
                }
            }
        },
        value: `import cadquery as cq
asm = cq.Assembly()
b1 = cq.Workplane("XY").box(5, 5, 5)
asm.add(b1, name="Red", color=cq.Color("red"))
b2 = cq.Workplane("XY").box(5, 5, 5)
asm.add(b2, name="Green", loc=cq.Location((10, 0, 0)), color=cq.Color("green"))
show_object(asm, "Test")`
    });
}

async function runCode() {
    const code = codeEditor.getValue();
    const outputDiv = document.getElementById('output');
    const runButton = document.getElementById('runButton');
    runButton.disabled = true;
    runButton.textContent = 'Running...';
    try {
        const response = await fetch('/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code: code })
        });
        const result = await response.json();
        if (result.success) {
            clearScene();
            result.objects.forEach(obj => {
                loadSTL(obj.stl, obj.name, obj.color, obj.transform);
            });
            outputDiv.innerHTML = `<span class="success-output">Success!</span>\\n${result.output || ''}`;
        } else {
            outputDiv.innerHTML = `<span class="error-output">Error: ${result.error}</span>`;
        }
    } catch (error) {
        outputDiv.innerHTML = `<span class="error-output">Network error: ${error.message}</span>`;
    } finally {
        runButton.disabled = false;
        runButton.textContent = 'Run';
    }
}
