// Brief → (optional) smart questions → job. A video, a series of user-given topics, or a social post (3 variants).
import {AnimatePresence, motion} from 'motion/react';
import {useEffect, useMemo, useState} from 'react';
import {useNavigate, useSearchParams} from 'react-router-dom';
import {answerText, Dropzone, QuestionCards, Thinking, type AnswerMap} from '../components/ui';
import {api, file, type Brand, type Intake} from '../lib/api';

const GOALS = ['promo', 'educational', 'event', 'story', 'announcement', 'tutorial'];
const PLATFORMS = ['LinkedIn', 'Instagram', 'TikTok', 'YouTube', 'Website'];
const LANGS: [string, string][] = [
	['en', 'English'],
	['ar', 'العربية'],
	['ru', 'Русский'],
];
const LENGTHS = [15, 30, 45, 60, 90];
const STYLES = ['motion graphics', 'product shots', 'screen demo', 'stock', 'AI story', 'presenter'];
const POST_GOALS = ['educational', 'promo', 'announcement', 'event', 'thought leadership', 'case study', 'hiring'];
const POST_PLATFORMS: [string, string][] = [
	['linkedin', 'LinkedIn'],
	['instagram', 'Instagram'],
	['facebook', 'Facebook'],
	['x', 'X'],
];
const POST_FORMATS: [string, string][] = [
	['auto', 'Let Claude decide'],
	['single', 'Single image'],
	['carousel', 'Carousel'],
];
const ASPECTS: [string, string][] = [
	['4x5', '4:5 feed'],
	['1x1', '1:1 square'],
	['9x16', '9:16 story'],
	['16x9', '16:9 wide'],
];
type Mode = 'single' | 'series' | 'post';

function Chips<T extends string | number>({options, value, onChange, multi, render}: {options: T[]; value: T[]; onChange: (v: T[]) => void; multi?: boolean; render?: (o: T) => string}) {
	return (
		<div className="flex flex-wrap gap-2">
			{options.map((o) => {
				const on = value.includes(o);
				return (
					<span key={String(o)} className="chip" data-on={on} onClick={() => onChange(multi ? (on ? value.filter((v) => v !== o) : [...value, o]) : on ? [] : [o])}>
						{render ? render(o) : String(o)}
					</span>
				);
			})}
		</div>
	);
}

