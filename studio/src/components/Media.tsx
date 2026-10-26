// Image or video from the run's public dir, with a Ken Burns move for stills.
import {Video} from '@remotion/media';
import React from 'react';
import {Img, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {clamp} from '../lib/anim';
import type {Visual} from '../types';

export const hasMedia = (v?: Visual) => Boolean(v && v.resolved && v.kind && v.kind !== 'none');

const kenBurns = (motion: Visual['motion'], p: number) => {
	switch (motion) {
		case 'static':
			return 'scale(1)';
		case 'zoom_out':
			return `scale(${interpolate(p, [0, 1], [1.18, 1.02], clamp)})`;
		case 'pan_left':
			return `scale(1.15) translateX(${interpolate(p, [0, 1], [4, -4], clamp)}%)`;
		case 'pan_right':
			return `scale(1.15) translateX(${interpolate(p, [0, 1], [-4, 4], clamp)}%)`;
		case 'pan_up':
			return `scale(1.15) translateY(${interpolate(p, [0, 1], [4, -4], clamp)}%)`;
		case 'pan_down':
			return `scale(1.15) translateY(${interpolate(p, [0, 1], [-4, 4], clamp)}%)`;
		default:
			return `scale(${interpolate(p, [0, 1], [1.02, 1.18], clamp)})`;
	}
};

export const Media: React.FC<{
	visual: Visual;
	durationInFrames: number;
	fit?: 'cover' | 'contain';
	style?: React.CSSProperties;
}> = ({visual, durationInFrames, fit = 'cover', style}) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	if (!hasMedia(visual)) return null;
	const src = staticFile(visual.resolved as string);
	const box: React.CSSProperties = {width: '100%', height: '100%', objectFit: fit, ...style};
	if (visual.kind === 'video') {
		// Stock and AI clips are short; loop them and keep them muted (voice + music carry the audio).
		const p = frame / Math.max(1, durationInFrames);
		const motion = visual.motion && visual.motion !== 'static' ? kenBurns(visual.motion, p) : 'scale(1.02)';
		return (
			<div style={{width: '100%', height: '100%', overflow: 'hidden'}}>
				<Video src={src} muted loop objectFit={fit} style={{...box, transform: motion}} />
			</div>
		);
	}
	const p = frame / Math.max(1, durationInFrames + fps * 0.4);
	return (
		<div style={{width: '100%', height: '100%', overflow: 'hidden'}}>
			<Img src={src} style={{...box, transform: kenBurns(visual.motion, p)}} />
		</div>
	);
};
