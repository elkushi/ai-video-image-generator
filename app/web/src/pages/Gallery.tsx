// Delivered videos and posts: grid (hover-play for videos), detail pages with players / slide viewer, copy, QA, revisions.
import {motion} from 'motion/react';
import {useEffect, useState} from 'react';
import {Link, useNavigate, useParams} from 'react-router-dom';
import {Empty} from '../components/ui';
import {api, file, isRtl, type Output, type OutputDetail} from '../lib/api';
import {ASPECT_CLASS, SlideViewer} from '../components/VariantPicker';

function PostCard({o}: {o: Output}) {
	const cover = o.cover ?? o.images?.[0];
	const n = o.images?.length ?? 1;
	return (
		<Link to={`/gallery/${o.name}`} className="panel group overflow-hidden transition hover:-translate-y-0.5 hover:border-ink-600">
			<div className="relative aspect-[4/5] bg-ink-950">
				{cover && <img src={file(cover)} className="h-full w-full object-contain" />}
				{o.aspect && <span className="absolute bottom-2 right-2 rounded-md bg-black/60 px-1.5 py-0.5 font-mono text-[10px]">{o.aspect.replace('x', ':')}</span>}
				<div className="absolute left-2 top-2 flex gap-1">
					<span className="rounded-md bg-amber/90 px-1.5 py-0.5 text-[10px] font-bold text-ink-950">{o.format === 'carousel' || n > 1 ? `Carousel · ${n}` : 'Post'}</span>
					{o.pdf && <span className="rounded-md bg-black/60 px-1.5 py-0.5 font-mono text-[10px]">PDF</span>}
				</div>
				{o.language && <span className="absolute right-2 top-2 rounded-md bg-black/60 px-1.5 py-0.5 text-[10px] uppercase">{o.language}</span>}
			</div>
			<div className="p-3">
				<div className="truncate text-sm font-semibold" dir={isRtl(o.title) ? 'rtl' : 'ltr'}>
					{o.title}
				</div>
				{o.angle && (
					<div className="mt-0.5 truncate text-[11px] text-ink-300" dir={isRtl(o.angle) ? 'rtl' : 'ltr'}>
						{o.angle}
					</div>
				)}
				<div className="mt-1 text-[11px] text-ink-400">
					{o.brand} · {o.date}
					{o.platforms?.length ? ` · ${o.platforms.join(', ')}` : ''}
				</div>
			</div>
		</Link>
	);
}

function Card({o}: {o: Output}) {
	if (o.kind === 'post') return <PostCard o={o} />;
	return <VideoCard o={o} />;
}

function VideoCard({o}: {o: Output}) {
	const v = o.videos.find((x) => x.aspect === '9x16') ?? o.videos[0];
	const [hover, setHover] = useState(false);
	return (
		<Link to={`/gallery/${o.name}`} onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)} className="panel group overflow-hidden transition hover:-translate-y-0.5 hover:border-ink-600">
			<div className="relative aspect-[4/5] bg-ink-950">
				{hover ? (
					<video src={file(v.path)} autoPlay muted loop playsInline className="h-full w-full object-contain" />
				) : (
					v.cover && <img src={file(v.cover)} className="h-full w-full object-contain" />
				)}
				<div className="absolute left-2 top-2 flex gap-1">
					{o.videos.map((x) => (
						<span key={x.aspect} className="rounded-md bg-black/60 px-1.5 py-0.5 font-mono text-[10px]">
							{x.aspect}
						</span>
					))}
				</div>
				{o.language && <span className="absolute right-2 top-2 rounded-md bg-black/60 px-1.5 py-0.5 text-[10px] uppercase">{o.language}</span>}
			</div>
			<div className="p-3">
				<div className="truncate text-sm font-semibold" dir={isRtl(o.title) ? 'rtl' : 'ltr'}>
					{o.title}
				</div>
				<div className="mt-1 flex items-center justify-between text-[11px] text-ink-400">
					<span>
						{o.brand} · {o.date}
						{o.duration ? ` · ${o.duration}s` : ''}
					</span>
					{o.qa.total > 0 && <span style={{color: o.qa.pass === o.qa.total ? '#34d3b4' : '#f5b942'}}>QA {o.qa.pass}/{o.qa.total}</span>}
				</div>
			</div>
		</Link>
	);
}

