import { getGenerator, listGenerators, registerGenerator, subscribeToGeneratorRegistry } from './generator-registry.js';

export { listGenerators, registerGenerator };

/** Generator menu controller; generated source stays editable in Monaco. */
export class GeneratorUI {
    constructor(editor) {
        this.editor = editor;
        this.panel = document.getElementById('generator-panel');
        this.summary = document.getElementById('generator-summary');
        this.createButton = document.getElementById('generator-create');
        this.kind = document.getElementById('generator-kind');
        this.activeGenerator = null;
        this._unsubscribeRegistry = subscribeToGeneratorRegistry(() => this._populateKinds());
        this._populateKinds();
        this._bind();
    }

    _bind() {
        document.getElementById('generator-btn')?.addEventListener('click', () => this.toggle());
        document.getElementById('generator-close')?.addEventListener('click', () => this.hide());
        this.panel?.querySelectorAll('input').forEach((input) => input.addEventListener('input', () => this._updateSummary()));
        this.kind?.addEventListener('change', () => this._selectGenerator(this.kind.value));
        this.createButton?.addEventListener('click', () => this.generate());
        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape' && this.panel && !this.panel.hidden) this.hide();
        });
    }

    _populateKinds() {
        if (!this.kind) return;
        const selected = this.kind.value;
        const options = listGenerators().map(({ id, label }) => {
            const option = document.createElement('option');
            option.value = id;
            option.textContent = label;
            return option;
        });
        this.kind.replaceChildren(...options);
        const next = listGenerators().some(({ id }) => id === selected) ? selected : (options[0]?.value || '');
        this.kind.value = next;
        this._selectGenerator(next);
    }

    _selectGenerator(id) {
        const definition = getGenerator(id);
        const fields = definition && this.panel?.querySelector(`[data-generator-fields="${definition.fieldsId}"]`);
        this.activeGenerator = fields ? definition : null;
        this.panel?.querySelectorAll('[data-generator-fields]').forEach((group) => {
            group.hidden = group.dataset.generatorFields !== id;
        });
        if (!this.activeGenerator) {
            this.createButton.disabled = true;
            this.summary.textContent = definition ? `Generator form not found: ${definition.fieldsId}` : 'No generator is registered.';
            this.summary.classList.add('error');
            return;
        }
        this.createButton.disabled = false;
        this._updateSummary();
    }

    toggle() { this.panel.hidden ? this.show() : this.hide(); }

    show() {
        this.panel.hidden = false;
        document.getElementById('generator-btn')?.setAttribute('aria-expanded', 'true');
        this._updateSummary();
    }

    hide() {
        this.panel.hidden = true;
        document.getElementById('generator-btn')?.setAttribute('aria-expanded', 'false');
    }

    _options() {
        if (!this.activeGenerator) throw new Error('Choose a registered generator first');
        const fields = this.panel.querySelector(`[data-generator-fields="${this.activeGenerator.fieldsId}"]`);
        return this.activeGenerator.readOptions(fields);
    }

    _updateSummary() {
        if (!this.summary || !this.activeGenerator) return;
        try {
            this.summary.textContent = this.activeGenerator.summarize(this._options());
            this.summary.classList.remove('error');
        } catch (error) {
            this.summary.textContent = error.message;
            this.summary.classList.add('error');
        }
    }

    async generate() {
        if (!this.editor.editor || !this.activeGenerator || this.createButton?.disabled) return;
        this.createButton.disabled = true;
        try {
            const result = this.activeGenerator.generate(this._options());
            if (!result || typeof result.source !== 'string' || typeof result.summary !== 'string') {
                throw new Error(`Generator ${this.activeGenerator.id} did not return source and summary text`);
            }
            this.editor.editor.setValue(result.source);
            this.summary.textContent = result.summary;
            this.summary.classList.remove('error');
        } catch (error) {
            this.summary.textContent = error.message;
            this.summary.classList.add('error');
        } finally {
            this.createButton.disabled = !this.activeGenerator;
        }
    }
}
