// Gantt timeline of real durations. Active bars grow live; a ghost bar shows the expected remaining time.
import {motion} from 'motion/react';
import {fmtSec} from '../lib/api';
import {NODE, nodeDef} from '../lib/nodes';
import type {PipelineState} from '../lib/pipeline';

export function expectedFor(id: string, timings?: Record<string, number>) {
	return timings?.[id] ?? NODE[id]?.expected ?? 30;
}

export function Timeline({s, timings, kind}: {s: PipelineState; timings?: Record<string, number>; kind?: string}) {
	const now = s.status === 'running' ? Date.now() : s.end ?? s.last ?? Date.now();
	const t0 = s.start ?? Object.values(s.nodes).reduce((m, n) => Math.min(m, n.start ?? Infinity), Infinity);
	const rows = s.order.filter((id) => NODE[id]);
	if (!rows.length || !isFinite(t0)) {
		return <div className="py-6 text-center text-sm text-ink-400">The timeline fills in as soon as the first agent starts.</div>;
	}
	let tEnd = now;
	for (const id of rows) {
		const n = s.nodes[id];
		if (n.status === 'active') {
			const left = id === 'render' && n.eta ? n.eta : Math.max(0, expectedFor(id, timings) - (now - (n.spans.at(-1)?.start ?? now)) / 1000);
			tEnd = Math.max(tEnd, now + left * 1000);
		}
	}
	const span = Math.max(30_000, tEnd - t0);
	const pct = (t: number) => ((t - t0) / span) * 100;
	const step = [10, 30, 60, 120, 300, 600, 1200].find((st) => span / 1000 / st <= 10) ?? 1800;
	const ticks = Array.from({length: Math.floor(span / 1000 / step) + 1}, (_, i) => i * step);

	return (
		<div className="relative">
			<div className="relative ml-[150px] h-5 border-b border-ink-700">
				{ticks.map((t) => (
					<span key={t} className="absolute -translate-x-1/2 font-mono text-[10px] text-ink-400" style={{left: `${(t * 1000 * 100) / span}%`}}>
						{fmtSec(t)}
					</span>
				))}
			</div>
			<div className="mt-1 space-y-1.5">
				{rows.map((id) => {
					const n = s.nodes[id];
					const def = nodeDef(id, kind)!;
					const active = n.status === 'active';
					const last = n.spans.at(-1);
					const left = active ? (id === 'render' && n.eta ? n.eta : Math.max(0, expectedFor(id, timings) - (now - (last?.start ?? now)) / 1000)) : 0;
					return (
						<div key={id} className="flex items-center">
							<div className="flex w-[150px] shrink-0 items-center gap-2 pr-3 text-[12px]">
								<span className="h-2 w-2 rounded-full" style={{background: def.color, boxShadow: active ? `0 0 10px ${def.color}` : 'none'}} />
								<span className={active ? 'font-semibold text-ink-100' : 'text-ink-300'}>{def.label}</span>
							</div>
							<div className="relative h-6 flex-1 rounded-md bg-ink-900">
								{ticks.map((t) => (
									<span key={t} className="absolute top-0 h-full w-px bg-ink-800" style={{left: `${(t * 1000 * 100) / span}%`}} />
								))}
								{n.spans.map((sp, i) => {
									const end = sp.end ?? now;
									return (
										<motion.div
											key={i}
											className={`absolute top-0.5 h-5 overflow-hidden rounded ${sp.end == null && active ? 'shimmer' : ''}`}
											style={{left: `${pct(sp.start)}%`, background: n.status === 'error' ? '#ff6b81' : def.color, opacity: sp.end == null ? 0.95 : 0.7}}
											initial={{width: 0}}
											animate={{width: `${Math.max(0.4, pct(end) - pct(sp.start))}%`}}
											transition={{duration: 0.4}}
										/>
									);
								})}
								{active && left > 0 && (
									<div
										className="absolute top-0.5 h-5 rounded border border-dashed"
										style={{left: `${pct(now)}%`, width: `${pct(now + left * 1000) - pct(now)}%`, borderColor: `${def.color}88`, background: `${def.color}12`}}
									/>
								)}
								<span className="absolute right-2 top-0.5 font-mono text-[11px] leading-5 text-ink-300">
									{fmtSec(n.spans.reduce((a, sp) => a + ((sp.end ?? now) - sp.start), 0) / 1000)}
									{active && left > 0 ? <span className="text-ink-400"> · ~{fmtSec(left)} left</span> : null}
									{id === 'render' && n.fps ? <span className="text-ink-400"> · {n.fps} fps</span> : null}
								</span>
							</div>
						</div>
					);
				})}
			</div>
			{s.status === 'running' && (
				<div className="pointer-events-none absolute bottom-0 top-5 ml-[150px] w-px bg-amber/70" style={{left: `calc(150px + (100% - 150px) * ${pct(now) / 100})`, marginLeft: 0}} />
			)}
		</div>
	);
}
