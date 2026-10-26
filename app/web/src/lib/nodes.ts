// The stations of the factory. Every event from the backend maps onto one of these ids.

export type NodeKind = 'agent' | 'tool' | 'claude';
export type NodeDef = {
	id: string;
	label: string;
	role: string; // one-line explanation shown on hover / in the graph
	kind: NodeKind;
	color: string;
	emoji: string;
	expected: number; // fallback seconds when there is no timing history yet
	col: number; // graph column
	row: number; // graph row (0 = agents, 1 = tools)
	optional?: boolean; // only shown when it actually ran
};

export const NODES: NodeDef[] = [
	{id: 'brand', label: 'Brand kit', role: 'Builds the brand kit from your uploads (onboard_brand.md)', kind: 'tool', color: '#5cb8ff', emoji: '🎨', expected: 90, col: 0, row: 1, optional: true},
	{id: 'planner', label: 'Content planner', role: 'Plans a series of videos (content-planner agent)', kind: 'agent', color: '#5cb8ff', emoji: '🗓️', expected: 120, col: 0, row: 0, optional: true},
	{id: 'intake', label: 'Run folder', role: 'Creates the run folder and copies the brand kit', kind: 'tool', color: '#7d89a8', emoji: '📁', expected: 2, col: 1, row: 1},
	{id: 'strategist', label: 'Strategist', role: 'Audience, angle, format, 3 hooks, CTA, platforms', kind: 'agent', color: '#9b7bff', emoji: '🧠', expected: 120, col: 1, row: 0},
	{id: 'scriptwriter', label: 'Scriptwriter', role: 'Writes the storyboard: voiceover, on-screen text, scenes', kind: 'agent', color: '#ff6b81', emoji: '✍️', expected: 180, col: 2, row: 0},
	{id: 'validate', label: 'Validator', role: 'Checks the storyboard contract and estimates length', kind: 'tool', color: '#a8b2cc', emoji: '✅', expected: 2, col: 2, row: 1},
	{id: 'voice', label: 'Voice booth', role: 'edge-tts neural voice with word timings (Piper offline)', kind: 'tool', color: '#34d3b4', emoji: '🎙️', expected: 40, col: 3, row: 1},
	{id: 'images', label: 'Image lab', role: 'AI stills: free FLUX → local Stable Diffusion → upscale', kind: 'tool', color: '#f5b942', emoji: '🖼️', expected: 300, col: 4, row: 1, optional: true},
	{id: 'clips', label: 'Motion lab', role: 'AI clips → local depth parallax → Ken Burns', kind: 'tool', color: '#f59e42', emoji: '🎞️', expected: 150, col: 5, row: 1, optional: true},
	{id: 'stock', label: 'Stock', role: 'Free stock footage (Pexels/Pixabay) or motion cards', kind: 'tool', color: '#a3e635', emoji: '📦', expected: 20, col: 4, row: 1, optional: true},
	{id: 'avatar', label: 'Presenter', role: 'Talking head (free GPU) or the animated mascot', kind: 'tool', color: '#e879f9', emoji: '🧑‍🏫', expected: 120, col: 5, row: 1, optional: true},
	{id: 'music', label: 'Music & SFX', role: 'Royalty-free library or the built-in synth bed + sound effects', kind: 'tool', color: '#5cb8ff', emoji: '🎵', expected: 5, col: 6, row: 1},
	{id: 'props', label: 'Assembly', role: 'Captions, voice levels and SFX timing for Remotion', kind: 'tool', color: '#a8b2cc', emoji: '🧩', expected: 3, col: 7, row: 1},
	{id: 'render', label: 'Render oven', role: 'Remotion renders every aspect ratio on the CPU', kind: 'tool', color: '#ff8a3d', emoji: '🔥', expected: 120, col: 8, row: 1},
	{id: 'qa', label: 'QA scanner', role: 'Contact sheet, loudness, black frames, Whisper transcript', kind: 'tool', color: '#34d3b4', emoji: '🔍', expected: 35, col: 9, row: 1},
	{id: 'qa-reviewer', label: 'QA director', role: 'Judges the frames, transcript and hook: SHIP or FIX', kind: 'agent', color: '#34d3b4', emoji: '🧐', expected: 90, col: 9, row: 0},
	{id: 'designer', label: 'Motion designer', role: 'Fixes or builds Remotion scenes when needed', kind: 'agent', color: '#e879f9', emoji: '🛠️', expected: 200, col: 7, row: 0, optional: true},
	{id: 'deliver', label: 'Shipping', role: 'Loudness −14 LUFS, covers, delivery to output/', kind: 'tool', color: '#f5b942', emoji: '🚚', expected: 6, col: 10, row: 1},
	{id: 'post-copywriter', label: 'Copywriter', role: 'Writes 3 angles: hook, copy per platform, alt text', kind: 'agent', color: '#ff6b81', emoji: '✍️', expected: 150, col: 1, row: 0, optional: true},
	{id: 'post-designer', label: 'Designer', role: 'Turns each angle into on-brand slides (HyperFrames)', kind: 'agent', color: '#e879f9', emoji: '🎨', expected: 180, col: 2, row: 0, optional: true},
	{id: 'post', label: 'Copywriter', role: 'Writes post.md: LinkedIn post, Instagram caption, alt text', kind: 'claude', color: '#f5b942', emoji: '📝', expected: 60, col: 10, row: 0},
];

