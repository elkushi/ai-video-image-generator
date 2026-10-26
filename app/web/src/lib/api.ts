// Thin typed client for the FastAPI backend (app/server/main.py).
import {toast} from './toast';

export type Brand = {
	slug: string;
	name: string;
	tagline: string;
	colors: Record<string, string>;
	fonts: Record<string, string>;
	logo: string | null;
	logo_dark: string | null;
	voices: Record<string, string>;
	website: string;
	videos: number;
	posts?: number;
	assets: number;
};

export type QuestionOption = {label: string; description?: string};
export type Question = {question: string; header: string; options: QuestionOption[]; multiSelect?: boolean};
export type Intake = {understood: string; questions: Question[]; defaults?: Record<string, unknown>};

export type Job = {
	id: string;
	kind: string;
	// explicit purpose: video | series | onboard-video | post | post-revise | brand-new | brand-guide | revise | performance | calendar
	flow?: string;
	title: string;
	brand: string;
	status: 'queued' | 'running' | 'waiting' | 'done' | 'error' | 'cancelled';
	created: number;
	started?: number;
	ended?: number;
	run?: string;
	output?: string;
	question?: Question | null;
	usage?: {turns?: number; seconds?: number; output_tokens?: number; input_tokens?: number; denials?: string[]};
	result?: unknown;
	error?: string;
	meta?: Record<string, unknown>;
	queue_position?: number;
};

export type Check = {name: string; ok: boolean; detail: string};
export type QaReport = {
	video: string;
	size: [number, number];
	duration: number;
	lufs: number | null;
	contact_sheet: string | null;
	fallbacks: string[];
	asr?: {id: string; match: number; heard: string}[];
	checks: Check[];
};
export type OutputVideo = {aspect: string; path: string; cover: string | null};
export type Output = {
	name: string;
	kind?: 'video' | 'post';
	images?: string[];
	cover?: string | null;
	pdf?: string | null;
	aspect?: string;
	angle?: string;
	platforms?: string[];
	date: string;
	brand: string;
	title: string;
	language?: string;
	goal?: string;
	format?: string;
	videos: OutputVideo[];
	duration: number | null;
	qa: {pass: number; total: number};
	has_post: boolean;
	has_stats: boolean;
	smoke: boolean;
};
export type OutputDetail = Output & {
	qa_reports: QaReport[];
	post: {title: string; text: string}[];
	post_md: string;
	credits: string;
	strategy: string;
	brief: string;
	storyboard: {scenes?: {id: string; type: string; vo?: string}[]; [k: string]: unknown} | null;
	stats: Record<string, unknown>[];
	post_spec?: PostSpec | null;
};

// ---- social posts (3 variants rendered by HyperFrames, the user picks one) ----
export type PostPlatform = 'linkedin' | 'instagram' | 'facebook' | 'x' | 'tiktok';
export type PostCopy = Partial<Record<PostPlatform, string>> & {hashtags?: string[]; alt: string};
export type PostSlide = {layout: string; theme?: string; props: Record<string, unknown>};
export type PostVariant = {id: string; angle: string; why?: string; format: 'single' | 'carousel'; theme?: string; copy: PostCopy; slides: PostSlide[]};
export type PostSpec = {
	brand: string;
	topic: string;
	goal?: string;
	language: string;
	aspect: string;
	platforms: string[];
	posting_time?: string;
	picked?: string;
	variants: PostVariant[];
};
export type PostPreview = {angle: string; format: string; slides: string[]; motion?: string};
export type PostRun = {
	name: string;
	run: string;
	spec: PostSpec;
	previews: Record<string, PostPreview | string | undefined>;
	picked: string | null;
	output: string | null;
};
export type PostJobResult = {run?: string; summary?: string; variants?: {id: string; angle: string; why?: string}[]};
export const postPreview = (p: PostRun, id: string) => {
	const v = p.previews[id];
	return v && typeof v === 'object' ? v : null;
};
export const runName = (run?: string | null) => (run ? run.split('/').filter(Boolean).pop() ?? '' : '');
export type CalendarItem = {
	id: string;
	date: string;
	time?: string;
	goal: string;
	format: string;
	topic: string;
	hook: string;
	facts?: string[];
	languages: string[];
	aspects: string[];
	style?: string;
	length_s?: number;
	cta?: string;
	status?: string;
	runs?: string[];
};

export const file = (path?: string | null) => (path ? `/files/${path.split('/').map(encodeURIComponent).join('/')}` : '');

