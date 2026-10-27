import { Gridfinity } from './gridfinity.js';
import { registerGenerator } from './generator-registry.js';

registerGenerator({
    id: 'segmented-gridfinity',
    label: 'Segmented Gridfinity baseplate',
    fieldsId: 'segmented-gridfinity',
    readOptions(fields) {
        const number = (id) => Number(fields.querySelector(`#${id}`).value);
        return {
            x: number('generator-x'),
            y: number('generator-y'),
            buildArea: number('generator-bed-area'),
            mouseEars: fields.querySelector('#generator-mouse-ears').checked,
            snapConnectors: fields.querySelector('#generator-snap-connectors').checked,
            extraConnectors: number('generator-extra-connectors')
        };
    },
    summarize(options) {
        const plan = Gridfinity.planBaseplateSegments(options);
        const axes = `${plan.xSegments.join(' + ')} wide × ${plan.ySegments.join(' + ')} deep`;
        const connectorText = plan.totalConnectors > 0
            ? `${plan.totalConnectors} snap connectors (${plan.seamConnectors} for seams${plan.extraConnectors ? `, ${plan.extraConnectors} spare` : ''})`
            : 'no connectors needed';
        const pieces = plan.segments.length;
        return `${pieces} balanced segment${pieces === 1 ? '' : 's'} · ${axes} units per row · up to ${plan.maxSegmentMm} mm per side. ${connectorText}.`;
    },
    generate(options) {
        const plan = Gridfinity.planBaseplateSegments(options);
        const source = `// Generated with the Gridfinity baseplate generator. Edit the options and regenerate as needed.\nconst result = Gridfinity.segmentedBaseplate(${JSON.stringify(options, null, 4)});\nresult;\n`;
        const spareText = plan.extraConnectors
            ? `, including ${plan.extraConnectors} spare connector${plan.extraConnectors === 1 ? '' : 's'}`
            : '';
        return {
            source,
            summary: `Generated ${plan.segments.length} baseplate segment${plan.segments.length === 1 ? '' : 's'}${spareText}. The editor preview and 3MF export contain the complete set.`
        };
    }
});
