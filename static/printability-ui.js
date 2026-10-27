/** One-click FDM finishing panel. Source generation is separate from geometry execution. */
export class PrintabilityUI {
    constructor(editor) {
        this.editor = editor;
        this.panel = document.getElementById('printability-panel');
        this.diagnostics = document.getElementById('printability-diagnostics');
        document.getElementById('printability-btn')?.addEventListener('click', () => this.toggle());
        document.getElementById('printability-close')?.addEventListener('click', () => this.hide());
        document.getElementById('printability-apply')?.addEventListener('click', () => this.apply());
    }

    toggle() { this.panel.hidden ? this.show() : this.hide(); }
    show() { this.panel.hidden = false; this._restoreSettings(); }
    hide() { this.panel.hidden = true; }

    _diagnose(text, error = false) {
        this.diagnostics.textContent = text;
        this.diagnostics.classList.toggle('error', error);
    }

    _options() {
        return {
            verticalFillet: Number(document.getElementById('printability-fillet').value),
            baseChamfer: Number(document.getElementById('printability-chamfer').value),
            preserveEdges: document.getElementById('printability-preserve').value
                .split(',').map((value) => value.trim()).filter(Boolean),
        };
    }

    _restoreSettings() {
        const prefix = 'const __printabilitySettings = ';
        const line = this.editor.editor.getValue().split('\n').find((entry) => entry.startsWith(prefix));
        if (!line) return;
        try {
            const options = JSON.parse(line.slice(prefix.length).replace(/;\s*$/, ''));
            document.getElementById('printability-fillet').value = options.verticalFillet;
            document.getElementById('printability-chamfer').value = options.baseChamfer;
            document.getElementById('printability-preserve').value = options.preserveEdges.join(', ');
        } catch (_) {
            this._diagnose('Saved printability settings could not be read; review them before applying.', true);
        }
    }

    _source(source) {
        const marker = '// BEGIN DAZ-CAD PRINTABILITY SOURCE';
        const endMarker = '// END DAZ-CAD PRINTABILITY SOURCE';
        const start = source.indexOf(marker);
        const end = source.indexOf(endMarker);
        return start < 0 || end <= start ? source : source.slice(start + marker.length, end).trim();
    }

    _generatedCode(source, options) {
        return `// Printability generated from the editable model below.\nconst __printabilitySettings = ${JSON.stringify(options)};\nconst __printabilitySource = (() => {\n// BEGIN DAZ-CAD PRINTABILITY SOURCE\n${source}\n// END DAZ-CAD PRINTABILITY SOURCE\n    return typeof result !== 'undefined' ? result : null;\n})();\nif (!__printabilitySource || __printabilitySource.isAssembly) throw new Error('Printability requires one Workplane result, not an Assembly.');\n// Chamfer bed-contact edges to relieve first-layer flare; fillet vertical edges except mating selectors.\nconst result = __printabilitySource.optimizeForPrinting(__printabilitySettings);\nfor (const change of result.printReport.changes) console.log(\`Printability: \${change.rule}, \${change.edges} edges, \${change.millimetres} mm\`);\nfor (const warning of result.printReport.warnings) console.warn(\`Printability: \${warning}\`);\nresult;\n`;
    }

    async apply() {
        const button = document.getElementById('printability-apply');
        if (button.disabled) return;
        button.disabled = true;
        try {
            const options = this._options();
            if (options.verticalFillet <= 0 && options.baseChamfer <= 0) {
                return this._diagnose('Enable a fillet or chamfer greater than zero.', true);
            }
            const editorSource = this.editor.editor.getValue();
            const source = this._source(editorSource);
            this._diagnose('Checking the current model before generating printability code…');
            const original = await this.editor.validateJoinerySource(source);
            if (this.editor.editor.getValue() !== editorSource) return this._diagnose('The editor changed; nothing was applied.', true);
            if (!original.ok) return this._diagnose(original.error.replace('Cut/Join', 'Printability'), true);
            const code = this._generatedCode(source, options);
            this._diagnose('Checking the optimized solid before changing your editor…');
            const generated = await this.editor.validateJoinerySource(code);
            if (this.editor.editor.getValue() !== editorSource) return this._diagnose('The editor changed; nothing was applied.', true);
            if (!generated.ok) return this._diagnose(`${generated.error.replace('Cut/Join', 'Printability')} Your source remains unchanged.`, true);
            this.editor.editor.setValue(code);
            this._diagnose('Applied deterministic FDM rules. Review the console report and slicer preview.');
            this.hide();
        } catch (error) {
            this._diagnose(`Printability was not applied: ${error.message}. Your source remains unchanged.`, true);
        } finally {
            button.disabled = false;
        }
    }
}
