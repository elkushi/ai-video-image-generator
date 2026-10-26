// Folds the job's event stream into the state every live view renders (factory floor, graph, timeline).
import {NODE, normNode} from './nodes';
import type {Question} from './api';

export type FactoryEvent = {
	ts: number;
	job?: string;
	source: 'claude' | 'tool' | 'app';
	kind: string;
	node: string;
	run?: string | null;
	data: Record<string, any>;
};

export type NodeState = {
	id: string;
	status: 'idle' | 'active' | 'done' | 'error';
	start?: number;
	end?: number;
	spans: {start: number; end?: number}[];
	detail?: string; // latest activity line
	progress?: number; // 0..100
	eta?: number; // seconds left (render)
	fps?: number;
	fallback?: string;
	count: number;
};

export type Asset = {ts: number; node: string; type: string; path: string; scene?: string; provider?: string; comp?: string};
export type Thought = {ts: number; node: string; text: string};

export type PipelineState = {
	nodes: Record<string, NodeState>;
	order: string[]; // nodes in the order they first started
	active: string[];
	thoughts: Thought[];
	activity: {ts: number; node: string; tool: string; detail?: string; error?: string}[];
	assets: Asset[];
	renders: Record<string, {pct: number; frame: number; total: number; fps: number; eta: number; size?: number[]}>;
	fallbacks: {ts: number; node: string; scene?: string; to: string; reason?: string}[];
	checks: {video: string; checks: {name: string; ok: boolean; detail: string}[]}[];
	question: Question | null;
	usage: {turns: number; tokens: number};
	start?: number;
	end?: number;
	status: 'queued' | 'running' | 'waiting' | 'done' | 'error' | 'cancelled';
	error?: string;
	summary?: string;
	run?: string;
	output?: string;
	model?: string;
	auth?: string;
	pipeline?: {aspects?: string[]; scenes?: number; language?: string; title?: string};
	last: number;
};

export const emptyPipeline = (): PipelineState => ({
	nodes: {},
	order: [],
	active: [],
	thoughts: [],
	activity: [],
	assets: [],
	renders: {},
	fallbacks: [],
	checks: [],
	question: null,
	usage: {turns: 0, tokens: 0},
	status: 'queued',
	last: 0,
});

function node(s: PipelineState, id: string): NodeState {
	if (!s.nodes[id]) {
		s.nodes[id] = {id, status: 'idle', spans: [], count: 0};
	}
	return s.nodes[id];
}

function startNode(s: PipelineState, id: string, ts: number, detail?: string) {
	const n = node(s, id);
	if (!s.order.includes(id)) s.order.push(id);
	if (n.status !== 'active') {
		n.spans.push({start: ts});
		n.count += 1;
	}
	n.status = 'active';
	n.start = n.start ?? ts;
	n.end = undefined;
	if (detail) n.detail = detail;
}

function endNode(s: PipelineState, id: string, ts: number, ok = true) {
	const n = node(s, id);
	if (!s.order.includes(id)) s.order.push(id);
	const span = n.spans[n.spans.length - 1];
	if (span && span.end == null) span.end = ts;
	if (!span) n.spans.push({start: ts, end: ts});
	n.status = ok ? 'done' : 'error';
	n.end = ts;
	if (ok && n.progress != null) n.progress = 100;
}

