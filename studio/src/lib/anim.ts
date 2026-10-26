// Small animation helpers. Everything is frame-driven (no CSS transitions — they don't render).
import {Easing, interpolate, spring} from 'remotion';

export const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

// 0 -> 1 spring that starts at `delay` frames.
export const pop = (frame: number, fps: number, delay = 0, damping = 18) =>
	spring({frame: frame - delay, fps, config: {damping, stiffness: 140, mass: 0.8}});

// Eased 0 -> 1 progress between two frames.
export const ease = (frame: number, start: number, end: number) =>
	interpolate(frame, [start, end], [0, 1], {...clamp, easing: Easing.bezier(0.22, 1, 0.36, 1)});

// Slide-up + fade entrance; returns a style object.
export const rise = (frame: number, fps: number, delay = 0, distance = 40) => {
	const p = pop(frame, fps, delay);
	return {opacity: interpolate(p, [0, 1], [0, 1], clamp), transform: `translateY(${(1 - p) * distance}px)`};
};

// Stagger delay so N items finish appearing within `window` frames.
export const stagger = (i: number, n: number, window: number, start = 6) =>
	start + (n <= 1 ? 0 : (i * Math.max(0, window - start)) / n);

const RTL_CHARS = /[֐-ࣿיִ-﷿ﹰ-﻿]/;

export const isRtlText = (text: string) => {
	const words = text.split(/\s+/).filter(Boolean);
	return words.filter((w) => RTL_CHARS.test(w)).length > words.length / 2;
};

// Word-animated text puts each word in its own inline-block, which the browser lays out in the
// line's direction. Inside an RTL line that reverses Latin phrases ("Margin Notes" -> "Notes Margin").
// So in RTL, consecutive non-RTL words are grouped into one LTR run. Returns [start, end) index ranges.
export const bidiRuns = (words: string[], rtl: boolean): [number, number][] => {
	const runs: [number, number][] = [];
	words.forEach((w, i) => {
		const last = runs[runs.length - 1];
		if (rtl && last && last[1] === i && !RTL_CHARS.test(w) && !RTL_CHARS.test(words[i - 1])) last[1] = i + 1;
		else runs.push([i, i + 1]);
	});
	return runs;
};
