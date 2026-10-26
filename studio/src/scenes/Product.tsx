// ProductHero, ScreenDemo.
import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {Media} from '../components/Media';
import {Kicker, Para, Stage, Words} from '../components/Text';
import {clamp, ease, pop} from '../lib/anim';
import {useLayout, useTheme} from '../lib/theme';
import type {Scene} from '../types';

// props: title?, caption?, kicker?, fullBleed?: boolean
export const ProductHero: React.FC<{scene: Scene}> = ({scene}) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	const t = useTheme();
	const L = useLayout();
	const {title, caption, kicker, fullBleed} = scene.props;
	if (fullBleed) {
		return (
			<AbsoluteFill>
				<Media visual={scene.visual} durationInFrames={scene.duration} />
				<AbsoluteFill style={{background: `linear-gradient(180deg, transparent 35%, ${t.bg}EE 100%)`}} />
				<Stage align="start" style={{justifyContent: 'flex-end'}}>
					<Kicker text={kicker} />
					{title ? <Words text={title} size={(L.landscape ? 84 : 96) * L.u} /> : null}
					<Para text={caption} />
				</Stage>
			</AbsoluteFill>
		);
	}
	const p = pop(frame, fps, 0, 15);
	const cardH = (L.bottom - L.top) * (title ? (L.landscape ? 0.62 : 0.6) : 0.85);
	if (scene.props.cutout) {
		// transparent product cut-out (tools/cutout.py): float it on the brand background with a soft shadow
		const float = Math.sin(frame / 22) * 8 * L.u;
		return (
			<Stage gap={40}>
				<Kicker text={kicker} center />
				<div style={{height: cardH, position: 'relative', transform: `translateY(${(1 - p) * 80 + float}px) scale(${0.85 + 0.15 * p})`, opacity: p}}>
					<div style={{position: 'absolute', left: '20%', right: '20%', bottom: '2%', height: '6%', borderRadius: '50%', background: 'rgba(0,0,0,0.45)', filter: `blur(${18 * L.u}px)`}} />
					<Media visual={{...scene.visual, motion: 'static'}} durationInFrames={scene.duration} fit="contain" style={{filter: `drop-shadow(0 ${20 * L.u}px ${40 * L.u}px rgba(0,0,0,0.35))`}} />
				</div>
				{title ? <Words text={title} size={(L.landscape ? 72 : 84) * L.u} center delay={8} /> : null}
				<Para text={caption} center delay={14} />
			</Stage>
		);
	}
	return (
		<Stage gap={40}>
			<Kicker text={kicker} center />
			<div
				style={{
					height: cardH,
					borderRadius: t.radius * L.u * 1.4,
					overflow: 'hidden',
					transform: `translateY(${(1 - p) * 80}px) scale(${0.92 + 0.08 * p}) rotate(${(1 - p) * -3}deg)`,
					opacity: p,
					boxShadow: `0 ${30 * L.u}px ${90 * L.u}px rgba(0,0,0,0.45), 0 0 0 ${3 * L.u}px ${t.primary}55`,
					background: t.surface,
				}}
			>
				<Media visual={scene.visual} durationInFrames={scene.duration} />
			</div>
			{title ? <Words text={title} size={(L.landscape ? 72 : 84) * L.u} center delay={8} /> : null}
			<Para text={caption} center delay={14} />
		</Stage>
	);
};

type Focus = {at: number; x: number; y: number; scale: number};
type Click = {at: number; x: number; y: number};

