// Presenter: AI talking-head clip when make_avatar.py produced one, otherwise the built-in mascot
// whose mouth follows the voiceover loudness (always free, fully local).
import {Video} from '@remotion/media';
import React from 'react';
import {AbsoluteFill, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {hasMedia} from '../components/Media';
import {Kicker, Para, Stage, Words} from '../components/Text';
import {pop} from '../lib/anim';
import {useLayout, useTheme, useVideoProps} from '../lib/theme';
import type {Scene} from '../types';

// Mouth opening from the precomputed per-frame voice loudness, lightly smoothed.
const useMouth = (absFrame: number) => {
	const {voiceLevels} = useVideoProps();
	const at = (f: number) => voiceLevels[Math.max(0, Math.min(voiceLevels.length - 1, f))] ?? 0;
	if (!voiceLevels.length) return 0;
	const v = (at(absFrame - 1) + 2 * at(absFrame) + at(absFrame + 1)) / 4;
	return v < 0.12 ? 0 : Math.min(1, v * 1.1);
};

export const Mascot: React.FC<{size: number; absFrame: number}> = ({size, absFrame}) => {
	const frame = useCurrentFrame();
	const t = useTheme();
	const mouth = useMouth(absFrame);
	const blink = frame % 96 > 90 ? 0.12 : 1;
	const bob = Math.sin(frame / 14) * 6;
	const tilt = Math.sin(frame / 40) * 3;
	const look = Math.sin(frame / 55) * 4;
	return (
		<svg width={size} height={size * 1.15} viewBox="0 0 200 230" style={{transform: `translateY(${bob}px) rotate(${tilt}deg)`, overflow: 'visible'}}>
			<defs>
				<linearGradient id="mascotBody" x1="0" y1="0" x2="1" y2="1">
					<stop offset="0" stopColor={t.accent} />
					<stop offset="1" stopColor={t.primary} />
				</linearGradient>
			</defs>
			<ellipse cx="100" cy="222" rx="62" ry="8" fill="rgba(0,0,0,0.25)" />
			<rect x="52" y="150" width="96" height="66" rx="26" fill={t.secondary} />
			<rect x="20" y="14" width="160" height="150" rx="44" fill="url(#mascotBody)" transform="rotate(-6 100 90)" />
			<rect x="44" y="44" width="112" height="86" rx="30" fill="#FFFFFF" opacity="0.96" transform="rotate(-6 100 90)" />
			<g transform="rotate(-6 100 90)">
				<ellipse cx={78 + look} cy="78" rx="9" ry={11 * blink} fill={t.secondary} />
				<ellipse cx={122 + look} cy="78" rx="9" ry={11 * blink} fill={t.secondary} />
				<circle cx={81 + look} cy="74" r="2.6" fill="#FFFFFF" opacity={blink > 0.5 ? 1 : 0} />
				<circle cx={125 + look} cy="74" r="2.6" fill="#FFFFFF" opacity={blink > 0.5 ? 1 : 0} />
				{mouth > 0 ? (
					<ellipse cx="100" cy="104" rx={13 + mouth * 5} ry={3 + mouth * 12} fill={t.secondary} />
				) : (
					<path d="M86 100 Q100 113 114 100" stroke={t.secondary} strokeWidth="5" strokeLinecap="round" fill="none" />
				)}
				<ellipse cx="62" cy="104" rx="8" ry="4" fill={t.primary} opacity="0.25" />
				<ellipse cx="138" cy="104" rx="8" ry="4" fill={t.primary} opacity="0.25" />
			</g>
			<line x1="100" y1="16" x2="104" y2="-6" stroke={t.secondary} strokeWidth="5" strokeLinecap="round" />
			<circle cx="104" cy="-8" r="8" fill={t.accent} />
		</svg>
	);
};

// props: title?, text?, name?, role?
export const Presenter: React.FC<{scene: Scene}> = ({scene}) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	const t = useTheme();
	const L = useLayout();
	const {title, text, name, role} = scene.props;
	const avatar = hasMedia(scene.visual) && scene.visual.kind === 'video';
	const e = pop(frame, fps, 0, 14);
	const span = L.bottom - L.top;
	const figure = avatar ? (
		<div
			style={{
				width: L.landscape ? span * 0.9 : Math.min(L.w - L.pad * 2, span * 0.62),
				aspectRatio: '1',
				borderRadius: t.radius * L.u * 1.6,
				overflow: 'hidden',
				border: `${6 * L.u}px solid ${t.primary}`,
				boxShadow: `0 ${30 * L.u}px ${80 * L.u}px rgba(0,0,0,0.45)`,
				transform: `scale(${0.9 + 0.1 * e})`,
				opacity: e,
			}}
		>
			<Video src={staticFile(scene.visual.resolved as string)} muted objectFit="cover" style={{width: '100%', height: '100%'}} />
		</div>
	) : (
		<div style={{opacity: e, transform: `scale(${0.8 + 0.2 * e})`}}>
			<Mascot size={(L.landscape ? span * 0.6 : Math.min(span * 0.55, 620 * L.u))} absFrame={scene.from + frame} />
		</div>
	);
	const nameTag = name ? (
		<div style={{display: 'flex', justifyContent: L.landscape ? 'flex-start' : 'center'}}>
			<div style={{background: t.primary, color: t.onPrimary, borderRadius: 18 * L.u, padding: `${12 * L.u}px ${26 * L.u}px`, opacity: pop(frame, fps, 10)}}>
				<span style={{fontWeight: 800, fontSize: 38 * L.u}}>{name}</span>
				{role ? <span style={{fontSize: 30 * L.u, opacity: 0.85}}>{`  ${role}`}</span> : null}
			</div>
		</div>
	) : null;

	if (L.landscape) {
		return (
			<Stage>
				<div style={{display: 'flex', alignItems: 'center', gap: 70 * L.u}}>
					<div style={{flex: 'none'}}>{figure}</div>
					<div style={{display: 'flex', flexDirection: 'column', gap: 26 * L.u}}>
						{nameTag}
						{title ? <Words text={title} size={76 * L.u} /> : null}
						<Para text={text} />
					</div>
				</div>
			</Stage>
		);
	}
	return (
		<AbsoluteFill>
			<Stage gap={30}>
				<Kicker text={scene.props.kicker} center />
				{title ? <Words text={title} size={(L.portrait ? 80 : 68) * L.u} center /> : null}
				<div style={{display: 'flex', justifyContent: 'center'}}>{figure}</div>
				{nameTag}
				<Para text={text} center />
			</Stage>
		</AbsoluteFill>
	);
};
