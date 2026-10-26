// Bundle once, render several compositions. Called by tools/render.py.
// node render.mjs --props <props.json> --public <dir> --out <dir> --comps Video-9x16,Video-1x1 [--scale 0.5] [--concurrency 2] [--crf 18] [--frames 0-90]
import {bundle} from '@remotion/bundler';
import {renderMedia, renderStill, selectComposition} from '@remotion/renderer';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const args = Object.fromEntries(
	process.argv.slice(2).reduce((acc, cur, i, arr) => (cur.startsWith('--') ? [...acc, [cur.slice(2), arr[i + 1]]] : acc), []),
);
const here = path.dirname(fileURLToPath(import.meta.url));
const inputProps = JSON.parse(fs.readFileSync(args.props, 'utf8'));
const comps = args.comps.split(',');
const scale = Number(args.scale ?? 1);
const concurrency = Number(args.concurrency ?? 2);

const t0 = Date.now();
const serveUrl = await bundle({entryPoint: path.join(here, 'src/index.ts'), publicDir: path.resolve(args.public)});
console.log(`bundled in ${((Date.now() - t0) / 1000).toFixed(1)}s`);
console.log(`@@bundle ${JSON.stringify({seconds: (Date.now() - t0) / 1000})}`);

for (const id of comps) {
	const composition = await selectComposition({serveUrl, id, inputProps});
	const out = path.join(args.out, `${id}${scale < 1 ? '.preview' : ''}.mp4`);
	const t1 = Date.now();
	let last = -1;
	let lastEvent = 0;
	console.log(`@@start ${JSON.stringify({comp: id, frames: composition.durationInFrames, width: Math.round(composition.width * scale), height: Math.round(composition.height * scale)})}`);
	const frameRange = args.frames ? args.frames.split('-').map(Number) : null;
	await renderMedia({
		composition,
		serveUrl,
		codec: 'h264',
		outputLocation: out,
		inputProps,
		scale,
		concurrency,
		crf: Number(args.crf ?? 18),
		imageFormat: 'jpeg',
		jpegQuality: 90,
		audioBitrate: '192k',
		frameRange,
		chromiumOptions: {gl: 'swangle'},
		timeoutInMilliseconds: 120000,
		onProgress: ({progress, renderedFrames, encodedFrames, stitchStage}) => {
			const now = Date.now();
			if (now - lastEvent > 700 || progress >= 1) {
				lastEvent = now;
				console.log(`@@progress ${JSON.stringify({comp: id, progress, renderedFrames, encodedFrames, stage: stitchStage, elapsed: (now - t1) / 1000})}`);
			}
			const pct = Math.floor(progress * 10) * 10;
			if (pct !== last) {
				last = pct;
				process.stdout.write(`  ${id} ${pct}%\n`);
			}
		},
	});
	console.log(`rendered ${out} in ${((Date.now() - t1) / 1000).toFixed(0)}s`);
	console.log(`@@done ${JSON.stringify({comp: id, out, seconds: (Date.now() - t1) / 1000})}`);
	if (args.cover && scale >= 1) {
		const cover = path.join(args.out, `${id}.cover.jpg`);
		await renderStill({composition, serveUrl, output: cover, inputProps, frame: Number(args.cover), imageFormat: 'jpeg', jpegQuality: 92});
		console.log(`cover ${cover}`);
		console.log(`@@cover ${JSON.stringify({comp: id, out: cover})}`);
	}
}
