// Scene registry: storyboard "type" -> component. Add new scenes here (see .claude/agents/remotion-motion-designer.md).
import type React from 'react';
import type {Scene} from '../types';
import {StockBroll, StoryShot} from './Footage';
import {BeforeAfter, EventCard, FeatureList, Quote, StatCounter} from './Info';
import {Presenter} from './Presenter';
import {ProductHero, ScreenDemo} from './Product';
import {CTAEndCard, KineticTitle, LogoReveal} from './Titles';

export const SCENES: Record<string, React.FC<{scene: Scene}>> = {
	KineticTitle,
	LogoReveal,
	ProductHero,
	ScreenDemo,
	FeatureList,
	StatCounter,
	BeforeAfter,
	Quote,
	EventCard,
	StockBroll,
	StoryShot,
	Presenter,
	CTAEndCard,
};
