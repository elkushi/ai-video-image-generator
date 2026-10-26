import {AnimatePresence, motion} from 'motion/react';
import {useEffect, useState} from 'react';
import {Link, useNavigate, useParams} from 'react-router-dom';
import {Dropzone, Empty} from '../components/ui';
import {api, file, type Brand} from '../lib/api';

type Upload = {name: string; path: string; size: number};

function useUploads() {
	const [draft] = useState(() => Math.random().toString(36).slice(2, 10));
	const [uploads, setUploads] = useState<Upload[]>([]);
	const [busy, setBusy] = useState(false);
	const [err, setErr] = useState('');
	const add = async (fs: File[]) => {
		if (!fs.length) return;
		setBusy(true);
		try {
			const r = await api.upload(fs, draft);
			setUploads((u) => [...u, ...r.files]);
		} catch (e) {
			setErr(String(e));
		}
		setBusy(false);
	};
	return {uploads, setUploads, busy, err, setErr, add};
}

function UploadList({uploads, onRemove}: {uploads: Upload[]; onRemove: (p: string) => void}) {
	if (!uploads.length) return null;
	return (
		<div className="mt-3 flex flex-wrap gap-2">
			{uploads.map((u) => (
				<span key={u.path} className="chip" data-on>
					📄 {u.name} <span className="text-ink-400">{(u.size / 1024 / 1024).toFixed(1)} MB</span>
					<span onClick={() => onRemove(u.path)}>✕</span>
				</span>
			))}
		</div>
	);
}

const LANGS: [string, string][] = [
	['en', 'English'],
	['ar', 'العربية'],
	['ru', 'Русский'],
];

function NewBrandForm({onClose}: {onClose: () => void}) {
	const nav = useNavigate();
	const up = useUploads();
	const [f, setF] = useState({name: '', website: '', notes: '', language: 'en'});
	const [starting, setStarting] = useState(false);
	const go = async () => {
		setStarting(true);
		up.setErr('');
		try {
			const job = await api.createBrand({...f, uploads: up.uploads.map((u) => u.path)});
			nav(`/runs/${job.id}`);
		} catch (e) {
			up.setErr(String(e));
			setStarting(false);
		}
	};
	return (
		<motion.div initial={{height: 0, opacity: 0}} animate={{height: 'auto', opacity: 1}} exit={{height: 0, opacity: 0}} className="overflow-hidden">
			<div className="panel space-y-4 border-amber/40 p-5">
				<div>
					<div className="font-semibold">New brand from its guide</div>
					<div className="text-sm text-ink-400">
						Any company or product. Drop the brand guide (PDF), logos (a white version helps), fonts and product photos. Claude builds the kit: colours, fonts, logo, tone, facts and rules. Every post and video then
						follows it.
					</div>
				</div>
				<div className="grid gap-3 md:grid-cols-2">
					<input className="field" placeholder="Brand or product name" value={f.name} onChange={(e) => setF({...f, name: e.target.value})} />
					<input className="field" placeholder="Website (optional, used for colours, screenshots and facts)" value={f.website} onChange={(e) => setF({...f, website: e.target.value})} />
					<textarea
						className="field md:col-span-2"
						rows={3}
						placeholder="What it is, who it is for, approved numbers, tone of voice, words to avoid, competitors not to name…"
						value={f.notes}
						onChange={(e) => setF({...f, notes: e.target.value})}
					/>
				</div>
				<div className="flex flex-wrap items-center gap-2">
					<span className="label mr-1">Main language</span>
					{LANGS.map(([k, l]) => (
						<span key={k} className="chip" data-on={f.language === k} onClick={() => setF({...f, language: k})}>
							{l}
						</span>
					))}
				</div>
				<Dropzone onFiles={up.add} busy={up.busy} />
				<UploadList uploads={up.uploads} onRemove={(p) => up.setUploads(up.uploads.filter((x) => x.path !== p))} />
				{up.err && <div className="rounded-xl border border-rose/50 bg-rose/10 p-3 text-sm text-rose">{up.err}</div>}
				<div className="flex gap-3">
					<button className="btn btn-primary" disabled={!f.name.trim() || starting || up.busy} onClick={go}>
						🎨 {starting ? 'Starting…' : 'Build the brand kit'}
					</button>
					<button className="btn btn-ghost" onClick={onClose}>
						Cancel
					</button>
				</div>
			</div>
		</motion.div>
	);
}

export default function BrandsPage() {
	const [items, setItems] = useState<Brand[] | null>(null);
	const [adding, setAdding] = useState(false);
	useEffect(() => {
		api.brands().then(setItems);
	}, []);
	if (!items) return null;
	return (
		<div className="space-y-5">
			<div className="flex items-center">
				<h1 className="mr-auto text-2xl font-extrabold">Brands</h1>
				<button className="btn btn-primary" onClick={() => setAdding(!adding)}>
					＋ New brand from guide
				</button>
			</div>
			<AnimatePresence>{adding && <NewBrandForm onClose={() => setAdding(false)} />}</AnimatePresence>
			{items.length ? (
				<div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
					{items.map((b, i) => (
						<motion.div key={b.slug} initial={{opacity: 0, y: 12}} animate={{opacity: 1, y: 0}} transition={{delay: i * 0.05}}>
							<Link to={`/brands/${b.slug}`} className="panel block overflow-hidden transition hover:border-ink-600">
								<div className="flex h-28 items-center justify-center" style={{background: `linear-gradient(135deg, ${b.colors.dark ?? '#111'}, ${b.colors.primary ?? '#333'})`}}>
									{b.logo ? <img src={file(b.logo)} className="max-h-12 max-w-[70%] object-contain" /> : <span className="text-2xl font-extrabold" style={{color: b.colors.accent}}>{b.name}</span>}
								</div>
								<div className="p-4">
									<div className="font-semibold">{b.name}</div>
									<div className="text-sm text-ink-400">{b.tagline}</div>
									<div className="mt-3 flex items-center gap-1.5">
										{Object.entries(b.colors)
											.filter(([k]) => !k.startsWith('text'))
											.map(([k, c]) => (
												<span key={k} title={`${k} ${c}`} className="h-5 w-5 rounded-md border border-white/10" style={{background: c}} />
											))}
										<span className="ml-auto text-xs text-ink-400">
											{b.fonts.heading} · {b.videos} videos · {b.posts ?? 0} posts · {b.assets} assets
										</span>
									</div>
								</div>
							</Link>
						</motion.div>
					))}
				</div>
			) : (
				<Empty icon="🎨" title="No brands yet">Click "New brand from guide" and drop the brand guide and logo.</Empty>
			)}
		</div>
	);
}

