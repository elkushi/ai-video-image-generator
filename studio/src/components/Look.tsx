// Finishing layers: film grain + vignette (from claude-code-video-toolkit, MIT) and Lottie stickers.
import {Lottie, type LottieAnimationData} from '@remotion/lottie';
import React, {useEffect, useState} from 'react';
import {AbsoluteFill, cancelRender, continueRender, delayRender, staticFile, useCurrentFrame} from 'remotion';

export const FilmGrain: React.FC<{opacity?: number}> = ({opacity = 0.05}) => {
	const seed = useCurrentFrame() % 100;
	return (
		<AbsoluteFill style={{opacity, mixBlendMode: 'overlay', pointerEvents: 'none'}}>
			<svg width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
				<filter id={`grain-${seed}`}>
					<feTurbulence type="fractalNoise" baseFrequency="0.65" numOctaves="3" seed={seed} stitchTiles="stitch" />
				</filter>
				<rect width="100%" height="100%" filter={`url(#grain-${seed})`} />
			</svg>
		</AbsoluteFill>
	);
};

export const Vignette: React.FC<{intensity?: number; centerSize?: number}> = ({intensity = 0.4, centerSize = 50}) => (
	<AbsoluteFill style={{background: `radial-gradient(ellipse at center, transparent ${centerSize}%, rgba(0,0,0,${intensity}) 100%)`, pointerEvents: 'none'}} />
);

const POS: Record<string, React.CSSProperties> = {
	center: {left: '50%', top: '50%', transform: 'translate(-50%, -50%)'},
	top: {left: '50%', top: '18%', transform: 'translateX(-50%)'},
	bottom: {left: '50%', bottom: '24%', transform: 'translateX(-50%)'},
	'top-right': {right: '7%', top: '16%'},
	'top-left': {left: '7%', top: '16%'},
	'bottom-right': {right: '7%', bottom: '24%'},
	'bottom-left': {left: '7%', bottom: '24%'},
};

// A Lottie animation (.json, e.g. a free one from LottieFiles) placed over a scene.
export const LottieSticker: React.FC<{src: string; position?: string; size?: number; loop?: boolean}> = ({src, position = 'top-right', size = 28, loop = true}) => {
	const [handle] = useState(() => delayRender(`lottie ${src}`));
	const [data, setData] = useState<LottieAnimationData | null>(null);
	useEffect(() => {
		fetch(staticFile(src))
			.then((r) => r.json())
			.then((j) => {
				setData(j);
				continueRender(handle);
			})
			.catch((e) => cancelRender(e));
	}, [handle, src]);
	if (!data) return null;
	return (
		<div style={{position: 'absolute', width: `${size}%`, aspectRatio: '1', pointerEvents: 'none', ...POS[position]}}>
			<Lottie animationData={data} loop={loop} />
		</div>
	);
};