export function applyEvent(s: PipelineState, e: FactoryEvent): PipelineState {
	const ts = e.ts * 1000;
	s.last = Math.max(s.last, ts);
	const d = e.data ?? {};
	const id = normNode(e.node);
	switch (e.kind) {
		case 'log':
			if (e.source === 'app' && d.started) {
				s.status = 'running';
				s.start = s.start ?? ts;
				s.question = null;
			}
			if (e.node === 'claude') {
				s.model = d.model ?? s.model;
				s.auth = d.auth ?? s.auth;
			}
			if (e.node === 'pipeline' && d.aspects) s.pipeline = d;
			if (e.node === 'deliver' && d.folder) s.output = String(d.folder).split('/').pop();
			break;
		case 'agent_start':
		case 'tool_start':
		case 'stage_start':
			if (id) startNode(s, id, ts, d.task || d.tool || d.command);
			break;
		case 'agent_end':
		case 'tool_end':
		case 'stage_end':
			if (id) {
				const ok = d.ok !== false && d.status !== 'error' && d.status !== 'failed';
				// a run_video stage can end while a child tool already closed it: only close what is open
				if (s.nodes[id]?.status === 'active' || e.kind !== 'stage_end') endNode(s, id, ts, ok);
				if (e.kind === 'agent_end' && d.summary) s.thoughts.push({ts, node: id, text: d.summary});
			}
			break;
		case 'progress': {
			if (!id) break;
			if (node(s, id).status !== 'active') startNode(s, id, ts);
			const n = node(s, id);
			if (id === 'render' && d.comp) {
				s.renders[d.comp] = {pct: d.pct ?? 0, frame: d.frame ?? 0, total: d.total ?? 0, fps: d.fps ?? 0, eta: d.eta ?? 0, size: d.size ?? s.renders[d.comp]?.size};
				const all = Object.values(s.renders);
				n.progress = all.reduce((a, r) => a + r.pct, 0) / all.length;
				n.eta = d.eta;
				n.fps = d.fps;
				n.detail = `${d.comp.replace('Video-', '')} · ${Math.round(d.pct ?? 0)}%`;
			} else if (d.n) {
				n.progress = ((d.i + 1) / d.n) * 100;
				n.detail = d.text ? `“${d.text}”` : d.scene;
			} else {
				n.detail = d.scene ? `${d.scene}${d.prompt ? ': ' + d.prompt : ''}` : n.detail;
			}
			break;
		}
		case 'asset':
			if (d.path) s.assets.push({ts, node: id ?? e.node, type: d.type, path: d.path, scene: d.scene, provider: d.provider, comp: d.comp});
			break;
		case 'fallback':
			s.fallbacks.push({ts, node: id ?? e.node, scene: d.scene, to: d.to, reason: d.reason});
			if (id) node(s, id).fallback = d.to;
			break;
		case 'check':
			s.checks = s.checks.filter((c) => c.video !== d.video).concat([{video: d.video, checks: d.checks ?? []}]);
			break;
		case 'thought': {
			const who = id ?? 'claude';
			s.thoughts.push({ts, node: who, text: d.text});
			if (s.thoughts.length > 300) s.thoughts.splice(0, s.thoughts.length - 300);
			break;
		}
		case 'activity': {
			s.activity.push({ts, node: e.node, tool: d.tool, detail: d.detail, error: d.error});
			if (s.activity.length > 400) s.activity.splice(0, s.activity.length - 400);
			const det = String(d.detail ?? '');
			if (d.tool === 'Write' || d.tool === 'Edit') {
				if (/post\.md$/.test(det)) {
					startNode(s, 'post', ts, 'writing post.md');
					endNode(s, 'post', ts + 1);
				}
			}
			if (id && NODE[id] && s.nodes[id]?.status === 'active') s.nodes[id].detail = `${d.tool}${det ? ' · ' + det : ''}`;
			break;
		}
		case 'question':
			s.question = {question: d.question, header: d.header ?? 'Question', options: d.options ?? [], multiSelect: d.multiSelect};
			break;
		case 'waiting':
			s.status = 'waiting';
			s.question = {question: d.question, header: d.header ?? 'Question', options: d.options ?? [], multiSelect: d.multiSelect};
			closeAll(s, ts);
			break;
		case 'answer':
			s.question = null;
			s.thoughts.push({ts, node: 'you', text: d.text});
			break;
		case 'usage':
			s.usage = {turns: s.usage.turns + (d.turns ?? 0), tokens: s.usage.tokens + (d.output_tokens ?? 0)};
			break;
		case 'done':
			s.status = d.status === 'cancelled' ? 'cancelled' : 'done';
			s.end = ts;
			s.summary = d.summary;
			if (d.output) s.output = d.output;
			closeAll(s, ts);
			break;
		case 'error':
			s.status = 'error';
			s.end = ts;
			s.error = d.error;
			closeAll(s, ts, false);
			break;
	}
	if (e.run) s.run = e.run;
	s.active = Object.values(s.nodes)
		.filter((n) => n.status === 'active')
		.map((n) => n.id);
	return s;
}

function closeAll(s: PipelineState, ts: number, ok = true) {
	for (const n of Object.values(s.nodes)) if (n.status === 'active') endNode(s, n.id, ts, ok);
}

export const nodeSeconds = (n?: NodeState, now = Date.now()) =>
	n ? n.spans.reduce((a, sp) => a + ((sp.end ?? (n.status === 'active' ? now : sp.start)) - sp.start), 0) / 1000 : 0;

// The node the "video box" should sit at: the most recently started active node, else the last finished one.
export function focusNode(s: PipelineState): string | null {
	const act = s.active.map((id) => s.nodes[id]).sort((a, b) => (b.start ?? 0) - (a.start ?? 0));
	if (act.length) {
		// prefer concrete tools over the umbrella agent while both run
		const tool = act.find((n) => NODE[n.id]?.kind === 'tool');
		return (tool ?? act[0]).id;
	}
	const done = Object.values(s.nodes).sort((a, b) => (b.end ?? 0) - (a.end ?? 0));
	return done[0]?.id ?? null;
}
