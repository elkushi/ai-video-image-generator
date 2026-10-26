// Fonts are loaded from local files only (offline-safe, no Google requests at render time):
//  - brand fonts:     <run public>/brand/fonts/*   (from brands/<slug>/fonts, copied by new_project.py)
//  - fallback fonts:  <run public>/fonts/Inter-*.ttf (Latin + Cyrillic) and Cairo-*.ttf (Arabic)
//    copied from assets/fonts/ by new_project.py / build_props.py
import {loadFont as loadLocal} from '@remotion/fonts';
import {staticFile} from 'remotion';
import type {Brand} from '../types';

const WEIGHTS = ['400', '500', '600', '700', '800'];
const loaded = new Set<string>();

const load = (family: string, url: string, weight: string) => {
	const key = `${family}-${weight}`;
	if (loaded.has(key)) return;
	loaded.add(key);
	loadLocal({family, url, weight}).catch((e) => console.warn(`font ${key} failed`, e));
};

export const loadBrandFonts = (brand: Brand, base: string) => {
	for (const fam of ['Inter', 'Cairo']) {
		for (const w of WEIGHTS) load(fam, staticFile(`fonts/${fam}-${w}.ttf`), w);
	}
	for (const spec of [brand.fonts.heading, brand.fonts.body]) {
		for (const [weight, file] of Object.entries(spec.files ?? {})) load(spec.family, staticFile(base + file), weight);
	}
};

// Arabic text gets Cairo first so letters always join; Latin/Cyrillic fall back to Inter for missing glyphs.
export const fontStack = (family: string, language: string) =>
	language === 'ar' ? `Cairo, "${family}", Inter, sans-serif` : `"${family}", Inter, Cairo, sans-serif`;
