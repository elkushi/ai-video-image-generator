// StockBroll and StoryShot: full-bleed footage with an overlay line. Without media they become a motion card.
import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {Media, hasMedia} from '../components/Media';
import {Kicker, Stage, Words} from '../components/Text';
import {clamp} from '../lib/anim';
import {useLayout, useTheme} from '../lib/theme';
import type {Scene} from '../types';
import {st} from '../lib/stress';

// props: text?, kicker?, position?: "center"|"bottom"
export const StockBroll: React.FC<{scene: Scene}> = ({scene}) => {
	const t = useTheme();
	const L = useLayout();
	const {text, kicker, position} = scene.props;
	const media = hasMedia(scene.visual);
	return (
		<AbsoluteFill>
			{media ? (
				<AbsoluteFill>
					<Media visual={scene.visual} durationInFrames={scene.duration} />
					<AbsoluteFill style={{background: `linear-gradient(180deg, ${t.bg}88 0%, ${t.bg}22 35%, ${t.bg}CC 100%)`}} />
				</AbsoluteFill>
			) : null}
			{text || kicker ? (
				<Stage align={position === 'bottom' ? 'start' : 'center'} style={position === 'bottom' ? {justifyContent: 'flex-end'} : undefined}>
					<Kicker text={kicker} center={position !== 'bottom'} />
					{text ? <Words text={text} size={(L.landscape ? 88 : media ? 96 : 110) * L.u} center={position !== 'bottom'} /> : null}
				</Stage>
			) : null}
		</AbsoluteFill>
	);
};

// Cinematic shot for short films. props: text?, letterbox?: boolean, chapter?
export const StoryShot: React.FC<{scene: Scene}> = ({scene}) => {
	const frame = useCurrentFrame();
	const L = useLayout();
	const {text, letterbox, chapter} = scene.props;
	const bar = letterbox ? (L.landscape ? 0.1 : 0.07) * L.h : 0;
	const textIn = interpolate(frame, [8, 22], [0, 1], clamp);
	if (!hasMedia(scene.visual)) {
		// No image could be made (quota/offline): a branded motion card, never a black frame.
		return (
			<AbsoluteFill>
				<Stage>
					{chapter ? <Kicker text={chapter} center /> : null}
					<Words text={text || chapter || ' '} size={(L.landscape ? 96 : 112) * L.u} center />
				</Stage>
			</AbsoluteFill>
		);
	}
	return (
		<AbsoluteFill style={{background: '#000'}}>
			<Media visual={scene.visual} durationInFrames={scene.duration} />
			<AbsoluteFill style={{background: 'radial-gradient(ellipse at center, transparent 55%, rgba(0,0,0,0.55) 100%)'}} />
			{bar ? (
				<>
					<div style={{position: 'absolute', top: 0, left: 0, right: 0, height: bar, background: '#000'}} />
					<div style={{position: 'absolute', bottom: 0, left: 0, right: 0, height: bar, background: '#000'}} />
				</>
			) : null}
			{chapter ? (
				<div style={{position: 'absolute', top: L.top, left: L.pad, right: L.pad, textAlign: 'center', color: '#FFFFFF', opacity: textIn * 0.85, fontSize: 34 * L.u, letterSpacing: '0.3em', textTransform: 'uppercase', fontWeight: 600}}>
					{st(chapter)}
				</div>
			) : null}
			{text ? (
				// portrait: overlay line at the top so it never stacks on the captions
				<Stage style={{justifyContent: L.portrait ? 'flex-start' : 'flex-end'}}>
					<Words text={text} size={(L.landscape ? 70 : 80) * L.u} center color="#FFFFFF" weight={700} />
				</Stage>
			) : null}
		</AbsoluteFill>
	);
};
