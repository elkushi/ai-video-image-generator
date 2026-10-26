// Content calendar: plan with the content-planner agent (live), approve/edit, then make items.
import {motion} from 'motion/react';
import {useEffect, useState} from 'react';
import {Link, useNavigate, useSearchParams} from 'react-router-dom';
import {StatusPill} from '../components/ui';
import {api, isRtl, type Brand, type CalendarItem} from '../lib/api';
import {useJob} from '../lib/useJob';

const GOAL_COLOR: Record<string, string> = {educational: '#34d3b4', promo: '#f5b942', story: '#9b7bff', event: '#ff6b81', announcement: '#5cb8ff', tutorial: '#a3e635'};

export default function CalendarPage() {
	const [params, setParams] = useSearchParams();
	const nav = useNavigate();
	const [brands, setBrands] = useState<Brand[]>([]);
	const slug = params.get('brand') ?? brands[0]?.slug ?? '';
	const [items, setItems] = useState<CalendarItem[]>([]);
	const [period, setPeriod] = useState('2 weeks');
	const [perWeek, setPerWeek] = useState(3);
	const [themes, setThemes] = useState('');
	const [planJob, setPlanJob] = useState<string | undefined>();
	const [draft, setDraft] = useState<CalendarItem[] | null>(null);
	const [rationale, setRationale] = useState('');
	const {s, job} = useJob(planJob);

	useEffect(() => {
		api.brands().then(setBrands);
	}, []);
	useEffect(() => {
		if (slug) api.brand(slug).then((b) => setItems(b.calendar?.items ?? []));
	}, [slug]);
	useEffect(() => {
		const r = job?.result as {items?: CalendarItem[]; rationale?: string} | undefined;
		if (job?.status === 'done' && r?.items && !draft) {
			setDraft(r.items);
			setRationale(r.rationale ?? '');
		}
	}, [job, draft]);

	const plan = async () => {
		setDraft(null);
		const j = await api.planCalendar(slug, {period, per_week: perWeek, themes});
		setPlanJob(j.id);
	};
	const approve = async () => {
		if (!draft) return;
		const cal = await api.approveCalendar(slug, draft);
		setItems(cal.items);
		setDraft(null);
		setPlanJob(undefined);
	};
	const makeItem = async (it: CalendarItem) => {
		const j = await api.makeVideo({
			brand: slug,
			topic: it.topic,
			goal: it.goal,
			language: it.languages.join(', '),
			length_s: it.length_s,
			style: it.style,
			cta: it.cta,
			understood: `Calendar item ${it.id}: ${it.format}. Hook: ${it.hook}. Facts: ${(it.facts ?? []).join(' | ')}. Aspects: ${it.aspects.join(', ')}.`,
			calendar_item: it,
		});
		nav(`/runs/${j.id}`);
	};

	return (
		<div className="space-y-5">
			<div className="flex flex-wrap items-center gap-3">
				<h1 className="mr-auto text-2xl font-extrabold">Content calendar</h1>
				{brands.map((b) => (
					<span key={b.slug} className="chip" data-on={b.slug === slug} onClick={() => setParams({brand: b.slug})}>
						{b.name}
					</span>
				))}
			</div>

			<section className="panel flex flex-wrap items-end gap-3 p-5">
				<div>
					<div className="label mb-1">Period</div>
					<select className="field" value={period} onChange={(e) => setPeriod(e.target.value)}>
						{['1 week', '2 weeks', '1 month'].map((p) => (
							<option key={p}>{p}</option>
						))}
					</select>
				</div>
				<div>
					<div className="label mb-1">Posts / week</div>
					<input type="number" min={1} max={7} className="field w-24" value={perWeek} onChange={(e) => setPerWeek(Number(e.target.value))} />
				</div>
				<div className="min-w-[260px] flex-1">
					<div className="label mb-1">Themes, launches, events (optional)</div>
					<input className="field" value={themes} onChange={(e) => setThemes(e.target.value)} placeholder="e.g. webinar on 12 Nov, focus on OTP" />
				</div>
				<button className="btn btn-primary" onClick={plan} disabled={!slug || job?.status === 'running'}>
					🗓️ Plan with the content planner
				</button>
			</section>

			{planJob && !draft && (
				<section className="panel flex items-center gap-4 p-5">
					<StatusPill status={job?.status ?? 'queued'} />
					<div className="flex-1 text-sm text-ink-300">{s.thoughts.at(-1)?.text?.slice(0, 200) ?? 'The content planner is reading the brand profile and the playbook…'}</div>
					<Link to={`/runs/${planJob}`} className="text-sm text-amber">
						Watch live →
					</Link>
				</section>
			)}

			{draft && (
				<motion.section initial={{opacity: 0, y: 10}} animate={{opacity: 1, y: 0}} className="panel space-y-3 border-violet/40 p-5">
					<div className="label !text-violet">Proposed plan: edit, drop or approve</div>
					{rationale && <p className="text-sm text-ink-300">{rationale}</p>}
					{draft.map((it, i) => (
						<div key={it.id} className="grid items-center gap-3 rounded-xl border border-ink-700 p-3 md:grid-cols-[110px_110px_1fr_auto]">
							<input className="field py-1.5 text-sm" value={it.date} onChange={(e) => setDraft(draft.map((x, j) => (j === i ? {...x, date: e.target.value} : x)))} />
							<span className="text-xs font-semibold uppercase" style={{color: GOAL_COLOR[it.goal] ?? '#a8b2cc'}}>
								{it.goal}
								<br />
								<span className="font-normal text-ink-400">{it.format}</span>
							</span>
							<div>
								<input className="field py-1.5 text-sm font-semibold" value={it.topic} onChange={(e) => setDraft(draft.map((x, j) => (j === i ? {...x, topic: e.target.value} : x)))} />
								<div className="mt-1 text-xs text-ink-400" dir={isRtl(it.hook) ? 'rtl' : 'ltr'}>
									Hook: {it.hook} · {it.languages.join('/')} · {it.aspects.join(' ')}
								</div>
							</div>
							<button className="btn btn-ghost px-3" onClick={() => setDraft(draft.filter((_, j) => j !== i))}>
								✕
							</button>
						</div>
					))}
					<button className="btn btn-primary" onClick={approve}>
						✓ Approve {draft.length} items
					</button>
				</motion.section>
			)}

			<section className="space-y-2">
				<div className="label">Queue ({items.length})</div>
				{items.map((it) => (
					<div key={it.id} className="panel flex flex-wrap items-center gap-4 p-4">
						<div className="w-24 font-mono text-sm text-ink-300">{it.date}</div>
						<span className="h-10 w-1 rounded-full" style={{background: GOAL_COLOR[it.goal] ?? '#7d89a8'}} />
						<div className="min-w-0 flex-1">
							<div className="truncate font-semibold">{it.topic}</div>
							<div className="truncate text-xs text-ink-400">
								{it.goal} · {it.format} · {it.languages.join('/')} · {it.hook}
							</div>
						</div>
						<span className="chip" data-on={it.status !== 'todo'}>
							{it.status}
						</span>
						{it.status === 'todo' && (
							<button className="btn btn-primary px-4 py-2" onClick={() => makeItem(it)}>
								Make
							</button>
						)}
					</div>
				))}
				{!items.length && <div className="text-sm text-ink-400">No items yet. Plan a period above.</div>}
			</section>
		</div>
	);
}
