// The one composition every aspect ratio renders: background, scenes on the voice timeline,
// voice + ducked music, captions, progress bar and logo.
import {Audio} from '@remotion/media';
import React from 'react';
import {AbsoluteFill, Sequence, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {Background} from './components/Background';
import {Captions} from './components/Captions';
import {ProgressBar, Watermark} from './components/Chrome';
import {clamp} from './lib/anim';
import {loadBrandFonts} from './lib/fonts';
import {ThemeProvider, makeTheme, useLayout} from './lib/theme';
import {FilmGrain, LottieSticker, Vignette} from './components/Look';
import {FX} from './lib/transitions';
import {SCENES} from './scenes';
import type {Scene, VideoProps} from './types';

// Entrance for a scene: overlaps the previous scene's exit by `T` frames.
const SceneShell: React.FC<{scene: Scene; T: number; first: boolean; last: boolean; children: React.ReactNode}> = ({scene, T, first, last, children}) => {
	const frame = useCurrentFrame();
	const L = useLayout();
	const kind = scene.transition ?? 'fade';
	const enter = first || kind === 'none' ? 1 : interpolate(frame, [0, T], [0, 1], clamp);
	const exit = last ? 1 : interpolate(frame, [scene.duration, scene.duration + T], [1, 0], clamp);
	const fx = FX[kind];
	if (fx) {
		// cinematic presentation only inside the overlap windows; plain scene in between
		const p = fx();
		const Comp = p.component;
		const inEnter = !first && frame < T;
		const inExit = !last && frame >= scene.duration;
		if (inEnter || inExit) {
			const progress = inEnter ? interpolate(frame, [0, T], [0, 1], clamp) : interpolate(frame, [scene.duration, scene.duration + T], [0, 1], clamp);
			return (
				<AbsoluteFill>
					<Comp presentationDirection={inEnter ? 'entering' : 'exiting'} presentationProgress={progress} passedProps={p.props ?? {}} presentationDurationInFrames={T} bothEnteringAndExiting={false} onElementImage={() => {}} onUnmount={() => {}}>
						{children}
					</Comp>
				</AbsoluteFill>
			);
		}
		return <AbsoluteFill>{children}</AbsoluteFill>;
	}
	let transform = 'none';
	let clipPath: string | undefined;
	if (kind === 'slide') transform = `translateX(${(1 - enter) * 12 * (L.w / 100)}px)`;
	if (kind === 'zoom') transform = `scale(${1.08 - 0.08 * enter})`;
	if (kind === 'wipe') clipPath = `inset(0 ${(1 - enter) * 100}% 0 0)`;
	return <AbsoluteFill style={{opacity: kind === 'wipe' ? exit : enter * exit, transform, clipPath}}>{children}</AbsoluteFill>;
};

const Music: React.FC<{props: VideoProps}> = ({props}) => {
	const m = props.music;
	if (!m) return null;
	const ramp = 8;
	const volume = (f: number) => {
		// duck under speech, rise in the gaps, fade in/out at the ends
		let d = 1;
		for (const [a, b] of props.voiceRanges) {
			if (f >= a - ramp && f <= b + ramp) {
				d = Math.min(d, f < a ? (a - f) / ramp : f > b ? (f - b) / ramp : 0);
			}
		}
		const level = m.underVoice + (m.noVoice - m.underVoice) * d;
		const edges = Math.min(
			interpolate(f, [0, m.fadeFrames], [0, 1], clamp),
			interpolate(f, [props.totalFrames - m.fadeFrames * 1.5, props.totalFrames - 1], [1, 0], clamp),
		);
		return level * edges;
	};
	return <Audio src={staticFile(m.src)} volume={volume} loop />;
};

export const Video: React.FC<VideoProps> = (props) => {
	loadBrandFonts(props.brand, props.brandBase);
	const T = props.transitionFrames;
	return (
		<ThemeProvider props={props}>
			<AbsoluteFill dir={props.dir} lang={props.language} style={{fontFamily: makeTheme(props).body}}>
				<Background />
				{props.scenes.map((scene, i) => {
					const Comp = SCENES[scene.type];
					const last = i === props.scenes.length - 1;
					if (!Comp) throw new Error(`Unknown scene type ${scene.type} (scene ${scene.id})`);
					return (
						<Sequence key={scene.id} name={`${scene.id} · ${scene.type}`} from={scene.from} durationInFrames={scene.duration + (last ? 0 : T)}>
							<SceneShell scene={scene} T={T} first={i === 0} last={last}>
								<Comp scene={scene} />
								{scene.lottie ? <LottieSticker {...scene.lottie} /> : null}
							</SceneShell>
						</Sequence>
					);
				})}
				{props.look?.vignette ? <Vignette intensity={props.look.vignette} /> : null}
					{props.look?.grain ? <FilmGrain opacity={props.look.grain} /> : null}
					{props.showCaptions ? <Captions /> : null}
				{props.watermarkLogo ? <Watermark /> : null}
				{props.progressBar ? <ProgressBar /> : null}
				{props.voice ? <Audio src={staticFile(props.voice)} /> : null}
				{(props.sfx ?? []).map((e, i) => (
					<Sequence key={`sfx${i}`} from={e.frame} durationInFrames={Math.max(1, props.totalFrames - e.frame)} layout="none">
						<Audio src={staticFile(e.src)} volume={e.volume} />
					</Sequence>
				))}
				<Music props={props} />
			</AbsoluteFill>
		</ThemeProvider>
	);
};
