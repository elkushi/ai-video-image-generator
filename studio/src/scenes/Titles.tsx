// KineticTitle, LogoReveal, CTAEndCard.
import React from 'react';
import {AbsoluteFill, Img, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {Media, hasMedia} from '../components/Media';
import {Kicker, Para, Stage, Words} from '../components/Text';
import {clamp, pop} from '../lib/anim';
import {useLayout, useTheme} from '../lib/theme';
import type {Scene} from '../types';
import {st} from '../lib/stress';

const Scrim: React.FC<{strength?: number}> = ({strength = 0.7}) => {
	const t = useTheme();
	return (
		<AbsoluteFill
			style={{background: `linear-gradient(180deg, ${t.bg}${Math.round(strength * 160).toString(16).padStart(2, '0')} 0%, ${t.bg}${Math.round(strength * 255).toString(16).padStart(2, '0')} 100%)`}}
		/>
	);
};

// props: title, subtitle?, kicker?, highlight?: string[], align?: "center"|"start"
export const KineticTitle: React.FC<{scene: Scene}> = ({scene}) => {
	const L = useLayout();
	const {title, subtitle, kicker, highlight, align} = scene.props;
	const center = align !== 'start';
	const words = String(title).split(/\s+/).length;
	const size = (L.landscape ? 104 : L.portrait ? (words > 6 ? 104 : 124) : 100) * L.u;
	return (
		<AbsoluteFill>
			{hasMedia(scene.visual) ? (
				<AbsoluteFill>
					<Media visual={scene.visual} durationInFrames={scene.duration} />
					<Scrim />
				</AbsoluteFill>
			) : null}
			<Stage>
				<Kicker text={kicker} center={center} />
				<Words text={title} size={size} center={center} highlight={highlight} delay={kicker ? 6 : 0} />
				<Para text={subtitle} center={center} delay={10 + words * 3} />
			</Stage>
		</AbsoluteFill>
	);
};

// props: tagline?
export const LogoReveal: React.FC<{scene: Scene}> = ({scene}) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	const t = useTheme();
	const L = useLayout();
	const p = pop(frame, fps, 2, 12);
	const ring = interpolate(frame, [0, 30], [0.6, 1.25], clamp);
	return (
		<AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
			<div
				style={{
					position: 'absolute',
					width: 520 * L.u,
					height: 520 * L.u,
					borderRadius: 520 * L.u * 0.22,
					border: `${4 * L.u}px solid ${t.primary}`,
					transform: `rotate(-12deg) scale(${ring})`,
					opacity: interpolate(frame, [0, 30], [0.9, 0], clamp),
				}}
			/>
			<div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 44 * L.u, padding: `0 ${L.pad}px`}}>
				{t.logo ? (
					<Img src={t.logo} style={{width: (L.landscape ? 560 : 640) * L.u, maxWidth: L.w * 0.78, objectFit: 'contain', transform: `scale(${0.7 + 0.3 * p})`, opacity: p}} />
				) : (
					<Words text={t.brandName} size={140 * L.u} center />
				)}
				{scene.props.tagline ? <Para text={scene.props.tagline} center delay={14} /> : null}
			</div>
		</AbsoluteFill>
	);
};

// props: headline, button?, url?, sub?
export const CTAEndCard: React.FC<{scene: Scene}> = ({scene}) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	const t = useTheme();
	const L = useLayout();
	const {headline, button, url, sub} = scene.props;
	const btn = pop(frame, fps, 14, 12);
	const pulse = 1 + Math.sin(Math.max(0, frame - 30) / 6) * 0.025;
	return (
		<Stage gap={44}>
			{t.logo ? (
				<div style={{display: 'flex', justifyContent: 'center', opacity: pop(frame, fps, 0)}}>
					<Img src={t.logo} style={{height: (L.landscape ? 90 : 110) * L.u, objectFit: 'contain'}} />
				</div>
			) : null}
			<Words text={headline} size={(L.landscape ? 88 : 100) * L.u} center delay={4} />
			<Para text={sub} center delay={10} />
			{button ? (
				<div style={{display: 'flex', justifyContent: 'center'}}>
					<div
						style={{
							transform: `scale(${btn * pulse})`,
							opacity: btn,
							background: t.primary === t.bg ? '#FFFFFF' : t.primary,
							color: t.primary === t.bg ? t.primary : t.onPrimary,
							fontFamily: t.heading,
							fontWeight: 800,
							fontSize: (L.landscape ? 44 : 52) * L.u,
							padding: `${26 * L.u}px ${64 * L.u}px`,
							borderRadius: 999,
							boxShadow: `0 ${16 * L.u}px ${48 * L.u}px ${t.primary}66`,
						}}
					>
						{st(button)}
					</div>
				</div>
			) : null}
			{(url || t.website) && (url || t.website) !== button ? (
				<div style={{textAlign: 'center', fontSize: 40 * L.u, fontWeight: 600, color: t.fgMuted, opacity: pop(frame, fps, 22)}}>{url || t.website}</div>
			) : null}
		</Stage>
	);
};
