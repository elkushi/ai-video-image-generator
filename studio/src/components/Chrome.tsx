// Persistent overlays: progress bar and corner logo watermark.
import React from 'react';
import {Img, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {clamp} from '../lib/anim';
import {useLayout, useTheme, useVideoProps} from '../lib/theme';

export const ProgressBar: React.FC = () => {
	const frame = useCurrentFrame();
	const {durationInFrames} = useVideoConfig();
	const t = useTheme();
	const L = useLayout();
	const p = interpolate(frame, [0, durationInFrames - 1], [0, 100], clamp);
	return (
		<div style={{position: 'absolute', top: 0, left: 0, right: 0, height: 8 * L.u, background: 'rgba(255,255,255,0.12)'}}>
			<div
				style={{
					width: `${p}%`,
					height: '100%',
					background: t.primary === t.bg ? '#FFFFFF' : t.primary,
					marginInlineStart: t.dir === 'rtl' ? 'auto' : undefined,
				}}
			/>
		</div>
	);
};

// Hidden while a scene that already shows the logo is on screen.
export const Watermark: React.FC = () => {
	const frame = useCurrentFrame();
	const t = useTheme();
	const L = useLayout();
	const {scenes, transitionFrames} = useVideoProps();
	if (!t.logo) return null;
	const showsLogo = scenes.some(
		(s) => (s.type === 'LogoReveal' || s.type === 'CTAEndCard') && frame >= s.from - transitionFrames && frame < s.from + s.duration + transitionFrames,
	);
	const fadeIn = interpolate(frame, [12, 30], [0, 1], clamp);
	const h = (L.landscape ? 44 : 52) * L.u;
	return (
		<Img
			src={t.logo}
			style={{
				position: 'absolute',
				top: L.portrait ? 240 * L.u : 44 * L.u,
				[t.dir === 'rtl' ? 'left' : 'right']: L.pad * 0.7,
				height: h,
				opacity: showsLogo ? 0 : 0.85 * fadeIn,
			}}
		/>
	);
};