export default function GalleryPage() {
	const [items, setItems] = useState<Output[] | null>(null);
	const [brand, setBrand] = useState('');
	const [showSmoke, setShowSmoke] = useState(false);
	useEffect(() => {
		api.outputs().then(setItems);
	}, []);
	if (!items) return null;
	const brands = [...new Set(items.map((i) => i.brand))];
	const shown = items.filter((i) => (!brand || i.brand === brand) && (showSmoke || !i.smoke));
	return (
		<div className="space-y-5">
			<div className="flex flex-wrap items-center gap-3">
				<h1 className="mr-auto text-2xl font-extrabold">Gallery</h1>
				<span className="chip" data-on={!brand} onClick={() => setBrand('')}>
					All
				</span>
				{brands.map((b) => (
					<span key={b} className="chip" data-on={brand === b} onClick={() => setBrand(b)}>
						{b}
					</span>
				))}
				<label className="flex items-center gap-2 text-xs text-ink-400">
					<input type="checkbox" checked={showSmoke} onChange={(e) => setShowSmoke(e.target.checked)} /> smoke tests
				</label>
			</div>
			{shown.length ? (
				<div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-5">
					{shown.map((o, i) => (
						<motion.div key={o.name} initial={{opacity: 0, y: 12}} animate={{opacity: 1, y: 0}} transition={{delay: i * 0.03}}>
							<Card o={o} />
						</motion.div>
					))}
				</div>
			) : (
				<Empty icon="🎬" title="Nothing here yet">
					Finished videos and posts land here with their copy, QA report and downloads.
				</Empty>
			)}
		</div>
	);
}

function Copy({text}: {text: string}) {
	const [ok, setOk] = useState(false);
	return (
		<button
			className="btn btn-ghost px-3 py-1 text-xs"
			onClick={() => {
				navigator.clipboard.writeText(text);
				setOk(true);
				setTimeout(() => setOk(false), 1500);
			}}
		>
			{ok ? '✓ Copied' : 'Copy'}
		</button>
	);
}

