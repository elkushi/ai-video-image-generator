// The 3 post variants side by side: slides, angle, editable copy per platform. Pick one -> delivered to output/.
import {AnimatePresence, motion} from 'motion/react';
import {useEffect, useState} from 'react';
import {Link, useNavigate} from 'react-router-dom';
import {api, file, isRtl, postPreview, runName, type PostCopy, type PostPlatform, type PostRun, type PostVariant} from '../lib/api';

export const PLATFORM_LABEL: Record<string, string> = {linkedin: 'LinkedIn', instagram: 'Instagram', facebook: 'Facebook', x: 'X', tiktok: 'TikTok'};
export const PLATFORM_LIMIT: Record<string, number> = {linkedin: 3000, instagram: 2200, x: 280, tiktok: 2200, facebook: 63206};
export const ASPECT_CLASS: Record<string, string> = {'4x5': 'aspect-[4/5]', '1x1': 'aspect-square', '9x16': 'aspect-[9/16]', '16x9': 'aspect-video'};

export function SlideViewer({slides, aspect, className = ''}: {slides: string[]; aspect: string; className?: string}) {
	const [i, setI] = useState(0);
	const n = slides.length;
	const cur = Math.min(i, Math.max(0, n - 1));
	return (
		<div className={`group relative overflow-hidden rounded-xl bg-ink-950 ${ASPECT_CLASS[aspect] ?? 'aspect-[4/5]'} ${className}`}>
			{n ? (
				<AnimatePresence mode="wait" initial={false}>
					<motion.img key={slides[cur]} src={file(slides[cur])} className="absolute inset-0 h-full w-full object-contain" initial={{opacity: 0, x: 20}} animate={{opacity: 1, x: 0}} exit={{opacity: 0, x: -20}} transition={{duration: 0.18}} />
				</AnimatePresence>
			) : (
				<div className="grid h-full place-items-center text-sm text-ink-400">No preview rendered</div>
			)}
			{n > 1 && (
				<>
					<button className="absolute left-2 top-1/2 grid h-9 w-9 -translate-y-1/2 place-items-center rounded-full bg-black/60 text-lg opacity-80 transition hover:opacity-100 disabled:opacity-20" disabled={cur === 0} onClick={() => setI(cur - 1)}>
						‹
					</button>
					<button className="absolute right-2 top-1/2 grid h-9 w-9 -translate-y-1/2 place-items-center rounded-full bg-black/60 text-lg opacity-80 transition hover:opacity-100 disabled:opacity-20" disabled={cur === n - 1} onClick={() => setI(cur + 1)}>
						›
					</button>
					<div className="absolute bottom-2 left-0 right-0 flex justify-center gap-1.5">
						{slides.map((_, k) => (
							<button key={k} onClick={() => setI(k)} className="h-1.5 rounded-full transition-all" style={{width: k === cur ? 18 : 6, background: k === cur ? '#f5b942' : '#ffffff88'}} />
						))}
					</div>
					<span className="absolute right-2 top-2 rounded-md bg-black/60 px-1.5 py-0.5 font-mono text-[10px]">
						{cur + 1}/{n}
					</span>
				</>
			)}
		</div>
	);
}

const platformsOf = (p: PostRun, v: PostVariant): string[] => {
	const keys = [...p.spec.platforms, ...Object.keys(v.copy).filter((k) => k in PLATFORM_LABEL)];
	return [...new Set(keys)];
};