export function BrandPage() {
	const {slug} = useParams();
	const [d, setD] = useState<Awaited<ReturnType<typeof api.brand>> | null>(null);
	const [tab, setTab] = useState<'profile' | 'kit' | 'assets' | 'performance'>('profile');
	const [guideOpen, setGuideOpen] = useState(false);
	const [notes, setNotes] = useState('');
	const [starting, setStarting] = useState(false);
	const up = useUploads();
	const nav = useNavigate();
	useEffect(() => {
		if (slug) api.brand(slug).then(setD);
	}, [slug]);
	if (!d) return null;
	const kit = d.kit as Record<string, any>;
	return (
		<div className="space-y-5">
			<div className="flex flex-wrap items-center gap-3 md:gap-4">
				<Link to="/brands" className="text-sm text-ink-400 hover:text-ink-100">
					← Brands
				</Link>
				<h1 className="mr-auto text-2xl font-extrabold">{kit.name}</h1>
				<Link to={`/?mode=post&brand=${slug}`} className="btn btn-primary">
					🖼️ Make a post
				</Link>
				<Link to={`/?brand=${slug}`} className="btn btn-ghost">
					🎬 Make a video
				</Link>
				<Link to={`/calendar?brand=${slug}`} className="btn btn-ghost">
					🗓️ Calendar
				</Link>
				<button className="btn btn-ghost" onClick={() => setGuideOpen(!guideOpen)}>
					🎨 Update from brand guide
				</button>
			</div>
			<AnimatePresence>
				{guideOpen && (
					<motion.div initial={{height: 0, opacity: 0}} animate={{height: 'auto', opacity: 1}} exit={{height: 0, opacity: 0}} className="overflow-hidden">
						<div className="panel space-y-3 border-amber/40 p-5">
							<div className="text-sm text-ink-400">Drop a new or updated brand guide, logos or fonts. Claude updates colours, fonts, logo, rules and approved facts in the kit and keeps what you already approved.</div>
							<Dropzone onFiles={up.add} busy={up.busy} />
							<UploadList uploads={up.uploads} onRemove={(p) => up.setUploads(up.uploads.filter((x) => x.path !== p))} />
							<textarea className="field text-sm" rows={2} placeholder="What changed? (optional) e.g. new primary colour, new tagline, stop using the old logo" value={notes} onChange={(e) => setNotes(e.target.value)} />
							{up.err && <div className="rounded-xl border border-rose/50 bg-rose/10 p-3 text-sm text-rose">{up.err}</div>}
							<button
								className="btn btn-primary"
								disabled={(!up.uploads.length && !notes.trim()) || starting || up.busy}
								onClick={async () => {
									setStarting(true);
									try {
										nav(`/runs/${(await api.brandGuide(slug!, {uploads: up.uploads.map((u) => u.path), notes})).id}`);
									} catch (e) {
										up.setErr(String(e));
										setStarting(false);
									}
								}}
							>
								{starting ? 'Starting…' : 'Update the brand kit'}
							</button>
						</div>
					</motion.div>
				)}
			</AnimatePresence>
			<div className="flex gap-2">
				{(['profile', 'kit', 'assets', 'performance'] as const).map((t) => (
					<span key={t} className="chip" data-on={tab === t} onClick={() => setTab(t)}>
						{t}
					</span>
				))}
			</div>
			{tab === 'profile' && <pre className="panel whitespace-pre-wrap p-5 text-sm leading-relaxed text-ink-300">{d.profile || 'No profile.md'}</pre>}
			{tab === 'kit' && <pre className="panel overflow-auto p-5 font-mono text-xs text-ink-300">{JSON.stringify(kit, null, 2)}</pre>}
			{tab === 'assets' && (
				<div className="grid grid-cols-3 gap-3 md:grid-cols-6">
					{d.assets.map((a) => (
						<a key={a} href={file(a)} target="_blank" className="panel overflow-hidden p-2">
							<img src={file(a)} className="h-28 w-full object-contain" />
							<div className="mt-1 truncate text-[10px] text-ink-400">{a.split('/').pop()}</div>
						</a>
					))}
					{!d.assets.length && <div className="text-sm text-ink-400">No assets yet.</div>}
				</div>
			)}
			{tab === 'performance' && <pre className="panel whitespace-pre-wrap p-5 text-sm text-ink-300">{d.performance || 'No stats yet. Add them on the Stats page.'}</pre>}
		</div>
	);
}
