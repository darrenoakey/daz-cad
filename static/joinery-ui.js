/** Cut/Join panel controller. Keeps code generation separate from source execution. */
export class JoineryUI {
    constructor(editor, methods = []) {
        this.editor = editor;
        this.methods = methods;
        this.panel = document.getElementById('joinery-panel');
        this.diagnostics = document.getElementById('joinery-diagnostics');
        this.preview = document.getElementById('joinery-preview');
        this.method = document.getElementById('joinery-method');
        this._positionedDefault = false;
        this._bind();
        this._populateMethods();
    }

    _bind() {
        document.getElementById('cut-join-btn')?.addEventListener('click', () => this.toggle());
        document.getElementById('joinery-close')?.addEventListener('click', () => this.hide());
        document.querySelectorAll('[data-joinery-axis]').forEach((button) => button.addEventListener('click', () => {
            this._setAxis(button.dataset.joineryAxis);
            document.querySelectorAll('[data-joinery-axis]').forEach((item) => item.classList.toggle('active', item === button));
        }));
        this.panel?.querySelectorAll('input, select').forEach((input) => input.addEventListener('input', () => this._syncPlane()));
        document.getElementById('joinery-apply')?.addEventListener('click', () => this.apply());
    }

    _populateMethods() {
        if (!this.method) return;
        this.method.replaceChildren(...this.methods.map(({ id, label, description }) => {
            const option = document.createElement('option');
            option.value = id;
            option.textContent = `${label} — ${description}`;
            return option;
        }));
    }

    toggle() { this.panel.hidden ? this.show() : this.hide(); }
    show() {
        this.panel.hidden = false;
        if (!this._restoreSettings() && !this._positionedDefault) this._placeAtModelMidpoint();
        this._syncPlane();
    }
    hide() { this.panel.hidden = true; this.editor.viewer?.clearCutPlane(); }

    _number(name, fallback) {
        const value = Number(document.getElementById(`joinery-${name}`)?.value);
        return Number.isFinite(value) ? value : fallback;
    }

    _plane() {
        return {
            origin: ['x', 'y', 'z'].map((axis) => this._number(axis, 0)),
            normal: ['nx', 'ny', 'nz'].map((axis) => this._number(axis, axis === 'nz' ? 1 : 0)),
            up: ['ux', 'uy', 'uz'].map((axis) => this._number(axis, axis === 'uy' ? 1 : 0)),
        };
    }

    _setAxis(axis) {
        const normal = { X: [1, 0, 0], Y: [0, 1, 0], Z: [0, 0, 1] }[axis];
        const up = axis === 'Z' ? [0, 1, 0] : [0, 0, 1];
        ['nx', 'ny', 'nz'].forEach((name, index) => { document.getElementById(`joinery-${name}`).value = normal[index]; });
        ['ux', 'uy', 'uz'].forEach((name, index) => { document.getElementById(`joinery-${name}`).value = up[index]; });
        this._syncPlane();
    }

    _placeAtModelMidpoint() {
        const bounds = this.editor.viewer?.getModelBounds();
        if (!bounds) return;
        ['x', 'y', 'z'].forEach((axis, index) => {
            document.getElementById(`joinery-${axis}`).value = ((bounds.min[index] + bounds.max[index]) / 2).toFixed(2);
        });
        this._positionedDefault = true;
    }

    _syncPlane() {
        if (!this.panel || this.panel.hidden) return;
        const plane = this._plane();
        if (Math.hypot(...plane.normal) < 0.001) {
            this._diagnose('Plane normal must have a non-zero length.', true);
            this.editor.viewer?.clearCutPlane();
            return;
        }
        const crossLength = Math.hypot(
            plane.normal[1] * plane.up[2] - plane.normal[2] * plane.up[1],
            plane.normal[2] * plane.up[0] - plane.normal[0] * plane.up[2],
            plane.normal[0] * plane.up[1] - plane.normal[1] * plane.up[0],
        );
        if (crossLength < 0.001) {
            this._diagnose('Plane up vector must not be parallel to its normal.', true);
            return;
        }
        this.editor.viewer?.setCutPlane(plane, (origin) => {
            ['x', 'y', 'z'].forEach((axis, index) => { document.getElementById(`joinery-${axis}`).value = origin[index].toFixed(2); });
            this._positionedDefault = true;
        });
        this._diagnose((this.preview?.value || 'assembled') === 'print'
            ? 'Print preview separates parts for manufacture. Confirm clearance and support before export.'
            : 'Plane preview: Shift-drag the cyan plane in the viewport or enter coordinates, then Apply.');
    }

    _options() {
        return { plane: this._plane(), method: this.method?.value, size: this._number('size', 8), depth: this._number('depth', 6), clearance: this._number('clearance', 0.2), count: Math.max(1, Math.round(this._number('count', 1))), wall: this._number('wall', 1.2) };
    }