export function OutputPage() {
	const {name} = useParams();
	const nav = useNavigate();
	const [d, setD] = useState<OutputDetail | null>(null);
	const [aspect, setAspect] = useState('');
	const [tab, setTab] = useState<'post' | 'qa' | 'script' | 'strategy' | 'credits'>('post');
	const [feedback, setFeedback] = useState('');
	useEffect(() => {
		if (name) api.output(name).then((x) => (setD(x), setAspect(x.videos[0]?.aspect ?? '')));
	}, [name]);
	if (!d) return null;
	if (d.kind === 'post') return <PostOutputPage d={d} />;
	const v = d.videos.find((x) => x.aspect === aspect) ?? d.videos[0];
	const portrait = v.aspect === '9x16' || v.aspect === '4x5';
	const qa = d.qa_reports.find((r) => r.video.includes(v.aspect)) ?? d.qa_reports[0];
	return (
		<div className="space-y-5">
			<div className="flex flex-wrap items-center gap-3">
				<Link to="/gallery" className="text-sm text-ink-400 hover:text-ink-100">
					← Gallery
				</Link>
				<h1 className="mr-auto min-w-0 truncate text-2xl font-extrabold" dir={isRtl(d.title) ? 'rtl' : 'ltr'}>
					{d.title}
				</h1>
				{d.videos.map((x) => (
					<span key={x.aspect} className="chip" data-on={x.aspect === v.aspect} onClick={() => setAspect(x.aspect)}>
						{x.aspect}
					</span>
				))}
				<a className="btn btn-ghost" href={file(v.path)} download>
					⬇ Download
				</a>
			</div>
			<div className={`grid gap-5 ${portrait ? 'lg:grid-cols-[400px_1fr]' : ''}`}>
				<div className="panel overflow-hidden bg-black">
					<video key={v.path} src={file(v.path)} controls autoPlay className="mx-auto max-h-[78vh] w-full" poster={file(v.cover)} />
				</div>
				<div className="space-y-4">
					<div className="flex flex-wrap gap-2">
						{(
							[
								['post', '📝 Post copy'],
								['qa', '🔍 QA'],
								['script', '✍️ Script'],
								['strategy', '🧠 Strategy'],
								['credits', '©️ Credits'],
							] as const
						).map(([k, l]) => (
							<span key={k} className="chip" data-on={tab === k} onClick={() => setTab(k)}>
								{l}
							</span>
						))}
					</div>
					{tab === 'post' &&
						(d.post.length ? (
							d.post.map((p) => (
								<div key={p.title} className="panel p-4">
									<div className="mb-2 flex items-center justify-between">
										<div className="font-semibold">{p.title}</div>
										<Copy text={p.text} />
									</div>
									<div className="whitespace-pre-line text-sm leading-relaxed text-ink-300" dir={isRtl(p.text) ? 'rtl' : 'ltr'}>
										{p.text}
									</div>
								</div>
							))
						) : (
							<div className="panel p-4 text-sm text-ink-400">No post.md for this video yet.</div>
						))}
					{tab === 'qa' && qa && (
						<div className="space-y-4">
							<div className="panel p-4">
								<div className="flex flex-wrap gap-2">
									{qa.checks.map((c) => (
										<span key={c.name} className="chip" title={c.detail} style={{borderColor: c.ok ? '#34d3b466' : '#f5b94266', color: c.ok ? '#34d3b4' : '#f5b942'}}>
											{c.ok ? '✓' : '!'} {c.name}
										</span>
									))}
								</div>
								<div className="mt-3 space-y-1 text-xs text-ink-400">
									{qa.checks.map((c) => (
										<div key={c.name}>
											<b className="text-ink-300">{c.name}</b>: {c.detail}
										</div>
									))}
								</div>
							</div>
							{qa.asr && qa.asr.length > 0 && (
								<div className="panel p-4">
									<div className="label mb-2">What the voice actually said (Whisper)</div>
									{qa.asr.map((a) => (
										<div key={a.id} className="flex items-center gap-3 py-1 text-sm">
											<span className="w-28 shrink-0 font-mono text-xs text-ink-400">{a.id}</span>
											<div className="h-1.5 w-24 shrink-0 overflow-hidden rounded-full bg-ink-700">
												<div className="h-full" style={{width: `${a.match * 100}%`, background: a.match > 0.7 ? '#34d3b4' : '#f5b942'}} />
											</div>
											<span className="truncate text-ink-300" dir={isRtl(a.heard) ? 'rtl' : 'ltr'}>
												{a.heard}
											</span>
										</div>
									))}
								</div>
							)}
							{qa.contact_sheet && <img src={file(qa.contact_sheet)} className="w-full rounded-xl border border-ink-700" />}
						</div>
					)}
					{tab === 'script' && (
						<div className="panel space-y-2 p-4">
							{(d.storyboard?.scenes ?? []).map((sc) => (
								<div key={sc.id} className="flex gap-3 border-b border-ink-800 pb-2 text-sm">
									<span className="w-32 shrink-0 font-mono text-xs text-ink-400">
										{sc.id}
										<br />
										{sc.type}
									</span>
									<span className="text-ink-300" dir={isRtl(sc.vo) ? 'rtl' : 'ltr'}>
										{sc.vo}
									</span>
								</div>
							))}
						</div>
					)}
					{tab === 'strategy' && <pre className="panel whitespace-pre-wrap p-4 text-sm text-ink-300">{d.strategy || 'No strategy.md saved.'}</pre>}
					{tab === 'credits' && <pre className="panel whitespace-pre-wrap p-4 text-sm text-ink-300">{d.credits}</pre>}

					<div className="panel border-violet/30 p-4">
						<div className="label mb-2 !text-violet">Request changes</div>
						<textarea className="field text-sm" rows={2} placeholder="e.g. Make the hook shorter, use a female voice, change the CTA to 'Book a demo'" value={feedback} onChange={(e) => setFeedback(e.target.value)} />
						<button className="btn btn-primary mt-2" disabled={!feedback.trim()} onClick={async () => nav(`/runs/${(await api.revise(d.name, feedback)).id}`)}>
							🔁 Revise this video
						</button>
					</div>
				</div>
			</div>
		</div>
	);
}

