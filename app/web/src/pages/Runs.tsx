// Live run view (factory floor / graph + timeline + feed) and the list of runs.
import {AnimatePresence, motion} from 'motion/react';
import {useEffect, useState} from 'react';
import {Link, useParams} from 'react-router-dom';
import {answerText, Empty, QuestionCards, StatusPill, type AnswerMap} from '../components/ui';
import {FactoryFloor} from '../live/FactoryFloor';
import {PipelineGraph} from '../live/PipelineGraph';
import {expectedFor, Timeline} from '../live/Timeline';
import {api, file, fmtSec, isRtl, type Job, type PostJobResult} from '../lib/api';
import {VariantPicker} from '../components/VariantPicker';
import {NODE, nodeDef} from '../lib/nodes';
import type {PipelineState} from '../lib/pipeline';
import {useJob} from '../lib/useJob';
import {stationsFor} from '../live/FactoryFloor';

// Post jobs render stills with HyperFrames, so their stage medians come from past post runs.
const POST_TIMED = ['render', 'validate', 'images', 'deliver'];
// first-run guesses until there is post history (HyperFrames: ~40 s for 3 variants)
const POST_DEFAULT_S: Record<string, number> = {render: 60, images: 60, validate: 2, deliver: 3, intake: 2};
function useTimings(kind: string) {
	const [r, setR] = useState<Awaited<ReturnType<typeof api.timings>> | null>(null);
	useEffect(() => {
		api.timings().then(setR).catch(() => {});
	}, []);
	if (kind !== 'post') return r?.median_s ?? {};
	const base = Object.fromEntries(Object.entries(r?.median_s ?? {}).filter(([k]) => !POST_TIMED.includes(k)));
	return {...POST_DEFAULT_S, ...base, ...(r?.post_median_s ?? {})};
}

function overallEta(s: PipelineState, kind: string, timings: Record<string, number>) {
	if (s.status !== 'running') return null;
	const now = Date.now();
	let left = 0;
	for (const id of stationsFor(kind, s)) {
		const n = s.nodes[id];
		if (!n) left += NODE[id].optional ? 0 : expectedFor(id, timings);
		else if (n.status === 'active') left += id === 'render' && n.eta ? n.eta : Math.max(5, expectedFor(id, timings) - (now - (n.spans.at(-1)?.start ?? now)) / 1000);
	}
	return left;
}