    _diagnose(text, error = false) {
        if (!this.diagnostics) return;
        this.diagnostics.textContent = text;
        this.diagnostics.classList.toggle('error', error);
    }

    _restoreSettings() {
        const prefix = 'const __joinerySettings = ';
        const line = this.editor.editor.getValue().split('\n').find((entry) => entry.startsWith(prefix));
        if (!line) return false;
        try {
            const settings = JSON.parse(line.slice(prefix.length).replace(/;\s*$/, ''));
            const options = settings.options;
            for (const [field, vector] of [['', options.plane.origin], ['n', options.plane.normal], ['u', options.plane.up]]) {
                if (!Array.isArray(vector) || vector.length !== 3 || !vector.every(Number.isFinite)) return false;
                ['x', 'y', 'z'].forEach((axis, index) => {
                    document.getElementById(`joinery-${field}${axis}`).value = vector[index];
                });
            }
            for (const name of ['size', 'depth', 'clearance', 'count', 'wall']) {
                document.getElementById(`joinery-${name}`).value = options[name];
            }
            this.method.value = options.method;
            this.preview.value = settings.mode;
            this._positionedDefault = true;
            return true;
        } catch (_) {
            this._diagnose('The saved joinery settings could not be read; review the plane and dimensions before applying.', true);
            return false;
        }
    }

    _sourceForJoinery(source) {
        const start = source.indexOf('// BEGIN DAZ-CAD CUT/JOIN SOURCE');
        const end = source.indexOf('// END DAZ-CAD CUT/JOIN SOURCE');
        return start < 0 || end <= start ? source : source.slice(start + '// BEGIN DAZ-CAD CUT/JOIN SOURCE'.length, end).trim();
    }

    _generatedCode(source, options, mode) {
        // Markers only unwrap a complete earlier generated block. The user source
        // stays lexical inside an IIFE: no variable-name regex replacement occurs.
        return `// Cut/Join generated from the model below.\nconst __joinerySettings = ${JSON.stringify({options, mode})};\nconst __joinerySource = (() => {\n// BEGIN DAZ-CAD CUT/JOIN SOURCE\n${source}\n// END DAZ-CAD CUT/JOIN SOURCE\n    return typeof result !== 'undefined' ? result : null;\n})();\nif (!__joinerySource || __joinerySource.isAssembly) throw new Error('Cut/Join requires one Workplane result, not an Assembly.');\nconst __joineryResult = __joinerySource.splitAndJoin(__joinerySettings.options);\nconst result = __joineryResult.toAssembly({ mode: __joinerySettings.mode, gap: 20 });\nconsole.log(__joineryResult.instructions.join('\\n'));\nif (__joineryResult.warnings.length) console.warn(__joineryResult.warnings.join('\\n'));\nresult;\n`;
    }

    async apply() {
        const button = document.getElementById('joinery-apply');
        if (button?.disabled) return;
        if (button) button.disabled = true;
        try {
            const options = this._options();
            if (Math.hypot(...options.plane.normal) < 0.001) return this._diagnose('Plane normal must have a non-zero length.', true);
            const upCross = [
                options.plane.normal[1] * options.plane.up[2] - options.plane.normal[2] * options.plane.up[1],
                options.plane.normal[2] * options.plane.up[0] - options.plane.normal[0] * options.plane.up[2],
                options.plane.normal[0] * options.plane.up[1] - options.plane.normal[1] * options.plane.up[0],
            ];
            if (Math.hypot(...upCross) < 0.001) return this._diagnose('Plane up vector must not be parallel to its normal.', true);
            const editorSource = this.editor.editor.getValue();
            const source = this._sourceForJoinery(editorSource);
            this._diagnose('Checking the current model before generating Cut/Join code…');
            const validation = await this.editor.validateJoinerySource(source);
            if (this.editor.editor.getValue() !== editorSource) return this._diagnose('The editor changed during validation; Cut/Join was not applied.', true);
            if (!validation.ok) return this._diagnose(validation.error, true);
            const code = this._generatedCode(source, options, this.preview?.value || 'assembled');
            this._diagnose('Checking the generated joinery before changing your editor…');
            const generated = await this.editor.validateJoinerySource(code, true);
            if (this.editor.editor.getValue() !== editorSource) return this._diagnose('The editor changed during validation; Cut/Join was not applied.', true);
            if (!generated.ok) return this._diagnose(`${generated.error} Your source remains unchanged.`, true);
            this.editor.editor.setValue(code);
            this._diagnose(`Generated ${this.method.selectedOptions[0]?.textContent.split(' — ')[0]} assembly. Use STL for selected preview or 3MF for all parts.`);
            this.hide();
            // setValue already schedules the normal editor render; a second
            // explicit render duplicated expensive geometry and export state.
        } catch (error) {
            this._diagnose(`Cut/Join was not applied: ${error.message}. Your source remains unchanged.`, true);
        } finally {
            if (button) button.disabled = false;
        }
    }
}
