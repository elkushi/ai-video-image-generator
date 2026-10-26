// Continuous animated brand background behind every scene (keeps cuts feeling like one piece).
import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {useTheme} from '../lib/theme';

const Squares: React.FC<{color: string; frame: number; w: number; h: number}> = ({color, frame, w, h}) => {
	const s = Math.min(w, h);
	const items = [
		{x: -0.12 * s, y: -0.1 * s, size: 0.62 * s, rot: -12, fill: false, speed: 0.04},
		{x: w - 0.38 * s, y: h - 0.42 * s, size: 0.72 * s, rot: -12, fill: true, speed: -0.03},
		{x: w - 0.22 * s, y: 0.12 * s, size: 0.26 * s, rot: -12, fill: true, speed: 0.06},
	];
	return (
		<>
			{items.map((it, i) => (
				<div
					key={i}
					style={{
						position: 'absolute',
						left: it.x,
						top: it.y + Math.sin((frame + i * 40) / 60) * 12,
						width: it.size,
						height: it.size,
						borderRadius: it.size * 0.22,
						transform: `rotate(${it.rot + frame * it.speed}deg)`,
						border: it.fill ? undefined : `${Math.max(2, s * 0.003)}px solid ${color}`,
						background: it.fill ? color : undefined,
						opacity: it.fill ? 0.07 : 0.16,
					}}
				/>
			))}
		</>
	);
};

export const Background: React.FC = () => {
	const t = useTheme();
	const frame = useCurrentFrame();
	const {width, height} = useVideoConfig();
	const glowX = 50 + Math.sin(frame / 90) * 18;
	return (
		<AbsoluteFill style={{background: t.bg, overflow: 'hidden'}}>
			<AbsoluteFill
				style={{
					background: `radial-gradient(circle at ${glowX}% 30%, ${t.primary}55 0%, transparent 55%)`,
				}}
			/>
			{t.motif !== 'none' ? <Squares color={t.motif === 'tilted_squares' ? '#FFFFFF' : t.accent} frame={frame} w={width} h={height} /> : null}
		</AbsoluteFill>
	);
};
