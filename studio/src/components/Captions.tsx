// Word-level captions from edge-tts timings. Pages of ~1.2 s; the active word is highlighted.
// Arabic: words stay whole (never split into letters) and the line gets dir="rtl".
import {createTikTokStyleCaptions} from '@remotion/captions';
import React, {useMemo} from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {bidiRuns, isRtlText, pop} from '../lib/anim';
import {useLayout, useTheme, useVideoProps} from '../lib/theme';
import {st} from '../lib/stress';

export const Captions: React.FC = () => {
	const {captions, captionStyle, theme} = useVideoProps();
	const t = useTheme();
	const L = useLayout(true);
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	const ms = (frame / fps) * 1000;

	const {pages} = useMemo(
		() => createTikTokStyleCaptions({captions, combineTokensWithinMilliseconds: L.landscape ? 1800 : 1200}),
		[captions, L.landscape],
	);
	const page = pages.find((p) => ms >= p.startMs && ms < p.startMs + p.durationMs + 250);
	if (!page) return null;
	const rtl = t.dir === 'rtl' || isRtlText(page.text);
	const size = (L.landscape ? 52 : L.portrait ? 70 : 58) * L.u;
	// white captions vanish on the light theme's pale background, so use the theme's text colour there
	const light = theme === 'light';
	const ink = light ? t.fg : '#FFFFFF';
	const inkDim = light ? t.fgMuted : 'rgba(255,255,255,0.78)';
	const pageFrame = frame - Math.round((page.startMs / 1000) * fps);

	return (
		<AbsoluteFill style={{pointerEvents: 'none'}}>
			<div
				dir={rtl ? 'rtl' : 'ltr'}
				lang={t.lang}
				style={{
					position: 'absolute',
					left: L.pad,
					right: L.pad,
					top: L.captionY,
					transform: `translateY(-50%) scale(${captionStyle === 'minimal' ? 1 : 0.92 + 0.08 * pop(pageFrame, fps, 0, 14)})`,
					textAlign: 'center',
					fontFamily: t.heading,
					fontWeight: 800,
					fontSize: size,
					lineHeight: 1.25,
					color: ink,
					textShadow: light ? `0 0 ${14 * L.u}px rgba(255,255,255,0.9)` : `0 ${4 * L.u}px ${18 * L.u}px rgba(0,0,0,0.55)`,
				}}
			>
				{bidiRuns(page.tokens.map((tok) => tok.text.trim()), rtl).map(([a, b]) => {
					const toks = page.tokens.slice(a, b);
					const active = ms >= toks[0].fromMs && ms < toks[toks.length - 1].toMs;
					const done = ms >= toks[toks.length - 1].toMs;
					const highlight = captionStyle === 'highlight' && active;
					return (
						<span
							key={a}
							dir={rtl && b - a > 1 ? 'ltr' : undefined}
							style={{
								display: 'inline-block',
								whiteSpace: 'pre',
								padding: `0 ${10 * L.u}px`,
								margin: `${4 * L.u}px 0`,
								borderRadius: 14 * L.u,
								background: highlight ? t.pill : 'transparent',
								color: highlight ? '#FFFFFF' : captionStyle === 'minimal' || active || done ? ink : inkDim,
								transform: captionStyle === 'pop' && active ? 'scale(1.12)' : 'none',
							}}
						>
							{st(toks.map((tok) => tok.text.trim()).join(' '))}
						</span>
					);
				})}
			</div>
		</AbsoluteFill>
	);
};
