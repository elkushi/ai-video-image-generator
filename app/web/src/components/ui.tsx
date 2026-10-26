import {AnimatePresence, motion} from 'motion/react';
import {useRef, useState} from 'react';
import {isRtl, type Job, type Question} from '../lib/api';

export const STATUS_STYLE: Record<Job['status'], {label: string; color: string}> = {
	queued: {label: 'Queued', color: '#7d89a8'},
	running: {label: 'Working', color: '#f5b942'},
	waiting: {label: 'Needs you', color: '#9b7bff'},
	done: {label: 'Done', color: '#34d3b4'},
	error: {label: 'Failed', color: '#ff6b81'},
	cancelled: {label: 'Cancelled', color: '#7d89a8'},
};

export function StatusPill({status}: {status: Job['status']}) {
	const st = STATUS_STYLE[status] ?? STATUS_STYLE.queued;
	return (
		<span className="inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold" style={{borderColor: `${st.color}66`, color: st.color, background: `${st.color}14`}}>
			<motion.span
				className="h-2 w-2 rounded-full"
				style={{background: st.color}}
				animate={status === 'running' || status === 'waiting' ? {opacity: [1, 0.25, 1], scale: [1, 1.4, 1]} : {}}
				transition={{duration: 1.2, repeat: Infinity}}
			/>
			{st.label}
		</span>
	);
}

export type AnswerMap = Record<number, {choice: string[]; other: string}>;

export function QuestionCards({questions, answers, onChange}: {questions: Question[]; answers: AnswerMap; onChange: (a: AnswerMap) => void}) {
	return (
		<div className="space-y-4">
			{questions.map((q, qi) => {
				const a = answers[qi] ?? {choice: [], other: ''};
				const set = (patch: Partial<typeof a>) => onChange({...answers, [qi]: {...a, ...patch}});
				return (
					<motion.div key={qi} initial={{opacity: 0, y: 14}} animate={{opacity: 1, y: 0}} transition={{delay: qi * 0.08}} className="panel p-5">
						<div className="mb-1 flex items-center gap-2">
							<span className="rounded-md bg-violet/15 px-2 py-0.5 text-[11px] font-bold uppercase tracking-wider text-violet">{q.header}</span>
							{q.multiSelect && <span className="text-[11px] text-ink-400">pick any</span>}
						</div>
						<div className="mb-3 text-[15px] font-semibold text-ink-100" dir={isRtl(q.question) ? 'rtl' : 'ltr'}>
							{q.question}
						</div>
						<div className="grid gap-2 sm:grid-cols-2">
							{q.options.map((o) => {
								const on = a.choice.includes(o.label);
								return (
									<button
										key={o.label}
										type="button"
										onClick={() => set({choice: q.multiSelect ? (on ? a.choice.filter((c) => c !== o.label) : [...a.choice, o.label]) : on ? [] : [o.label]})}
										className="rounded-xl border p-3 text-left transition"
										style={{borderColor: on ? '#f5b942' : '#2e3956', background: on ? '#f5b94214' : '#0c1019'}}
									>
										<div className="flex items-start gap-2">
											<span className="mt-0.5 grid h-4 w-4 shrink-0 place-items-center rounded-full border" style={{borderColor: on ? '#f5b942' : '#56607c'}}>
												{on && <span className="h-2 w-2 rounded-full bg-amber" />}
											</span>
											<div>
												<div className={`text-sm font-semibold ${on ? 'text-amber' : 'text-ink-100'}`} dir={isRtl(o.label) ? 'rtl' : 'ltr'}>
													{o.label}
												</div>
												{o.description && <div className="mt-0.5 text-xs leading-snug text-ink-400">{o.description}</div>}
											</div>
										</div>
									</button>
								);
							})}
						</div>
						<input className="field mt-3 text-sm" placeholder="Or type your own answer…" value={a.other} onChange={(e) => set({other: e.target.value})} />
					</motion.div>
				);
			})}
		</div>
	);
}

export const answerText = (_q: Question, a?: {choice: string[]; other: string}) =>
	[...(a?.choice ?? []).map((c) => c.replace(/\s*\(Recommended\)\s*$/i, '')), a?.other?.trim()].filter(Boolean).join('; ');

export function Dropzone({onFiles, busy}: {onFiles: (f: File[]) => void; busy?: boolean}) {
	const [over, setOver] = useState(false);
	const ref = useRef<HTMLInputElement>(null);
	return (
		<div
			onDragOver={(e) => {
				e.preventDefault();
				setOver(true);
			}}
			onDragLeave={() => setOver(false)}
			onDrop={(e) => {
				e.preventDefault();
				setOver(false);
				onFiles([...e.dataTransfer.files]);
			}}
			onClick={() => ref.current?.click()}
			className="cursor-pointer rounded-2xl border-2 border-dashed p-5 text-center transition"
			style={{borderColor: over ? '#f5b942' : '#2e3956', background: over ? '#f5b9420d' : 'transparent'}}
		>
			<input ref={ref} type="file" multiple hidden onChange={(e) => onFiles([...(e.target.files ?? [])])} />
			<div className="text-2xl">{busy ? '⏳' : '📎'}</div>
			<div className="mt-1 text-sm font-semibold text-ink-100">{busy ? 'Uploading…' : 'Drop brand guidelines, logos, product photos, screenshots'}</div>
			<div className="text-xs text-ink-400">PDF, PNG, SVG, JPG, fonts, MP4: Claude reads them all</div>
		</div>
	);
}

export function Thinking({label}: {label: string}) {
	return (
		<div className="panel flex items-center gap-4 p-5">
			<div className="relative h-12 w-12">
				{[0, 1, 2].map((i) => (
					<motion.span
						key={i}
						className="absolute inset-0 rounded-full border-2 border-violet"
						animate={{scale: [0.6, 1.4], opacity: [0.8, 0]}}
						transition={{duration: 1.6, repeat: Infinity, delay: i * 0.5}}
					/>
				))}
				<span className="absolute inset-0 grid place-items-center text-xl">🧠</span>
			</div>
			<div>
				<div className="font-semibold text-ink-100">{label}</div>
				<div className="text-sm text-ink-400">It reads the brand profile, the playbook and your files, then picks the questions that matter.</div>
			</div>
		</div>
	);
}

export function Empty({icon, title, children}: {icon: string; title: string; children?: React.ReactNode}) {
	return (
		<div className="panel grid place-items-center p-12 text-center">
			<div className="text-4xl">{icon}</div>
			<div className="mt-2 text-lg font-semibold">{title}</div>
			<div className="mt-1 max-w-md text-sm text-ink-400">{children}</div>
		</div>
	);
}

export function Toasts({items}: {items: {id: string; text: string; color?: string}[]}) {
	return (
		<div className="pointer-events-none fixed bottom-20 right-4 z-50 space-y-2 md:bottom-5 md:right-5">
			<AnimatePresence>
				{items.map((t) => (
					<motion.div key={t.id} initial={{opacity: 0, x: 40}} animate={{opacity: 1, x: 0}} exit={{opacity: 0, x: 40}} className="panel px-4 py-3 text-sm" style={{borderColor: t.color}}>
						{t.text}
					</motion.div>
				))}
			</AnimatePresence>
		</div>
	);
}