function PostOutputPage({d}: {d: OutputDetail}) {
	const nav = useNavigate();
	const [tab, setTab] = useState<'post' | 'brief' | 'credits'>('post');
	const [feedback, setFeedback] = useState('');
	const [busy, setBusy] = useState(false);
	const spec = d.post_spec;
	const variant = spec?.variants?.[0];
	const images = d.images ?? [];
	const motionVideo = d.videos?.[0];
	const aspect = spec?.aspect ?? '4x5';
	const wide = aspect === '16x9';
	return (
		<div className="space-y-5">
			<div className="flex flex-wrap items-center gap-3">
				<Link to="/gallery" className="text-sm text-ink-400 hover:text-ink-100">
					← Gallery
				</Link>
				<h1 className="mr-auto min-w-0 truncate text-2xl font-extrabold" dir={isRtl(d.title) ? 'rtl' : 'ltr'}>
					{d.title}
				</h1>
				{d.pdf && (
					<a className="btn btn-primary" href={file(d.pdf)} download>
						⬇ Carousel PDF
					</a>
				)}
				{images.length === 1 && (
					<a className="btn btn-primary" href={file(images[0])} download>
						⬇ Image
					</a>
				)}
			</div>
			<div className={`grid gap-5 ${wide ? '' : 'lg:grid-cols-[460px_1fr]'}`}>
				<div className="space-y-3">
					<div className="panel p-3">
						<SlideViewer slides={images} aspect={aspect} />
					</div>
					{images.length > 1 && (
						<div className="flex flex-wrap gap-2">
							{images.map((im, i) => (
								<a key={im} href={file(im)} download className={`panel w-16 overflow-hidden p-0.5 ${ASPECT_CLASS[aspect] ?? ''}`} title={`Download slide ${i + 1}`}>
									<img src={file(im)} className="h-full w-full rounded object-cover" />
								</a>
							))}
						</div>
					)}
					{motionVideo && (
						<div className="panel overflow-hidden bg-black">
							<div className="label px-3 pt-2">Animated version</div>
							<video src={file(motionVideo.path)} controls className="w-full" />
							<a className="btn btn-ghost m-2" href={file(motionVideo.path)} download>
								⬇ MP4
							</a>
						</div>
					)}
				</div>
				<div className="space-y-4">
					{variant && (
						<div className="panel p-4 text-sm">
							<div className="label mb-1">Angle</div>
							<div className="font-semibold" dir={isRtl(variant.angle) ? 'rtl' : 'ltr'}>
								{variant.angle}
							</div>
							<div className="mt-1 text-xs text-ink-400">
								{spec?.brand} · {aspect.replace('x', ':')} · {spec?.language} · {variant.format === 'carousel' ? `carousel, ${variant.slides.length} slides` : 'single image'}
							</div>
						</div>
					)}
					<div className="flex flex-wrap gap-2">
						{(
							[
								['post', '📝 Post copy'],
								['brief', '📋 Brief'],
								['credits', '©️ Credits'],
							] as const
						).map(([k, l]) => (
							<span key={k} className="chip" data-on={tab === k} onClick={() => setTab(k)}>
								{l}
							</span>
						))}
					</div>
					{tab === 'post' &&
						(d.post.length ? (
							d.post.map((p) => (
								<div key={p.title} className="panel p-4">
									<div className="mb-2 flex items-center justify-between">
										<div className="font-semibold">{p.title}</div>
										<Copy text={p.text} />
									</div>
									<div className="whitespace-pre-line text-sm leading-relaxed text-ink-300" dir={isRtl(p.text) ? 'rtl' : 'ltr'}>
										{p.text}
									</div>
								</div>
							))
						) : (
							<div className="panel p-4 text-sm text-ink-400">No post.md saved.</div>
						))}
					{tab === 'brief' && <pre className="panel whitespace-pre-wrap p-4 text-sm text-ink-300">{d.brief || 'No brief saved.'}</pre>}
					{tab === 'credits' && <pre className="panel whitespace-pre-wrap p-4 text-sm text-ink-300">{d.credits}</pre>}

					<div className="panel border-violet/30 p-4">
						<div className="label mb-2 !text-violet">Request changes</div>
						<textarea className="field text-sm" rows={2} placeholder="e.g. Lead with the client count, light theme, make it a 5-slide carousel" value={feedback} onChange={(e) => setFeedback(e.target.value)} />
						<button
							className="btn btn-primary mt-2"
							disabled={!feedback.trim() || busy}
							onClick={async () => {
								setBusy(true);
								try {
									nav(`/runs/${(await api.revisePost(d.name, {feedback})).id}`);
								} catch {
									setBusy(false);
								}
							}}
						>
							🔁 Make new options
						</button>
					</div>
				</div>
			</div>
		</div>
	);
}