export const NODE = Object.fromEntries(NODES.map((n) => [n.id, n])) as Record<string, NodeDef>;

// The stations each job kind always shows (others appear only when they actually run).
export const KIND_NODES: Record<string, string[]> = {
	video: ['strategist', 'scriptwriter', 'validate', 'voice', 'music', 'props', 'render', 'qa', 'qa-reviewer', 'deliver', 'post'],
	series: ['strategist', 'scriptwriter', 'validate', 'voice', 'music', 'props', 'render', 'qa', 'qa-reviewer', 'deliver', 'post'],
	onboard: ['brand', 'strategist', 'scriptwriter', 'validate', 'voice', 'music', 'props', 'render', 'qa', 'qa-reviewer', 'deliver', 'post'],
	brand: ['brand'],
	revise: ['scriptwriter', 'validate', 'voice', 'props', 'render', 'qa', 'qa-reviewer', 'deliver'],
	post: ['intake', 'post-copywriter', 'post-designer', 'validate', 'render', 'qa-reviewer', 'deliver'],
	calendar: ['planner'],
	performance: [],
};
export const nodesFor = (kind: string) => KIND_NODES[kind] ?? KIND_NODES.video;

// Same node, different wording per job kind (posts render stills with HyperFrames, not Remotion video).
const KIND_LABELS: Record<string, Record<string, Partial<Pick<NodeDef, 'label' | 'role' | 'emoji'>>>> = {
	post: {
		render: {label: 'HyperFrames', role: 'Renders every variant to on-brand PNG slides (HTML → image)'},
		validate: {role: 'Checks post.json: layouts, text length, brand rules, facts'},
		intake: {label: 'Post folder', role: 'Creates the post folder and the brief'},
		'qa-reviewer': {role: 'Judges the 3 variants for legibility, contrast, brand fit'},
		deliver: {role: 'PNGs, carousel PDF, post copy in output/'},
		images: {role: 'AI photo for photo slides: free FLUX → local Stable Diffusion'},
	},
};
export const nodeDef = (id: string, kind?: string): NodeDef | undefined => {
	const base = NODE[id];
	if (!base) return undefined;
	const o = kind ? KIND_LABELS[kind]?.[id] : undefined;
	return o ? {...base, ...o} : base;
};

// Stage names from tools/run_video.py that aren't nodes themselves
export const STAGE_ALIASES: Record<string, string | null> = {
	validate: 'validate',
	voice: 'voice',
	assets: null,
	props: 'props',
	preview: 'render',
	final: 'render',
	sfx: 'music',
	pipeline: null,
	test: null,
	setup: null,
	agent: null,
	claude: null,
	app: null,
};

export const normNode = (n: string): string | null => {
	if (n in STAGE_ALIASES) return STAGE_ALIASES[n];
	return NODE[n] ? n : null;
};