function VariantCard({p, v, copy, onCopy, picked, busy, onPick}: {p: PostRun; v: PostVariant; copy: PostCopy; onCopy: (c: PostCopy) => void; picked: boolean; busy: boolean; onPick: () => void}) {
	const plats = platformsOf(p, v);
	const [tab, setTab] = useState(plats[0] ?? 'linkedin');
	const prev = postPreview(p, v.id);
	const text = (copy[tab as PostPlatform] as string | undefined) ?? '';
	const limit = PLATFORM_LIMIT[tab];
	const rtl = p.spec.language === 'ar' || isRtl(text);
	return (
		<motion.div layout className="panel flex flex-col gap-3 p-4" style={picked ? {borderColor: '#34d3b4', boxShadow: '0 0 0 3px #34d3b433'} : undefined}>
			<div className="flex items-center gap-2">
				<span className="grid h-8 w-8 place-items-center rounded-lg bg-amber/15 font-extrabold text-amber">{v.id}</span>
				<span className="rounded-md bg-ink-800 px-2 py-0.5 text-[11px] uppercase tracking-wider text-ink-300">
					{v.format === 'carousel' ? `Carousel · ${v.slides.length}` : 'Single image'}
				</span>
				{picked && <span className="ml-auto rounded-md bg-teal/15 px-2 py-0.5 text-[11px] font-bold text-teal">✓ Picked</span>}
			</div>
			<SlideViewer slides={prev?.slides ?? []} aspect={p.spec.aspect} />
			{prev?.motion && (
				<a href={file(prev.motion)} target="_blank" className="text-xs text-sky hover:underline">
					▶ Animated version
				</a>
			)}
			<div>
				<div className="font-semibold leading-snug" dir={isRtl(v.angle) ? 'rtl' : 'ltr'}>
					{v.angle}
				</div>
				{v.why && <div className="mt-1 text-xs leading-snug text-ink-400">{v.why}</div>}
			</div>
			<div className="flex flex-wrap gap-1.5">
				{plats.map((k) => (
					<span key={k} className="chip !px-2.5 !py-0.5 !text-xs" data-on={tab === k} onClick={() => setTab(k)}>
						{PLATFORM_LABEL[k] ?? k}
					</span>
				))}
			</div>
			<div>
				<textarea className="field text-[13px] leading-relaxed" rows={8} dir={rtl ? 'rtl' : 'ltr'} value={text} onChange={(e) => onCopy({...copy, [tab]: e.target.value})} />
				{limit && (
					<div className="mt-1 text-right font-mono text-[11px]" style={{color: text.length > limit ? '#ff6b81' : '#7d89a8'}}>
						{text.length}/{limit}
					</div>
				)}
			</div>
			<div>
				<div className="label mb-1">Hashtags</div>
				<input
					className="field text-[13px]"
					value={(copy.hashtags ?? []).map((h) => (h.startsWith('#') ? h : `#${h}`)).join(' ')}
					onChange={(e) => onCopy({...copy, hashtags: e.target.value.split(/[\s,]+/).map((h) => h.replace(/^#/, '')).filter(Boolean)})}
				/>
			</div>
			<div>
				<div className="label mb-1">Alt text</div>
				<textarea className="field text-[13px]" rows={2} dir={rtl ? 'rtl' : 'ltr'} value={copy.alt ?? ''} onChange={(e) => onCopy({...copy, alt: e.target.value})} />
			</div>
			<button className="btn btn-primary mt-auto" disabled={busy} onClick={onPick}>
				{busy ? 'Delivering…' : picked ? '✓ Pick again (with these edits)' : 'Pick this one'}
			</button>
		</motion.div>
	);
}

export function VariantPicker({run}: {run: string}) {
	const name = runName(run);
	const nav = useNavigate();
	const [p, setP] = useState<PostRun | null>(null);
	const [err, setErr] = useState('');
	const [copies, setCopies] = useState<Record<string, PostCopy>>({});
	const [busy, setBusy] = useState('');
	const [done, setDone] = useState<{output: string; files: string[]} | null>(null);
	const [feedback, setFeedback] = useState('');
	const [which, setWhich] = useState<string[]>([]);
	const [revising, setRevising] = useState(false);

	const load = () =>
		api
			.post(name)
			.then((x) => {
				setP(x);
				setCopies(Object.fromEntries(x.spec.variants.map((v) => [v.id, {...v.copy}])));
			})
			.catch((e) => setErr(String(e)));
	useEffect(() => {
		if (name) load();
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [name]);

	if (err) return <div className="panel border-rose/50 p-4 text-sm text-rose">Could not load the post variants: {err}</div>;
	if (!p) return <div className="panel p-5 text-sm text-ink-400">Loading the variants…</div>;

	const picked = p.picked ?? p.spec.picked ?? null;
	const output = done?.output ?? p.output;
	const files = done?.files ?? [];
	const contact = typeof p.previews.contact === 'string' ? p.previews.contact : null;

	const pick = async (id: string) => {
		setBusy(id);
		setErr('');
		try {
			const r = await api.pickPost(name, {variant: id, copy: copies[id]});
			setDone(r);
			await load();
		} catch (e) {
			setErr(String(e));
		}
		setBusy('');
	};
	const revise = async () => {
		setRevising(true);
		try {
			const job = await api.revisePost(name, {feedback, variants: which.length ? which : undefined});
			nav(`/runs/${job.id}`);
		} catch (e) {
			setErr(String(e));
			setRevising(false);
		}
	};

	return (
		<section className="space-y-4">
			<div className="flex flex-wrap items-end gap-3">
				<div className="mr-auto">
					<div className="label !text-amber">Your 3 options</div>
					<h2 className="text-xl font-extrabold" dir={isRtl(p.spec.topic) ? 'rtl' : 'ltr'}>
						{p.spec.topic}
					</h2>
					<div className="text-xs text-ink-400">
						{p.spec.brand} · {p.spec.aspect.replace('x', ':')} · {p.spec.language}
						{p.spec.posting_time ? ` · best time: ${p.spec.posting_time}` : ''}
					</div>
				</div>
				{contact && (
					<a href={file(contact)} target="_blank" className="btn btn-ghost text-xs">
						🗂️ Contact sheet
					</a>
				)}
			</div>

			<AnimatePresence>
				{output && (
					<motion.div initial={{opacity: 0, y: 8}} animate={{opacity: 1, y: 0}} className="panel flex flex-wrap items-center gap-3 border-teal/50 p-4">
						<span className="text-2xl">🚚</span>
						<div className="mr-auto">
							<div className="font-semibold">Delivered{picked ? `: variant ${picked}` : ''}</div>
							<div className="text-xs text-ink-400">output/{output}</div>
						</div>
						{files
							.filter((f) => /\.(png|pdf|mp4)$/.test(f))
							.map((f) => (
								<a key={f} href={file(`output/${output}/${f}`)} download className="chip">
									⬇ {f}
								</a>
							))}
						<Link to={`/gallery/${output}`} className="btn btn-primary">
							Open in gallery →
						</Link>
					</motion.div>
				)}
			</AnimatePresence>

			<div className="grid gap-4 lg:grid-cols-3">
				{p.spec.variants.map((v) => (
					<VariantCard
						key={v.id}
						p={p}
						v={v}
						copy={copies[v.id] ?? v.copy}
						onCopy={(c) => setCopies({...copies, [v.id]: c})}
						picked={picked === v.id}
						busy={busy === v.id}
						onPick={() => pick(v.id)}
					/>
				))}
			</div>

			<div className="panel border-violet/30 p-4">
				<div className="label mb-2 !text-violet">Not quite? Regenerate with feedback</div>
				<textarea
					className="field text-sm"
					rows={2}
					placeholder="e.g. Shorter hook, use the light theme, make B a 5-slide carousel, lead with the client count"
					value={feedback}
					onChange={(e) => setFeedback(e.target.value)}
				/>
				<div className="mt-2 flex flex-wrap items-center gap-2">
					<span className="text-xs text-ink-400">Redo:</span>
					{p.spec.variants.map((v) => (
						<span key={v.id} className="chip" data-on={which.includes(v.id)} onClick={() => setWhich(which.includes(v.id) ? which.filter((x) => x !== v.id) : [...which, v.id])}>
							{v.id}
						</span>
					))}
					<span className="text-xs text-ink-400">{which.length ? '' : '(none selected = all)'}</span>
					<button className="btn btn-primary ml-auto" disabled={!feedback.trim() || revising} onClick={revise}>
						🔁 {revising ? 'Starting…' : 'Regenerate'}
					</button>
				</div>
			</div>
		</section>
	);
}
