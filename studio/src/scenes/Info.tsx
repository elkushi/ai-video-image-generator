// FeatureList, StatCounter, BeforeAfter, Quote, EventCard.
import React from 'react';
import {Img, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {IconTile, Kicker, Para, Stage, Words} from '../components/Text';
import {clamp, ease, pop, stagger} from '../lib/anim';
import {useLayout, useTheme, useVideoProps} from '../lib/theme';
import type {Scene} from '../types';
import {st} from '../lib/stress';

const Card: React.FC<{children: React.ReactNode; style?: React.CSSProperties; enter: number; from?: 'up' | 'side'}> = ({children, style, enter, from = 'up'}) => {
	const t = useTheme();
	const L = useLayout();
	const side = (t.dir === 'rtl' ? -1 : 1) * (1 - enter) * 80;
	return (
		<div
			style={{
				background: t.surface,
				borderRadius: t.radius * L.u,
				padding: `${28 * L.u}px ${34 * L.u}px`,
				border: `${2 * L.u}px solid rgba(255,255,255,0.08)`,
				boxShadow: `0 ${18 * L.u}px ${50 * L.u}px rgba(0,0,0,0.25)`,
				opacity: enter,
				transform: from === 'up' ? `translateY(${(1 - enter) * 50}px)` : `translateX(${side}px)`,
				...style,
			}}
		>
			{children}
		</div>
	);
};

// props: title, kicker?, items: [{text, icon?, sub?}]
export const FeatureList: React.FC<{scene: Scene}> = ({scene}) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	const t = useTheme();
	const L = useLayout();
	const items: {text: string; icon?: string; sub?: string}[] = scene.props.items ?? [];
	const n = items.length;
	// spread items over the spoken part so each lands roughly as it is said
	const window = Math.max(20, (scene.speechFrames ?? scene.duration) * 0.8);
	const grid = L.landscape && n > 3;
	const fs = (L.landscape ? 42 : n > 4 ? 44 : 50) * L.u;
	return (
		<Stage gap={30}>
			<Kicker text={scene.props.kicker} />
			{scene.props.title ? <Words text={scene.props.title} size={(L.landscape ? 72 : 84) * L.u} /> : null}
			<div style={{display: grid ? 'grid' : 'flex', gridTemplateColumns: grid ? '1fr 1fr' : undefined, flexDirection: 'column', gap: 22 * L.u}}>
				{items.map((it, i) => {
					const e = pop(frame, fps, stagger(i, n, window, 10));
					return (
						<Card key={i} enter={e} from="side" style={{display: 'flex', alignItems: 'center', gap: 28 * L.u}}>
							<IconTile icon={it.icon} size={(L.landscape ? 76 : 88) * L.u} index={i} />
							<div>
								<div style={{fontFamily: t.heading, fontWeight: 700, fontSize: fs, lineHeight: 1.15}}>{st(it.text)}</div>
								{it.sub ? <div style={{fontSize: fs * 0.66, color: t.fgMuted, marginTop: 6 * L.u}}>{st(it.sub)}</div> : null}
							</div>
						</Card>
					);
				})}
			</div>
		</Stage>
	);
};

