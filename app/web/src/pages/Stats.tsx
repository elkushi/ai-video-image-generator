// Post stats per delivered video, simple charts, and "learn from stats" (review_performance.md).
import {motion} from 'motion/react';
import {useEffect, useState} from 'react';
import {useNavigate} from 'react-router-dom';
import {Empty} from '../components/ui';
import {api, file, type Output, type OutputDetail} from '../lib/api';

const FIELDS: [string, string][] = [
	['views', 'Views'],
	['avg_watch_s', 'Avg watch (s)'],
	['likes', 'Likes'],
	['comments', 'Comments'],
	['shares', 'Shares'],
	['saves', 'Saves'],
	['follows', 'Follows'],
	['clicks', 'Clicks'],
];

const median = (xs: number[]) => {
	if (!xs.length) return 0;
	const s = [...xs].sort((a, b) => a - b);
	return s.length % 2 ? s[(s.length - 1) / 2] : (s[s.length / 2 - 1] + s[s.length / 2]) / 2;
};

export default function StatsPage() {
	const nav = useNavigate();
	const [outs, setOuts] = useState<Output[]>([]);
	const [details, setDetails] = useState<Record<string, OutputDetail>>({});
	const [sel, setSel] = useState('');
	const [form, setForm] = useState<Record<string, string>>({platform: 'Instagram'});

	const load = async () => {
		const o = (await api.outputs()).filter((x) => !x.smoke);
		setOuts(o);
		const d = await Promise.all(o.map((x) => api.output(x.name)));
		setDetails(Object.fromEntries(d.map((x) => [x.name, x])));
		if (!sel && o[0]) setSel(o[0].name);
	};
	useEffect(() => {
		load();
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, []);

	const save = async () => {
		const body: Record<string, unknown> = {platform: form.platform, notes: form.notes ?? ''};
		for (const [k] of FIELDS) if (form[k]) body[k] = Number(form[k]);
		await api.addStats(sel, body);
		setForm({platform: form.platform});
		load();
	};

	// median views by format / goal
	const rows = Object.values(details).flatMap((d) => (d.stats as Record<string, number>[]).map((s) => ({format: d.format || d.goal || 'other', brand: d.brand, views: Number(s.views) || 0})));
	const byFormat = Object.entries(rows.reduce<Record<string, number[]>>((a, r) => ((a[r.format] = [...(a[r.format] ?? []), r.views]), a), {})).map(([k, v]) => ({k, v: median(v), n: v.length}));
	const max = Math.max(1, ...byFormat.map((b) => b.v));
	const brands = [...new Set(outs.map((o) => o.brand))];

	if (!outs.length) return <Empty icon="📈" title="No delivered videos yet">After you post a video, come back and add its numbers here. Claude learns what works for each brand.</Empty>;
	return (
		<div className="space-y-5">
			<div className="flex flex-wrap items-center gap-3">
				<h1 className="mr-auto text-2xl font-extrabold">Stats & learning</h1>
				{brands.map((b) => (
					<button key={b} className="btn btn-ghost" onClick={async () => nav(`/runs/${(await api.learn(b)).id}`)}>
						🧠 Learn from {b}'s stats
					</button>
				))}
			</div>
			<div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_420px]">
				<section className="panel min-w-0 p-5">
					<div className="label mb-3">Add numbers for a published video or post</div>
					<div className="mb-3 flex gap-3 overflow-x-auto pb-2 scroll-thin">
						{outs.map((o) => (
							<button key={o.name} onClick={() => setSel(o.name)} className="w-28 shrink-0 overflow-hidden rounded-xl border text-left" style={{borderColor: sel === o.name ? '#f5b942' : '#212a40'}}>
								{(o.videos[0]?.cover ?? o.cover) && <img src={file((o.videos[0]?.cover ?? o.cover)!)} className="h-32 w-full bg-black object-contain" />}
								<div className="truncate p-1.5 text-[11px]">{o.title}</div>
							</button>
						))}
					</div>
					<div className="grid gap-3 md:grid-cols-4">
						<select className="field" value={form.platform} onChange={(e) => setForm({...form, platform: e.target.value})}>
							{['Instagram', 'LinkedIn', 'TikTok', 'YouTube', 'Facebook'].map((p) => (
								<option key={p}>{p}</option>
							))}
						</select>
						{FIELDS.map(([k, l]) => (
							<input key={k} className="field" type="number" placeholder={l} value={form[k] ?? ''} onChange={(e) => setForm({...form, [k]: e.target.value})} />
						))}
						<input className="field md:col-span-3" placeholder="Notes (boosted? posted at 9am?)" value={form.notes ?? ''} onChange={(e) => setForm({...form, notes: e.target.value})} />
					</div>
					<button className="btn btn-primary mt-3" onClick={save} disabled={!sel || !form.views}>
						Save stats
					</button>
					<div className="mt-5 space-y-1 text-sm">
						{(details[sel]?.stats ?? []).map((s, i) => (
							<div key={i} className="flex flex-wrap gap-3 border-b border-ink-800 py-1.5 text-ink-300">
								<b>{String(s.platform)}</b>
								{FIELDS.filter(([k]) => s[k] != null).map(([k, l]) => (
									<span key={k}>
										{l}: {String(s[k])}
									</span>
								))}
								<span className="ml-auto text-xs text-ink-400">{String(s.measured_at)}</span>
							</div>
						))}
					</div>
				</section>
				<section className="panel min-w-0 p-5">
					<div className="label mb-3">Median views by format</div>
					{byFormat.length ? (
						<div className="space-y-3">
							{byFormat.map((b) => (
								<div key={b.k}>
									<div className="flex justify-between text-sm">
										<span>{b.k}</span>
										<span className="font-mono text-ink-300">
											{Math.round(b.v).toLocaleString()} <span className="text-ink-400">(n={b.n})</span>
										</span>
									</div>
									<div className="mt-1 h-3 overflow-hidden rounded-full bg-ink-800">
										<motion.div className="h-full rounded-full bg-gradient-to-r from-violet to-amber" initial={{width: 0}} animate={{width: `${(b.v / max) * 100}%`}} />
									</div>
								</div>
							))}
						</div>
					) : (
						<div className="text-sm text-ink-400">Add stats to see which formats win. After 5+ videos, "Learn" writes what works into the brand's performance.md, and the planner and strategist use it.</div>
					)}
				</section>
			</div>
		</div>
	);
}
