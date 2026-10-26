// Typographic building blocks used by the scenes.
import React from 'react';
import {AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {bidiRuns, clamp, isRtlText, pop} from '../lib/anim';
import {useLayout, useTheme, useVideoProps} from '../lib/theme';
import {st} from '../lib/stress';

// Content box between the safe top and the caption zone.
export const Stage: React.FC<{children: React.ReactNode; align?: 'center' | 'start'; gap?: number; style?: React.CSSProperties}> = ({
	children,
	align = 'center',
	gap = 36,
	style,
}) => {
	const {showCaptions} = useVideoProps();
	const L = useLayout(showCaptions);
	const t = useTheme();
	return (
		<AbsoluteFill>
			<div
				dir={t.dir}
				lang={t.lang}
				style={{
					position: 'absolute',
					left: L.pad,
					right: L.pad,
					top: L.top,
					height: L.bottom - L.top,
					display: 'flex',
					flexDirection: 'column',
					justifyContent: align === 'center' ? 'center' : 'flex-start',
					alignItems: 'stretch',
					gap: gap * L.u,
					color: t.fg,
					fontFamily: t.body,
					...style,
				}}
			>
				{children}
			</div>
		</AbsoluteFill>
	);
};

export const Kicker: React.FC<{text?: string; delay?: number; center?: boolean}> = ({text, delay = 0, center}) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	const t = useTheme();
	const L = useLayout();
	if (!text) return null;
	const p = pop(frame, fps, delay);
	const latin = t.lang !== 'ar';
	return (
		<div style={{display: 'flex', justifyContent: center ? 'center' : 'flex-start'}}>
			<div
				style={{
					opacity: p,
					transform: `translateY(${(1 - p) * 20}px)`,
					background: t.pill,
					color: t.onPrimary,
					fontFamily: t.heading,
					fontWeight: 700,
					fontSize: (L.landscape ? 26 : 30) * L.u,
					letterSpacing: latin ? '0.14em' : undefined,
					textTransform: latin ? 'uppercase' : undefined,
					padding: `${10 * L.u}px ${22 * L.u}px`,
					borderRadius: 999,
				}}
			>
				{st(text)}
			</div>
		</div>
	);
};

// Word-by-word reveal. Splits on spaces only, so Arabic letters stay joined.
export const Words: React.FC<{
	text: string;
	size: number;
	weight?: number;
	delay?: number;
	perWord?: number;
	color?: string;
	center?: boolean;
	highlight?: string[]; // words drawn in the accent colour
	lineHeight?: number;
}> = ({text, size, weight = 800, delay = 0, perWord = 3, color, center, highlight = [], lineHeight = 1.08}) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	const t = useTheme();
	const words = String(text).split(/\s+/).filter(Boolean);
	const rtl = t.dir === 'rtl' || isRtlText(text); // an Arabic video keeps RTL order even when a line is mostly Latin
	const hl = new Set(highlight.map((w) => w.toLowerCase()));
	return (
		<div
			dir={rtl ? 'rtl' : t.dir}
			style={{
				fontFamily: t.heading,
				fontWeight: weight,
				fontSize: size,
				lineHeight,
				letterSpacing: t.lang === 'ar' ? undefined : '-0.02em',
				color: color ?? t.fg,
				textAlign: center ? 'center' : 'start',
			}}
		>
			{bidiRuns(words, rtl).map(([a, b], i, runs) => {
				const p = pop(frame, fps, delay + a * perWord, 16);
				const run = words.slice(a, b);
				const ltrRun = rtl && b - a > 1;
				return (
					<span
						key={a}
						dir={ltrRun ? 'ltr' : undefined}
						style={{
							display: 'inline-block',
							whiteSpace: 'pre',
							opacity: interpolate(p, [0, 0.6], [0, 1], clamp),
							transform: `translateY(${(1 - p) * size * 0.45}px)`,
						}}
					>
						{run.map((w, j) => (
							<span key={j} style={{color: hl.has(w.toLowerCase().replace(/[.,!?:;]/g, '')) ? t.accent : undefined}}>
								{st(w)}
								{j < run.length - 1 || i < runs.length - 1 ? ' ' : ''}
							</span>
						))}
					</span>
				);
			})}
		</div>
	);
};

export const Para: React.FC<{text?: string; delay?: number; center?: boolean; size?: number}> = ({text, delay = 10, center, size}) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	const t = useTheme();
	const L = useLayout();
	if (!text) return null;
	const p = pop(frame, fps, delay);
	return (
		<div
			style={{
				opacity: p,
				transform: `translateY(${(1 - p) * 24}px)`,
				fontSize: size ?? (L.landscape ? 38 : 44) * L.u,
				lineHeight: 1.35,
				color: t.fgMuted,
				fontWeight: 500,
				textAlign: center ? 'center' : 'start',
			}}
		>
			{text}
		</div>
	);
};

// Icon tile: brand asset path (relative to brand folder), or a short glyph/number.
export const IconTile: React.FC<{icon?: string; size: number; index?: number}> = ({icon, size, index}) => {
	const t = useTheme();
	const {brandBase} = useVideoProps();
	const isFile = icon && /\.(svg|png|jpe?g|webp)$/i.test(icon);
	return (
		<div
			style={{
				width: size,
				height: size,
				flex: 'none',
				borderRadius: size * 0.28,
				background: t.pill,
				display: 'flex',
				alignItems: 'center',
				justifyContent: 'center',
				color: t.onPrimary,
				fontFamily: t.heading,
				fontWeight: 800,
				fontSize: size * 0.42,
			}}
		>
			{isFile ? (
				<Img src={staticFile(`${brandBase}${icon}`)} style={{width: size * 0.56, height: size * 0.56, objectFit: 'contain'}} />
			) : (
				icon ?? (index !== undefined ? String(index + 1) : '•')
			)}
		</div>
	);
};