// props: value (number), label, prefix?, suffix?, decimals?, kicker?, source?
export const StatCounter: React.FC<{scene: Scene}> = ({scene}) => {
	const frame = useCurrentFrame();
	const t = useTheme();
	const L = useLayout();
	const {value, label, prefix = '', suffix = '', decimals = 0, kicker, source} = scene.props;
	const p = ease(frame, 4, Math.min(scene.duration * 0.6, 45));
	const v = Number(value) * p;
	const shown = v.toLocaleString(t.lang === 'ar' ? 'ar-EG' : t.lang === 'ru' ? 'ru-RU' : 'en-US', {
		minimumFractionDigits: decimals,
		maximumFractionDigits: decimals,
	});
	const size = (L.landscape ? 220 : 250) * L.u * (String(prefix + shown + suffix).length > 7 ? 0.72 : 1);
	return (
		<Stage gap={26}>
			<Kicker text={kicker} center />
			<div
				style={{
					textAlign: 'center',
					fontFamily: t.heading,
					fontWeight: 800,
					fontSize: size,
					lineHeight: 1,
					letterSpacing: '-0.04em',
					color: t.primary === t.bg ? '#FFFFFF' : t.accent,
					fontVariantNumeric: 'tabular-nums',
					transform: `scale(${0.85 + 0.15 * p})`,
				}}
			>
				{prefix}
				{shown}
				{suffix}
			</div>
			<Words text={label} size={(L.landscape ? 60 : 68) * L.u} center delay={10} weight={700} />
			{source ? <Para text={source} center delay={30} size={28 * L.u} /> : null}
		</Stage>
	);
};

// props: title?, before: {label, text}, after: {label, text}
export const BeforeAfter: React.FC<{scene: Scene}> = ({scene}) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	const t = useTheme();
	const L = useLayout();
	const {before, after, title} = scene.props;
	const half = (scene.speechFrames ?? scene.duration) * 0.45;
	const b = pop(frame, fps, 4);
	const a = pop(frame, fps, half);
	const strike = ease(frame, half - 8, half + 6);
	const fs = (L.landscape ? 46 : 52) * L.u;
	const box = (side: {label: string; text: string}, enter: number, good: boolean) => (
		<Card enter={enter} style={{flex: 1, background: good ? t.primary : t.surface, color: good ? t.onPrimary : t.fg}}>
			<div style={{fontSize: 30 * L.u, fontWeight: 700, letterSpacing: t.lang === 'ar' ? undefined : '0.12em', textTransform: t.lang === 'ar' ? undefined : 'uppercase', opacity: 0.8, marginBottom: 14 * L.u}}>
				{st(side.label)}
			</div>
			<div style={{fontFamily: t.heading, fontWeight: 700, fontSize: fs, lineHeight: 1.2, position: 'relative'}}>
				{st(side.text)}
				{!good ? (
					<div style={{position: 'absolute', left: 0, top: '52%', height: 6 * L.u, width: `${strike * 100}%`, background: '#EB5757', borderRadius: 9}} />
				) : null}
			</div>
		</Card>
	);
	return (
		<Stage gap={30}>
			{title ? <Words text={title} size={(L.landscape ? 70 : 80) * L.u} center /> : null}
			<div style={{display: 'flex', flexDirection: L.landscape ? 'row' : 'column', gap: 30 * L.u, opacity: interpolate(frame, [0, 4], [0, 1], clamp)}}>
				{box(before, b * (1 - 0.35 * strike), false)}
				{box(after, a, true)}
			</div>
		</Stage>
	);
};

// props: quote, author?, role?
export const Quote: React.FC<{scene: Scene}> = ({scene}) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	const t = useTheme();
	const L = useLayout();
	const {quote, author, role} = scene.props;
	const words = String(quote).split(/\s+/).length;
	return (
		<Stage gap={30}>
			<div style={{fontFamily: 'Georgia, serif', fontSize: 260 * L.u, lineHeight: 0.6, height: 120 * L.u, color: t.accent, opacity: pop(frame, fps, 0)}}>
				{t.dir === 'rtl' ? '”' : '“'}
			</div>
			<Words text={quote} size={(L.landscape ? 64 : words > 18 ? 62 : 74) * L.u} weight={700} perWord={2} lineHeight={1.2} />
			{author ? (
				<div style={{opacity: pop(frame, fps, 10 + words * 2), fontSize: 40 * L.u}}>
					<span style={{fontWeight: 800}}>{author}</span>
					{role ? <span style={{color: t.fgMuted}}>{` · ${role}`}</span> : null}
				</div>
			) : null}
		</Stage>
	);
};

