// Shape of props.json written by tools/build_props.py. Keep both sides in sync.
import type {Caption} from '@remotion/captions';

export type FontSpec = {family: string; files?: Record<string, string>};

export type Brand = {
	name: string;
	tagline?: string;
	website?: string;
	handle?: string;
	colors: {
		primary: string;
		secondary: string;
		dark: string;
		light: string;
		accent: string;
		text_on_dark: string;
		text_on_light: string;
		muted: string;
		success?: string;
		danger?: string;
	};
	fonts: {heading: FontSpec; body: FontSpec};
	logo: {on_light?: string; on_dark?: string};
	radius?: number;
	motif?: 'tilted_squares' | 'circles' | 'grid' | 'none';
};

export type Visual = {
	source: string;
	resolved?: string | null; // path inside the run's public dir
	kind?: 'image' | 'video' | 'none';
	motion?: 'zoom_in' | 'zoom_out' | 'pan_left' | 'pan_right' | 'pan_up' | 'pan_down' | 'static';
	fallback_used?: string;
};

export type Scene = {
	id: string;
	type: string;
	vo?: string;
	from: number; // frame where this scene starts (voice timeline)
	duration: number; // frames until the next scene starts
	speechFrames?: number; // frames of actual speech in this scene
	transition?: 'fade' | 'slide' | 'zoom' | 'wipe' | 'none' | 'glitch' | 'light-leak' | 'rgb-split' | 'zoom-blur' | 'clock-wipe' | 'pixelate' | 'checkerboard';
	lottie?: {src: string; position?: string; size?: number; loop?: boolean};
	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	props: Record<string, any>;
	visual: Visual;
};

export type VideoProps = {
	title: string;
	language: 'en' | 'ar' | 'ru';
	dir: 'ltr' | 'rtl';
	theme: 'dark' | 'light' | 'brand';
	brand: Brand;
	brandBase: string; // public-dir prefix for brand files, e.g. "brand/"
	scenes: Scene[];
	totalFrames: number;
	transitionFrames: number;
	look?: {grain?: number; vignette?: number};
	voice: string | null;
	music: {src: string; underVoice: number; noVoice: number; fadeFrames: number} | null;
	voiceRanges: [number, number][];
	voiceLevels: number[]; // per-frame voice loudness 0-1 (mascot mouth)
	sfx?: {frame: number; src: string; volume: number}[]; // planned by build_props.py
	captions: Caption[];
	showCaptions: boolean;
	captionStyle: 'highlight' | 'pop' | 'minimal';
	progressBar: boolean;
	watermarkLogo: boolean;
};
