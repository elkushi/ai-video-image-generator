// Brand theme + responsive layout shared by every scene.
import React, {createContext, useContext} from 'react';
import {staticFile, useVideoConfig} from 'remotion';
import type {VideoProps} from '../types';
import {fontStack} from './fonts';

export type Theme = {
	bg: string;
	surface: string;
	fg: string;
	fgMuted: string;
	primary: string;
	secondary: string;
	accent: string;
	onPrimary: string;
	pill: string; // fill for chips, caption highlight, icon tiles (visible on bg)
	radius: number;
	heading: string;
	body: string;
	dir: 'ltr' | 'rtl';
	lang: string;
	logo: string | null; // logo that reads on bg
	logoOnPrimary: string | null;
	motif: string;
	brandName: string;
	website: string;
	handle: string;
};

const Ctx = createContext<{theme: Theme; props: VideoProps} | null>(null);

const mix = (hex: string, other: string, t: number) => {
	const p = (h: string) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
	const a = p(hex);
	const b = p(other);
	const c = a.map((v, i) => Math.round(v + (b[i] - v) * t));
	return `rgb(${c[0]}, ${c[1]}, ${c[2]})`;
};

export const makeTheme = (props: VideoProps): Theme => {
	const {colors: c, logo} = props.brand;
	const file = (p?: string) => (p ? staticFile(props.brandBase + p) : null);
	const darkLogo = file(logo.on_dark) ?? file(logo.on_light);
	const lightLogo = file(logo.on_light) ?? file(logo.on_dark);
	const base = {
		primary: c.primary,
		secondary: c.secondary,
		accent: c.accent,
		onPrimary: '#FFFFFF',
		pill: c.primary,
		radius: props.brand.radius ?? 24,
		heading: fontStack(props.brand.fonts.heading.family, props.language),
		body: fontStack(props.brand.fonts.body.family, props.language),
		dir: props.dir,
		lang: props.language,
		logoOnPrimary: darkLogo,
		motif: props.brand.motif ?? 'tilted_squares',
		brandName: props.brand.name,
		website: props.brand.website ?? '',
		handle: props.brand.handle ?? '',
	};
	if (props.theme === 'light') {
		return {...base, bg: c.light, surface: '#FFFFFF', fg: c.text_on_light, fgMuted: c.muted, logo: lightLogo};
	}
	if (props.theme === 'brand') {
		return {
			...base,
			bg: c.primary,
			pill: c.secondary,
			surface: mix(c.primary, '#000000', 0.18),
			fg: '#FFFFFF',
			fgMuted: mix(c.primary, '#FFFFFF', 0.7),
			accent: '#FFFFFF',
			logo: darkLogo,
		};
	}
	return {
		...base,
		bg: c.dark,
		surface: mix(c.dark, '#FFFFFF', 0.08),
		fg: c.text_on_dark,
		fgMuted: mix(c.dark, '#FFFFFF', 0.62),
		logo: darkLogo,
	};
};

export const ThemeProvider: React.FC<{props: VideoProps; children: React.ReactNode}> = ({props, children}) => (
	<Ctx.Provider value={{theme: makeTheme(props), props}}>{children}</Ctx.Provider>
);

export const useTheme = () => {
	const v = useContext(Ctx);
	if (!v) throw new Error('useTheme outside ThemeProvider');
	return v.theme;
};

export const useVideoProps = () => {
	const v = useContext(Ctx);
	if (!v) throw new Error('useVideoProps outside ThemeProvider');
	return v.props;
};

export type Layout = {
	u: number; // 1 unit = 1px on a 1080-wide portrait/square canvas
	w: number;
	h: number;
	portrait: boolean;
	landscape: boolean;
	pad: number; // side padding
	top: number; // top of the content box
	bottom: number; // bottom of the content box (captions live below it)
	captionY: number; // vertical centre of the caption block
};

// Safe zones: Reels/TikTok UI covers ~220px at the top and ~380px at the bottom of 1080x1920.
export const useLayout = (captionsOn = true): Layout => {
	const {width: w, height: h} = useVideoConfig();
	const portrait = h / w > 1.5;
	const landscape = w / h > 1.3;
	// 16:9 is watched small in feeds: scale type up 20% relative to its height
	const u = (Math.min(w, h) / 1080) * (landscape ? 1.2 : 1);
	if (portrait) {
		return {u, w, h, portrait, landscape, pad: 80 * u, top: 330 * u, bottom: h - (captionsOn ? 640 : 420) * u, captionY: h - 520 * u};
	}
	if (landscape) {
		return {u, w, h, portrait, landscape, pad: 150 * u, top: 70 * u, bottom: h - (captionsOn ? 200 : 70) * u, captionY: h - 115 * u};
	}
	const tall = h > w * 1.1; // 4:5
	return {u, w, h, portrait, landscape, pad: 80 * u, top: 90 * u, bottom: h - (captionsOn ? (tall ? 270 : 230) : 90) * u, captionY: h - (tall ? 150 : 130) * u};
};