export default function CreatePage() {
	const nav = useNavigate();
	const [params] = useSearchParams();
	const [brands, setBrands] = useState<Brand[]>([]);
	const [brand, setBrand] = useState<string>(params.get('brand') ?? '');
	const [newBrand, setNewBrand] = useState({name: '', website: '', notes: ''});
	const [mode, setMode] = useState<Mode>(() => (['single', 'series', 'post'].includes(params.get('mode') ?? '') ? (params.get('mode') as Mode) : 'single'));
	const [postPlatforms, setPostPlatforms] = useState<string[]>(['linkedin']);
	const [postFormat, setPostFormat] = useState<string[]>(['auto']);
	const [aspect, setAspect] = useState<string[]>(['4x5']);
	const [motionToo, setMotionToo] = useState(false);
	const [topic, setTopic] = useState('');
	const [topics, setTopics] = useState<string[]>(['', '', '']);
	const [goal, setGoal] = useState<string[]>([]);
	const [platforms, setPlatforms] = useState<string[]>([]);
	const [lang, setLang] = useState<string[]>([]);
	const [length, setLength] = useState<number[]>([]);
	const [style, setStyle] = useState<string[]>([]);
	const [more, setMore] = useState(false);
	const [mustSay, setMustSay] = useState('');
	const [cta, setCta] = useState('');
	const [event, setEvent] = useState('');
	const [uploads, setUploads] = useState<{name: string; path: string; size: number}[]>([]);
	const [uploading, setUploading] = useState(false);
	const [draft] = useState(() => Math.random().toString(36).slice(2, 10));
	const [phase, setPhase] = useState<'brief' | 'thinking' | 'questions' | 'starting'>('brief');
	const [intake, setIntake] = useState<Intake | null>(null);
	const [answers, setAnswers] = useState<AnswerMap>({});
	const [understood, setUnderstood] = useState('');
	const [err, setErr] = useState('');

	useEffect(() => {
		api.brands().then((b) => {
			setBrands(b);
			if (b.length && (!brand || (brand !== '__new' && !b.some((x) => x.slug === brand)))) setBrand(b[0].slug);
		});
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, []);

	const isNew = brand === '__new';
	const cleanTopics = topics.map((t) => t.trim()).filter(Boolean);
	const isPost = mode === 'post';
	const ready = (mode === 'series' ? cleanTopics.length >= 1 : topic.trim().length > 3) && (!isNew || newBrand.name.trim()) && (!isPost || postPlatforms.length > 0);

	const brief = useMemo(
		() => ({
			brand: isNew ? '' : brand,
			new_brand: isNew ? newBrand : null,
			topic: mode === 'series' ? '' : topic.trim(),
			topics: mode === 'series' ? cleanTopics : [],
			goal: goal[0] ?? '',
			platforms: isPost ? postPlatforms : platforms,
			language: lang.join(', '),
			length_s: isPost ? null : length[0] ?? null,
			style: isPost ? '' : style.join(', '),
			must_say: mustSay,
			cta,
			event,
			uploads: uploads.map((u) => u.path),
			...(isPost ? {post_format: postFormat[0] ?? 'auto', aspect: aspect[0] ?? '4x5', motion: motionToo} : {}),
		}),
		[isNew, brand, newBrand, mode, isPost, topic, cleanTopics, goal, platforms, postPlatforms, lang, length, style, mustSay, cta, event, uploads, postFormat, aspect, motionToo],
	);

	const onFiles = async (fs: File[]) => {
		if (!fs.length) return;
		setUploading(true);
		try {
			const r = await api.upload(fs, draft);
			setUploads((u) => [...u, ...r.files]);
		} catch (e) {
			setErr(String(e));
		}
		setUploading(false);
	};

	const ask = async () => {
		setErr('');
		setPhase('thinking');
		try {
			const r = await api.intake({...brief, kind: isPost ? 'post' : mode === 'series' ? 'series' : 'video'});
			const df = (r.data.defaults ?? {}) as Record<string, unknown>;
			if (isPost) {
				if (typeof df.aspect === 'string' && aspect[0] === '4x5' && ASPECTS.some((a) => a[0] === df.aspect)) setAspect([df.aspect]);
				if (typeof df.post_format === 'string' && postFormat[0] === 'auto' && POST_FORMATS.some((f) => f[0] === df.post_format)) setPostFormat([df.post_format]);
			}
			setIntake(r.data);
			setUnderstood(r.data.understood);
			setAnswers({});
			setPhase(r.data.questions.length ? 'questions' : 'questions');
		} catch (e) {
			setErr(String(e));
			setPhase('brief');
		}
	};

	const make = async (withAnswers: boolean) => {
		setPhase('starting');
		setErr('');
		try {
			const ans = withAnswers && intake ? intake.questions.map((q, i) => ({question: q.question, answer: answerText(q, answers[i])})).filter((a) => a.answer) : [];
			const body = {...brief, answers: ans, understood: withAnswers ? understood : ''};
			const job = isPost ? await api.makePost(body) : await api.makeVideo(body);
			nav(`/runs/${job.id}`);
		} catch (e) {
			setErr(String(e));
			setPhase(withAnswers ? 'questions' : 'brief');
		}
	};

	const sel = brands.find((b) => b.slug === brand);
	return (
		<div className="grid gap-7 xl:grid-cols-[1fr_380px]">
			<div className="space-y-6">
				<header>
					<h1 className="text-3xl font-extrabold tracking-tight">
						What should we make <span className="text-amber">today</span>?
					</h1>
					<p className="mt-1.5 text-ink-400">
						{isPost
							? 'Describe the post in your own words. Your marketing team asks a few smart questions, then writes and designs 3 on-brand options. You pick one.'
							: "Describe it in your own words. Claude's strategist asks a few smart questions, then the agents and tools make the finished video while you watch."}
					</p>
				</header>

				<section className="panel p-5">
					<div className="label mb-3">Brand</div>
					<div className="grid grid-cols-2 gap-3 md:grid-cols-4">
						{brands.map((b) => (
							<button key={b.slug} onClick={() => setBrand(b.slug)} className="rounded-2xl border p-3 text-left transition" style={{borderColor: brand === b.slug ? '#f5b942' : '#212a40', background: brand === b.slug ? '#f5b94210' : '#0c1019'}}>
								<div className="mb-2 flex h-10 items-center rounded-lg px-2" style={{background: b.colors.dark ?? '#111'}}>
									{b.logo ? <img src={file(b.logo)} className="max-h-6 max-w-full object-contain" /> : <span className="font-bold" style={{color: b.colors.accent ?? '#fff'}}>{b.name}</span>}
								</div>
								<div className="text-sm font-semibold">{b.name}</div>
								<div className="mt-1 flex gap-1">
									{['primary', 'secondary', 'accent', 'dark'].map((k) => b.colors[k] && <span key={k} className="h-3 w-3 rounded-full border border-white/10" style={{background: b.colors[k]}} />)}
									<span className="ml-auto text-[11px] text-ink-400">{b.videos} videos · {b.posts ?? 0} posts</span>
								</div>
							</button>
						))}
						<button onClick={() => setBrand('__new')} className="grid place-items-center rounded-2xl border border-dashed p-3 text-sm transition" style={{borderColor: isNew ? '#f5b942' : '#2e3956', color: isNew ? '#f5b942' : '#7d89a8'}}>
							<div className="text-2xl">＋</div>
							New brand
						</button>
					</div>
					<AnimatePresence>
						{isNew && (
							<motion.div initial={{height: 0, opacity: 0}} animate={{height: 'auto', opacity: 1}} exit={{height: 0, opacity: 0}} className="overflow-hidden">
								<div className="mt-4 grid gap-3 md:grid-cols-2">
									<input className="field" placeholder="Brand or product name" value={newBrand.name} onChange={(e) => setNewBrand({...newBrand, name: e.target.value})} />
									<input className="field" placeholder="Website (optional)" value={newBrand.website} onChange={(e) => setNewBrand({...newBrand, website: e.target.value})} />
									<textarea className="field md:col-span-2" rows={2} placeholder="What is it, who is it for, tone, words to avoid… (drop the brand guidelines below)" value={newBrand.notes} onChange={(e) => setNewBrand({...newBrand, notes: e.target.value})} />
								</div>
							</motion.div>
						)}
					</AnimatePresence>
				</section>

				<section className="panel p-5">
					<div className="mb-3 flex items-center justify-between">
						<div className="label">{mode === 'single' ? 'The video' : mode === 'post' ? 'The post' : 'The series: your topics, in order'}</div>
						<div className="flex rounded-xl border border-ink-700 p-1 text-sm">
							{(['single', 'series', 'post'] as const).map((m) => (
								<button key={m} onClick={() => setMode(m)} className={`rounded-lg px-3 py-1.5 font-medium transition ${mode === m ? 'bg-ink-700 text-ink-100' : 'text-ink-400'}`}>
									{m === 'single' ? '🎬 Video' : m === 'series' ? '📚 Series' : '🖼️ Post'}
								</button>
							))}
						</div>
					</div>
					{mode !== 'series' ? (
						<textarea
							className="field text-[15px]"
							rows={3}
							placeholder={isPost ? 'e.g. A LinkedIn carousel on why one channel is not enough for login codes, with our uptime number' : "e.g. A 30-second Reel on planning your week in five minutes"}
							value={topic}
							onChange={(e) => setTopic(e.target.value)}
						/>
					) : (
						<div className="space-y-2">
							{topics.map((t, i) => (
								<motion.div key={i} layout className="flex items-center gap-2">
									<span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-ink-800 text-sm font-bold text-amber">{i + 1}</span>
									<input className="field" placeholder={['e.g. Plan your week in five minutes', 'e.g. The margin method', 'e.g. One notebook, not five'][i] ?? 'Next topic'} value={t} onChange={(e) => setTopics(topics.map((x, j) => (j === i ? e.target.value : x)))} />
									<button className="btn btn-ghost px-3" onClick={() => setTopics(topics.filter((_, j) => j !== i))} disabled={topics.length <= 1}>
										✕
									</button>
								</motion.div>
							))}
							<button className="btn btn-ghost" onClick={() => setTopics([...topics, ''])} disabled={topics.length >= 10}>
								＋ Add topic
							</button>
							<p className="text-xs text-ink-400">Claude asks the questions once for the whole series, writes a series bible and every script, then produces each episode.</p>
						</div>
					)}

					{isPost ? (
						<div className="mt-5 grid gap-5 md:grid-cols-2">
							<div>
								<div className="label mb-2">Where</div>
								<Chips options={POST_PLATFORMS.map((p) => p[0])} value={postPlatforms} onChange={setPostPlatforms} multi render={(o) => POST_PLATFORMS.find((p) => p[0] === o)![1]} />
							</div>
							<div>
								<div className="label mb-2">Goal</div>
								<Chips options={POST_GOALS} value={goal} onChange={setGoal} />
							</div>
							<div>
								<div className="label mb-2">Format</div>
								<Chips options={POST_FORMATS.map((f) => f[0])} value={postFormat} onChange={(v) => setPostFormat(v.length ? v : ['auto'])} render={(o) => POST_FORMATS.find((f) => f[0] === o)![1]} />
							</div>
							<div>
								<div className="label mb-2">Size</div>
								<Chips options={ASPECTS.map((a) => a[0])} value={aspect} onChange={(v) => setAspect(v.length ? v : ['4x5'])} render={(o) => ASPECTS.find((a) => a[0] === o)![1]} />
							</div>
							<div>
								<div className="label mb-2">Language</div>
								<Chips options={LANGS.map((l) => l[0])} value={lang} onChange={setLang} render={(o) => LANGS.find((l) => l[0] === o)![1]} />
							</div>
							<div>
								<div className="label mb-2">Extras</div>
								<label className="chip" data-on={motionToo}>
									<input type="checkbox" className="hidden" checked={motionToo} onChange={(e) => setMotionToo(e.target.checked)} />
									🎞️ Also make an animated version
								</label>
							</div>
						</div>
					) : (
					<div className="mt-5 grid gap-5 md:grid-cols-2">
						<div>
							<div className="label mb-2">Goal</div>
							<Chips options={GOALS} value={goal} onChange={setGoal} />
						</div>
						<div>
							<div className="label mb-2">Where</div>
							<Chips options={PLATFORMS} value={platforms} onChange={setPlatforms} multi />
						</div>
						<div>
							<div className="label mb-2">Language</div>
							<Chips options={LANGS.map((l) => l[0])} value={lang} onChange={setLang} multi render={(o) => LANGS.find((l) => l[0] === o)![1]} />
						</div>
						<div>
							<div className="label mb-2">Length</div>
							<Chips options={LENGTHS} value={length} onChange={setLength} render={(o) => `${o}s`} />
						</div>
						<div className="md:col-span-2">
							<div className="label mb-2">Style</div>
							<Chips options={STYLES} value={style} onChange={setStyle} multi />
						</div>
					</div>
					)}
					<button className="mt-4 text-sm text-ink-400 hover:text-ink-100" onClick={() => setMore(!more)}>
						{more ? '▾' : '▸'} Must-say points, CTA{isPost ? ', link' : ''}, event details
					</button>
					{more && (
						<div className="mt-3 grid gap-3 md:grid-cols-3">
							<textarea className="field" rows={2} placeholder="Must say (facts, offer, feature)" value={mustSay} onChange={(e) => setMustSay(e.target.value)} />
							<textarea className="field" rows={2} placeholder="CTA / link" value={cta} onChange={(e) => setCta(e.target.value)} />
							<textarea className="field" rows={2} placeholder="Event: title, date, time + timezone, link, speakers" value={event} onChange={(e) => setEvent(e.target.value)} />
						</div>
					)}
				</section>

				<section className="panel p-5">
					<div className="label mb-3">Files (optional)</div>
					<Dropzone onFiles={onFiles} busy={uploading} />
					{uploads.length > 0 && (
						<div className="mt-3 flex flex-wrap gap-2">
							{uploads.map((u) => (
								<span key={u.path} className="chip" data-on>
									📄 {u.name} <span className="text-ink-400">{(u.size / 1024 / 1024).toFixed(1)} MB</span>
									<span onClick={() => setUploads(uploads.filter((x) => x.path !== u.path))}>✕</span>
								</span>
							))}
						</div>
					)}
				</section>

				{err && <div className="rounded-xl border border-rose/50 bg-rose/10 p-3 text-sm text-rose">{err}</div>}

				<AnimatePresence mode="wait">
					{phase === 'brief' && (
						<motion.div key="b" initial={{opacity: 0}} animate={{opacity: 1}} exit={{opacity: 0}} className="flex flex-wrap gap-3">
							<button className="btn btn-primary text-[15px]" disabled={!ready} onClick={ask}>
								💬 Ask me the right questions first
							</button>
							<button className="btn btn-ghost" disabled={!ready} onClick={() => make(false)}>
								{isPost ? 'Skip questions: make 3 options now' : 'Skip questions: make it now'}
							</button>
						</motion.div>
					)}
					{phase === 'thinking' && (
						<motion.div key="t" initial={{opacity: 0, y: 10}} animate={{opacity: 1, y: 0}} exit={{opacity: 0}}>
							<Thinking label={isPost ? 'Your marketing team is reading the brief…' : 'The strategist is reading your brief…'} />
						</motion.div>
					)}
					{(phase === 'questions' || phase === 'starting') && intake && (
						<motion.div key="q" initial={{opacity: 0, y: 10}} animate={{opacity: 1, y: 0}} className="space-y-4">
							<div className="panel border-violet/40 p-5">
								<div className="label mb-2 !text-violet">What I understood</div>
								<textarea className="field text-[14px] leading-relaxed" rows={3} value={understood} onChange={(e) => setUnderstood(e.target.value)} />
							</div>
							{intake.questions.length ? (
								<QuestionCards questions={intake.questions} answers={answers} onChange={setAnswers} />
							) : (
								<div className="panel p-4 text-sm text-ink-300">No questions needed: the brief and brand profile cover everything.</div>
							)}
							<div className="flex gap-3">
								<button className="btn btn-primary text-[15px]" onClick={() => make(true)} disabled={phase === 'starting'}>
									{mode === 'series' ? `🏭 Make the series (${cleanTopics.length} episodes)` : isPost ? '🖼️ Make 3 post options' : '🏭 Make the video'}
								</button>
								<button className="btn btn-ghost" onClick={() => setPhase('brief')}>
									Back to the brief
								</button>
							</div>
							<p className="text-xs text-ink-400">Unanswered questions use the recommended option.</p>
						</motion.div>
					)}
				</AnimatePresence>
			</div>

			<aside className="space-y-4">
				<div className="panel p-5">
					<div className="label mb-3">How it works</div>
					<ol className="space-y-3 text-sm">
						{(isPost
							? [
									['💬', 'Smart questions', 'Only what changes the post: angle, format, facts, CTA'],
									['✍️', 'Copywriter', '3 different angles with copy for every platform'],
									['🎨', 'Designer', 'Each angle becomes on-brand slides from your brand kit'],
									['🖼️', 'HyperFrames', 'Renders every slide to PNG (AI photo when it helps, free)'],
									['🧐', 'QA', 'Legibility, contrast, brand rules, facts'],
									['👆', 'You pick', 'Edit the copy, pick one: PNGs, carousel PDF and copy in output/'],
								]
							: [
							['💬', 'Smart questions', 'The strategist asks only what changes the result'],
							['🧠', 'Strategy', 'Audience, angle, 3 hooks, CTA, platforms'],
							['✍️', 'Script', 'Scene-by-scene voiceover and on-screen text'],
							['🎙️', 'Voice, visuals, music', 'Free neural voice, local AI images, synth music, SFX'],
							['🔥', 'Render', 'Remotion renders every aspect ratio'],
							['🧐', 'QA', 'Frames, transcript and hook score: SHIP or FIX'],
							['🚚', 'Delivery', 'MP4s, covers and post copy in output/'],
								]
						).map(([i, t, d], k) => (
							<li key={k} className="flex gap-3">
								<span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-ink-800">{i}</span>
								<div>
									<div className="font-semibold">{t}</div>
									<div className="text-ink-400">{d}</div>
								</div>
							</li>
						))}
					</ol>
				</div>
				{sel && (
					<div className="panel p-5 text-sm">
						<div className="label mb-2">Brand voices</div>
						{Object.entries(sel.voices).map(([l, v]) => (
							<div key={l} className="flex justify-between py-0.5">
								<span className="text-ink-400">{l}</span>
								<span className="font-mono text-xs">{v}</span>
							</div>
						))}
					</div>
				)}
			</aside>
		</div>
	);
}
