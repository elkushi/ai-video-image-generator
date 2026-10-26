// Cinematic scene transitions, from claude-code-video-toolkit (MIT, Digital Samba), lib/transitions.
// Each file exports a factory returning a @remotion/transitions TransitionPresentation. Video.tsx applies the
// component only during the T-frame overlap: entering (scene start) or exiting (scene end).
import type {TransitionPresentation} from '@remotion/transitions';
import {checkerboard} from './checkerboard';
import {clockWipe} from './clock-wipe';
import {glitch} from './glitch';
import {lightLeak} from './light-leak';
import {pixelate} from './pixelate';
import {rgbSplit} from './rgb-split';
import {zoomBlur} from './zoom-blur';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const FX: Record<string, () => TransitionPresentation<any>> = {
	glitch: () => glitch({}),
	'light-leak': () => lightLeak({}),
	'rgb-split': () => rgbSplit({}),
	'zoom-blur': () => zoomBlur({}),
	'clock-wipe': () => clockWipe({}),
	pixelate: () => pixelate({}),
	checkerboard: () => checkerboard({}),
};
