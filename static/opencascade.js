/**
 * Official opencascade.js release used by daz-cad.
 *
 * npm dist-tag `beta` is 2.0.0-beta.b5ff984 (published 2023-03-23). The `latest`
 * tag is the older 1.x API and is not a newer build. Forks such as
 * @taucad/opencascade.js are not drop-in replacements.
 */
export const OPENCASCADE_VERSION = "2.0.0-beta.b5ff984";

export const OPENCASCADE_CDN = `https://cdn.jsdelivr.net/npm/opencascade.js@${OPENCASCADE_VERSION}/dist`;

export async function loadOpenCascade() {
    let lastError = null;
    for (let attempt = 1; attempt <= 3; attempt++) {
        try {
            const initOC = await import(`${OPENCASCADE_CDN}/opencascade.full.js`);
            const oc = await initOC.default({
                locateFile: (file) => (file.endsWith(".wasm") ? `${OPENCASCADE_CDN}/${file}` : file),
            });
            await oc.ready;
            return oc;
        } catch (error) {
            lastError = error;
            if (attempt === 3) break;
            await new Promise((resolve) => setTimeout(resolve, 400 * attempt));
        }
    }
    throw lastError;
}