async function req<T>(method: string, url: string, body?: unknown): Promise<T> {
	const r = await fetch(url, {
		method,
		headers: body instanceof FormData || body === undefined ? undefined : {'content-type': 'application/json'},
		body: body instanceof FormData ? body : body === undefined ? undefined : JSON.stringify(body),
	});
	if (!r.ok) {
		let msg = `${r.status} ${r.statusText}`;
		try {
			const j = await r.json();
			msg = j.detail ?? j.error ?? msg;
		} catch {
			/* not json */
		}
		const text = typeof msg === 'string' ? msg : JSON.stringify(msg);
		if (r.status === 400 || r.status === 404 || r.status === 409) {
			const what = r.status === 404 ? 'Not found' : r.status === 409 ? 'Busy' : 'Check the input';
			toast(`⚠️ ${what}: ${text}`, r.status === 409 ? '#f5b942' : '#ff6b81');
		}
		throw new Error(text);
	}
	return r.json();
}

export const api = {
	brands: () => req<Brand[]>('GET', '/api/brands'),
	brand: (slug: string) =>
		req<{slug: string; kit: Record<string, unknown>; logo: string | null; profile: string; performance: string; calendar: {items: CalendarItem[]} | null; assets: string[]}>(
			'GET',
			`/api/brands/${slug}`,
		),
	outputs: () => req<Output[]>('GET', '/api/outputs'),
	output: (name: string) => req<OutputDetail>('GET', `/api/outputs/${name}`),
	jobs: () => req<Job[]>('GET', '/api/jobs'),
	job: (id: string) => req<Job>('GET', `/api/jobs/${id}`),
	cancel: (id: string) => req<Job>('POST', `/api/jobs/${id}/cancel`),
	answer: (id: string, text: string) => req<Job>('POST', `/api/jobs/${id}/answer`, {text}),
	intake: (brief: unknown) => req<{data: Intake; seconds: number}>('POST', '/api/intake/questions', brief),
	makeVideo: (brief: unknown) => req<Job>('POST', '/api/jobs/video', brief),
	makePost: (brief: unknown) => req<Job>('POST', '/api/jobs/post', brief),
	post: (name: string) => req<PostRun>('GET', `/api/posts/${name}`),
	pickPost: (name: string, body: {variant: string; copy?: Partial<PostCopy>}) => req<{output: string; files: string[]}>('POST', `/api/posts/${name}/pick`, body),
	revisePost: (name: string, body: {feedback: string; variants?: string[]}) => req<Job>('POST', `/api/posts/${name}/revise`, body),
	createBrand: (body: {name: string; website?: string; notes?: string; uploads?: string[]; language?: string}) => req<Job>('POST', '/api/brands', body),
	brandGuide: (slug: string, body: {uploads: string[]; notes?: string}) => req<Job>('POST', `/api/brands/${slug}/guide`, body),
	revise: (name: string, feedback: string) => req<Job>('POST', `/api/outputs/${name}/revise`, {feedback}),
	addStats: (name: string, stats: unknown) => req<unknown[]>('POST', `/api/outputs/${name}/stats`, stats),
	learn: (slug: string) => req<Job>('POST', `/api/brands/${slug}/performance`),
	planCalendar: (slug: string, body: unknown) => req<Job>('POST', `/api/brands/${slug}/calendar/plan`, body),
	approveCalendar: (slug: string, items: CalendarItem[]) => req<{items: CalendarItem[]}>('POST', `/api/brands/${slug}/calendar/approve`, {items}),
	timings: () =>
		req<{median_s: Record<string, number>; per_video_second: Record<string, number>; post_median_s?: Record<string, number>; post_samples?: Record<string, number>}>('GET', '/api/timings'),
	system: () =>
		req<{claude: string; ram_total_mb: number; ram_free_mb: number; disk_free_gb: number; running: string | null; queued: number; local_models: Record<string, boolean>}>(
			'GET',
			'/api/system',
		),
	upload: (files: File[], draft: string) => {
		const fd = new FormData();
		files.forEach((f) => fd.append('files', f));
		return req<{draft: string; files: {name: string; path: string; size: number; type: string}[]}>('POST', `/api/uploads?draft=${draft}`, fd);
	},
};

export const fmtSec = (s?: number | null) => {
	if (s == null || !isFinite(s)) return '–';
	s = Math.max(0, Math.round(s));
	if (s < 60) return `${s}s`;
	const m = Math.floor(s / 60);
	if (m < 60) return `${m}m ${String(s % 60).padStart(2, '0')}s`;
	return `${Math.floor(m / 60)}h ${String(m % 60).padStart(2, '0')}m`;
};

export const isRtl = (t?: string) => !!t && /[֐-ࣿ]/.test(t);