const ICONS: Record<string, string> = {
	date: 'M7 2v3M17 2v3M3 9h18M5 5h14a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2z',
	time: 'M12 7v5l3 2M12 3a9 9 0 1 0 0 18a9 9 0 0 0 0-18z',
	location: 'M12 21s-7-6.2-7-12a7 7 0 0 1 14 0c0 5.8-7 12-7 12zM12 11.5a2.5 2.5 0 1 0 0-5a2.5 2.5 0 0 0 0 5z',
};

const LineIcon: React.FC<{name: string; size: number; color: string}> = ({name, size, color}) => (
	<svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
		<path d={ICONS[name]} />
	</svg>
);

// props: kicker?, title, date, time?, location?, speakers?: [{name, role?, photo?}], button?
export const EventCard: React.FC<{scene: Scene}> = ({scene}) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	const t = useTheme();
	const L = useLayout();
	const {brandBase} = useVideoProps();
	const {kicker, title, date, time, location, speakers = [], button} = scene.props;
	const chips = [
		{icon: 'date', text: date},
		{icon: 'time', text: time},
		{icon: 'location', text: location},
	].filter((c) => c.text);
	const fs = (L.landscape ? 38 : 44) * L.u;
	return (
		<Stage gap={30}>
			<Kicker text={kicker} />
			<Words text={title} size={(L.landscape ? 80 : 92) * L.u} />
			<div style={{display: 'flex', flexWrap: 'wrap', gap: 18 * L.u}}>
				{chips.map((c, i) => {
					const e = pop(frame, fps, 12 + i * 5);
					return (
						<div
							key={i}
							style={{
								opacity: e,
								transform: `translateY(${(1 - e) * 30}px)`,
								display: 'flex',
								alignItems: 'center',
								gap: 14 * L.u,
								background: t.surface,
								border: `${2 * L.u}px solid ${t.primary}`,
								borderRadius: 999,
								padding: `${14 * L.u}px ${28 * L.u}px`,
								fontSize: fs,
								fontWeight: 700,
							}}
						>
							<LineIcon name={c.icon} size={fs} color={t.accent} />
							{st(c.text)}
						</div>
					);
				})}
			</div>
			{speakers.length ? (
				<div style={{display: 'flex', flexDirection: L.landscape ? 'row' : 'column', gap: 20 * L.u}}>
					{speakers.slice(0, 3).map((s: {name: string; role?: string; photo?: string}, i: number) => {
						const e = pop(frame, fps, 24 + i * 6);
						return (
							<div key={i} style={{display: 'flex', alignItems: 'center', gap: 22 * L.u, opacity: e, transform: `translateY(${(1 - e) * 30}px)`}}>
								<div style={{width: 96 * L.u, height: 96 * L.u, borderRadius: 999, overflow: 'hidden', background: t.primary, flex: 'none', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: 40 * L.u, color: t.onPrimary}}>
									{s.photo ? <Img src={staticFile(brandBase + s.photo)} style={{width: '100%', height: '100%', objectFit: 'cover'}} /> : s.name.split(' ').map((p) => p[0]).slice(0, 2).join('')}
								</div>
								<div>
									<div style={{fontWeight: 800, fontSize: fs}}>{s.name}</div>
									{s.role ? <div style={{color: t.fgMuted, fontSize: fs * 0.75}}>{s.role}</div> : null}
								</div>
							</div>
						);
					})}
				</div>
			) : null}
			{button ? (
				<div style={{display: 'flex'}}>
					<div
						style={{
							opacity: pop(frame, fps, 34),
							background: t.primary === t.bg ? '#FFFFFF' : t.primary,
							color: t.primary === t.bg ? t.primary : t.onPrimary,
							fontFamily: t.heading,
							fontWeight: 800,
							fontSize: fs * 1.05,
							padding: `${20 * L.u}px ${48 * L.u}px`,
							borderRadius: 999,
						}}
					>
						{button}
					</div>
				</div>
			) : null}
		</Stage>
	);
};