// props: title?, device: "phone"|"laptop"|"none", focus?: Focus[] (at 0-1 of scene, x/y 0-1 of screenshot), clicks?: Click[]
export const ScreenDemo: React.FC<{scene: Scene}> = ({scene}) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	const t = useTheme();
	const L = useLayout();
	const {title, kicker} = scene.props;
	const device: string = scene.props.device ?? (L.landscape ? 'laptop' : 'phone');
	const focus: Focus[] = scene.props.focus ?? [{at: 0, x: 0.5, y: 0.5, scale: 1}];
	const clicks: Click[] = scene.props.clicks ?? [];
	const prog = frame / Math.max(1, scene.duration);

	// interpolate camera through focus keyframes
	const ats = focus.map((f) => f.at);
	const cam = (key: 'x' | 'y' | 'scale') =>
		focus.length === 1 ? focus[0][key] : interpolate(prog, ats, focus.map((f) => f[key]), {...clamp, easing: (v) => v * v * (3 - 2 * v)});
	const sc = cam('scale');
	const tx = (0.5 - cam('x')) * 100 * (sc - 1) / sc;
	const ty = (0.5 - cam('y')) * 100 * (sc - 1) / sc;

	const enter = pop(frame, fps, 0, 15);
	const titleH = title ? (L.landscape ? 130 : 130) * L.u : 0;
	const avail = L.bottom - L.top - titleH;
	const phone = device === 'phone';
	// phone ≈ 19.5:9 (matches capture_screens.py phone shots), laptop 16:10.5
	const frameH = phone ? Math.min(avail, (L.w - L.pad * 2) * 2.17) : Math.min(avail, (L.w - L.pad * 2) * 0.66);
	const frameW = phone ? frameH / 2.17 : frameH / 0.66;
	const bezel = (phone ? 18 : 10) * L.u;

	return (
		<Stage gap={34}>
			<Kicker text={kicker} center />
			{title ? <Words text={title} size={(L.landscape ? 68 : 76) * L.u} center /> : null}
			<div style={{display: 'flex', justifyContent: 'center'}}>
				<div
					style={{
						width: frameW,
						height: frameH,
						borderRadius: phone ? 64 * L.u : 22 * L.u,
						background: '#0B0F1A',
						padding: bezel,
						paddingTop: phone ? bezel : 46 * L.u,
						position: 'relative',
						transform: `translateY(${(1 - enter) * 120}px)`,
						opacity: enter,
						boxShadow: `0 ${40 * L.u}px ${100 * L.u}px rgba(0,0,0,0.5), 0 0 0 ${2 * L.u}px rgba(255,255,255,0.12)`,
					}}
				>
					{!phone ? (
						<div style={{position: 'absolute', top: 16 * L.u, left: 20 * L.u, display: 'flex', gap: 10 * L.u}}>
							{['#FF5F57', '#FEBC2E', '#28C840'].map((c) => (
								<div key={c} style={{width: 14 * L.u, height: 14 * L.u, borderRadius: 99, background: c}} />
							))}
						</div>
					) : null}
					<div style={{width: '100%', height: '100%', overflow: 'hidden', borderRadius: phone ? 48 * L.u : 8 * L.u, position: 'relative', background: '#FFFFFF'}}>
						<div style={{width: '100%', height: '100%', transform: `scale(${sc}) translate(${tx}%, ${ty}%)`}}>
							<Media visual={{...scene.visual, motion: 'static'}} durationInFrames={scene.duration} fit="cover" style={{objectPosition: 'top'}} />
						</div>
						{clicks.map((c, i) => {
							const start = c.at * scene.duration;
							const local = frame - start;
							if (local < -12 || local > 24) return null;
							const appear = ease(frame, start - 12, start);
							const ripple = interpolate(local, [0, 20], [0, 1], clamp);
							return (
								<div key={i} style={{position: 'absolute', left: `${c.x * 100}%`, top: `${c.y * 100}%`}}>
									<div
										style={{
											position: 'absolute',
											width: 120 * L.u,
											height: 120 * L.u,
											left: -60 * L.u,
											top: -60 * L.u,
											borderRadius: 999,
											border: `${5 * L.u}px solid ${t.primary}`,
											transform: `scale(${ripple})`,
											opacity: local >= 0 ? 1 - ripple : 0,
										}}
									/>
									<div
										style={{
											position: 'absolute',
											width: 44 * L.u,
											height: 44 * L.u,
											left: -22 * L.u,
											top: -22 * L.u,
											borderRadius: 999,
											background: `${t.primary}CC`,
											border: `${4 * L.u}px solid #FFFFFF`,
											opacity: appear,
											transform: `scale(${local >= 0 && local < 6 ? 0.8 : 1})`,
										}}
									/>
								</div>
							);
						})}
					</div>
				</div>
			</div>
		</Stage>
	);
};