export default function RunPage() {
	const {id} = useParams();
	const {s, job} = useJob(id);
	const [view, setView] = useState<'factory' | 'graph'>('factory');
	const [answers, setAnswers] = useState<AnswerMap>({});
	const [free, setFree] = useState('');
	const [showLog, setShowLog] = useState(false);
	const rawKind = job?.kind ?? 'video';
	// brand-only onboarding (Brands page) shows just the brand stations, not the video line
	const brandOnly = job?.flow ? job.flow === 'brand-new' || job.flow === 'brand-guide' : /^(New brand|Update brand from guide):/.test(job?.title ?? '');
	const kind = rawKind === 'onboard' && brandOnly ? 'brand' : rawKind;
	const timings = useTimings(kind);
	const status = (job?.status === 'waiting' || job?.status === 'queued' ? job.status : s.status === 'queued' && job ? job.status : s.status) as Job['status'];
	const elapsed = s.start ? ((s.status === 'running' ? Date.now() : s.end ?? s.last) - s.start) / 1000 : 0;
	const eta = overallEta(s, kind, timings);
	const question = job?.status === 'waiting' ? job.question ?? s.question : null;
	const output = job?.output ?? s.output;
	const postRun = kind === 'post' && status === 'done' ? (job?.result as PostJobResult | undefined)?.run ?? job?.run : undefined;

	const sendAnswer = async () => {
		if (!id) return;
		const text = question ? [answerText(question, answers[0]), free.trim()].filter(Boolean).join('. ') : free.trim();
		if (!text) return;
		await api.answer(id, text);
		setAnswers({});
		setFree('');
	};

	if (!id) return null;
	return (
		<div className="space-y-5">
			<header className="flex flex-wrap items-start gap-4">
				<div className="min-w-0 flex-1">
					<div className="flex items-center gap-3">
						<StatusPill status={status} />
						<span className="text-xs uppercase tracking-wider text-ink-400">
							{kind} · {job?.brand}
						</span>
					</div>
					<h1 className="mt-2 truncate text-2xl font-extrabold" dir={isRtl(job?.title) ? 'rtl' : 'ltr'}>
						{job?.title ?? '…'}
					</h1>
				</div>
				<div className="flex gap-6">
					{[
						['Elapsed', fmtSec(elapsed)],
						['Time left', eta != null ? `~${fmtSec(eta)}` : '–'],
						['Claude turns', String(job?.usage?.turns ?? s.usage.turns ?? 0)],
						['Images', String(s.assets.filter((a) => a.node === 'images').length)],
					].map(([k, v]) => (
						<div key={k} className="text-right">
							<div className="label">{k}</div>
							<div className="font-mono text-xl font-bold">{v}</div>
						</div>
					))}
				</div>
				{(status === 'running' || status === 'queued') && (
					<button className="btn btn-ghost" onClick={() => api.cancel(id)}>
						Stop
					</button>
				)}
			</header>

			{status === 'queued' && job?.queue_position ? (
				<div className="panel p-4 text-sm text-ink-300">⏳ In the queue (#{job.queue_position}). One job runs at a time so the laptop's RAM is enough to render.</div>
			) : null}

			<section className="panel overflow-hidden">
				<div className="flex items-center justify-between border-b border-ink-700 px-4 py-2.5">
					<div className="flex rounded-xl border border-ink-700 p-1 text-sm">
						{(['factory', 'graph'] as const).map((v) => (
							<button key={v} onClick={() => setView(v)} className={`rounded-lg px-3 py-1 font-medium transition ${view === v ? 'bg-ink-700 text-ink-100' : 'text-ink-400'}`}>
								{v === 'factory' ? '🏭 Factory floor' : '🕸️ Graph'}
							</button>
						))}
					</div>
					<div className="flex items-center gap-4 text-xs text-ink-400">
						{s.model && <span>model {s.model}</span>}
						{s.auth && <span>auth: {s.auth === 'none' ? 'your Claude login (no API key)' : s.auth}</span>}
						{s.pipeline?.aspects && <span>aspects {s.pipeline.aspects.join(' · ')}</span>}
					</div>
				</div>
				<AnimatePresence mode="wait">
					<motion.div key={view} initial={{opacity: 0}} animate={{opacity: 1}} exit={{opacity: 0}} transition={{duration: 0.2}}>
						{view === 'factory' ? <FactoryFloor s={s} kind={kind} /> : <PipelineGraph s={s} kind={kind} />}
					</motion.div>
				</AnimatePresence>
			</section>

			<AnimatePresence>
				{question && (
					<motion.section initial={{opacity: 0, y: 12}} animate={{opacity: 1, y: 0}} exit={{opacity: 0}} className="space-y-3">
						<div className="label !text-violet">💬 Claude needs one answer to continue</div>
						<QuestionCards questions={[question]} answers={answers} onChange={setAnswers} />
						<div className="flex gap-3">
							<input className="field" placeholder="Anything to add…" value={free} onChange={(e) => setFree(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && sendAnswer()} />
							<button className="btn btn-primary" onClick={sendAnswer}>
								Continue
							</button>
						</div>
					</motion.section>
				)}
			</AnimatePresence>

			{status === 'done' && (
				<motion.section initial={{opacity: 0, scale: 0.98}} animate={{opacity: 1, scale: 1}} className="panel flex flex-wrap items-center gap-4 border-teal/40 p-5">
					<div className="text-3xl">🎉</div>
					<div className="min-w-0 flex-1">
						<div className="font-semibold">Finished in {fmtSec(elapsed)}</div>
						<div className="line-clamp-3 whitespace-pre-line text-sm text-ink-300" dir={isRtl(s.summary) ? 'rtl' : 'ltr'}>
							{s.summary}
						</div>
					</div>
					{output && !postRun && (
						<Link to={`/gallery/${output}`} className="btn btn-primary">
							Open in gallery →
						</Link>
					)}
				</motion.section>
			)}
			{postRun && <VariantPicker run={postRun} />}
			{kind === 'post' && status === 'done' && !postRun && (
				<div className="panel p-4 text-sm text-ink-300">The run finished but did not report its post folder. Check the live feed for the run path.</div>
			)}
			{status === 'error' && (
				<section className="panel border-rose/50 p-5 text-sm">
					<div className="font-semibold text-rose">The run failed</div>
					<pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap text-xs text-ink-300 scroll-thin">{job?.error ?? s.error}</pre>
					<button className="btn btn-ghost mt-3" onClick={() => api.answer(id, 'Please continue from where you stopped; fix the cause of the failure first.')}>
						Try to continue
					</button>
				</section>
			)}

			<div className="grid gap-5 xl:grid-cols-[1fr_420px]">
				<section className="panel p-5">
					<div className="mb-3 flex items-center justify-between">
						<div className="label">Timeline · real durations</div>
						<div className="text-xs text-ink-400">dashed = expected time left (from your past runs)</div>
					</div>
					<Timeline s={s} timings={timings} kind={kind} />
					{Object.keys(s.renders).length > 0 && (
						<div className="mt-5 grid gap-3 sm:grid-cols-2">
							{Object.entries(s.renders).map(([comp, r]) => (
								<div key={comp} className="rounded-xl border border-ink-700 bg-ink-900 p-3">
									<div className="flex justify-between text-sm">
										<span className="font-semibold">🔥 {comp.replace('Video-', '')}</span>
										<span className="font-mono text-ink-300">
											{r.frame}/{r.total} frames · {r.fps} fps
										</span>
									</div>
									<div className="mt-2 h-2.5 overflow-hidden rounded-full bg-ink-700">
										<motion.div className="h-full rounded-full bg-gradient-to-r from-[#ff8a3d] to-amber" animate={{width: `${r.pct}%`}} />
									</div>
									<div className="mt-1 flex justify-between font-mono text-xs text-ink-400">
										<span>{Math.round(r.pct)}%</span>
										<span>{r.pct >= 100 ? 'done' : r.eta ? `~${fmtSec(r.eta)} left` : 'warming up'}</span>
									</div>
								</div>
							))}
						</div>
					)}
					{s.fallbacks.length > 0 && (
						<div className="mt-5">
							<div className="label mb-2">Free fallbacks used</div>
							<div className="flex flex-wrap gap-2">
								{s.fallbacks.map((f, i) => (
									<span key={i} className="chip border-amber/50 text-amber" title={f.reason}>
										↪ {f.scene ?? f.node}: {f.to}
									</span>
								))}
							</div>
						</div>
					)}
					{s.checks.length > 0 && (
						<div className="mt-5">
							<div className="label mb-2">Automatic QA</div>
							{s.checks.map((c) => (
								<div key={c.video} className="mb-2 flex flex-wrap gap-2">
									<span className="text-xs text-ink-400">{c.video}</span>
									{c.checks.map((k) => (
										<span key={k.name} className="chip" title={k.detail} style={{borderColor: k.ok ? '#34d3b466' : '#f5b94266', color: k.ok ? '#34d3b4' : '#f5b942'}}>
											{k.ok ? '✓' : '!'} {k.name}
										</span>
									))}
								</div>
							))}
						</div>
					)}
				</section>

				<section className="panel flex max-h-[640px] flex-col p-5">
					<div className="label mb-3">Live feed</div>
					{s.assets.length > 0 && (
						<div className="mb-3 flex gap-2 overflow-x-auto pb-2 scroll-thin">
							<AnimatePresence>
								{s.assets
									.filter((a) => a.type === 'image' || a.type === 'contact_sheet')
									.map((a) => (
										<motion.a key={a.path + a.ts} href={file(a.path)} target="_blank" initial={{opacity: 0, scale: 0.6, y: 20}} animate={{opacity: 1, scale: 1, y: 0}} className="shrink-0">
											<img src={file(a.path)} className="h-24 rounded-lg border border-ink-700 object-cover" title={`${a.scene ?? a.type} ${a.provider ?? ''}`} />
										</motion.a>
									))}
							</AnimatePresence>
						</div>
					)}
					<div className="flex-1 space-y-2.5 overflow-y-auto pr-1 scroll-thin">
						{[...s.thoughts]
							.reverse()
							.slice(0, 80)
							.map((t, i) => {
								const def = nodeDef(t.node, kind);
								return (
									<motion.div key={t.ts + '-' + i} initial={i === 0 ? {opacity: 0, x: 12} : false} animate={{opacity: 1, x: 0}} className="flex gap-2.5">
										<span className="mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-lg text-sm" style={{background: `${def?.color ?? '#7d89a8'}22`}}>
											{t.node === 'you' ? '🙂' : def?.emoji ?? '🤖'}
										</span>
										<div className="min-w-0">
											<div className="text-[11px] font-semibold" style={{color: def?.color ?? '#a8b2cc'}}>
												{t.node === 'you' ? 'You' : def?.label ?? 'Claude'} <span className="font-normal text-ink-400">{new Date(t.ts).toLocaleTimeString()}</span>
											</div>
											<div className="whitespace-pre-line text-[13px] leading-snug text-ink-300" dir={isRtl(t.text) ? 'rtl' : 'ltr'}>
												{t.text.length > 500 ? t.text.slice(0, 500) + '…' : t.text}
											</div>
										</div>
									</motion.div>
								);
							})}
						{!s.thoughts.length && <div className="text-sm text-ink-400">Waiting for Claude to start…</div>}
					</div>
					<button className="mt-3 text-left text-xs text-ink-400 hover:text-ink-100" onClick={() => setShowLog(!showLog)}>
						{showLog ? '▾' : '▸'} Tool activity ({s.activity.length})
					</button>
					{showLog && (
						<div className="mt-2 max-h-48 space-y-1 overflow-y-auto font-mono text-[11px] text-ink-400 scroll-thin">
							{[...s.activity].reverse().map((a, i) => (
								<div key={i} className={a.error ? 'text-rose' : ''}>
									{new Date(a.ts).toLocaleTimeString()} {a.tool} {a.detail ?? ''} {a.error ?? ''}
								</div>
							))}
						</div>
					)}
				</section>
			</div>
		</div>
	);
}

export function RunsPage({jobs}: {jobs: Job[]}) {
	if (!jobs.length) return <Empty icon="🏭" title="No runs yet">Start one from Create. Every run appears here with its live factory view.</Empty>;
	return (
		<div className="space-y-4">
			<h1 className="text-2xl font-extrabold">Live runs</h1>
			<div className="space-y-2">
				{jobs.map((j) => (
					<Link key={j.id} to={`/runs/${j.id}`} className="panel flex items-center gap-4 p-4 transition hover:border-ink-600">
						<StatusPill status={j.status} />
						<div className="min-w-0 flex-1">
							<div className="truncate font-semibold" dir={isRtl(j.title) ? 'rtl' : 'ltr'}>
								{j.title}
							</div>
							<div className="text-xs text-ink-400">
								{j.kind} · {j.brand} · {new Date(j.created * 1000).toLocaleString()}
								{j.output ? ` · ${j.output}` : ''}
							</div>
						</div>
						<div className="text-right font-mono text-sm text-ink-300">{j.started ? fmtSec(((j.ended ?? Date.now() / 1000) - j.started) as number) : '–'}</div>
					</Link>
				))}
			</div>
		</div>
	);
}
