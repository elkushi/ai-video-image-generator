import {motion} from 'motion/react';
import {useEffect, useRef, useState} from 'react';
import {NavLink, Route, Routes, useLocation} from 'react-router-dom';
import {Toasts} from './components/ui';
import {api, type Job} from './lib/api';
import {onToast} from './lib/toast';
import BrandsPage, {BrandPage} from './pages/Brands';
import CalendarPage from './pages/Calendar';
import CreatePage from './pages/Create';
import GalleryPage, {OutputPage} from './pages/Gallery';
import RunPage, {RunsPage} from './pages/Runs';
import StatsPage from './pages/Stats';

const NAV = [
	{to: '/', label: 'Create', icon: '✨'},
	{to: '/runs', label: 'Live runs', icon: '🏭'},
	{to: '/gallery', label: 'Gallery', icon: '🎬'},
	{to: '/brands', label: 'Brands', icon: '🎨'},
	{to: '/calendar', label: 'Calendar', icon: '🗓️'},
	{to: '/stats', label: 'Stats', icon: '📈'},
];

export default function App() {
	const [jobs, setJobs] = useState<Job[]>([]);
	const [sys, setSys] = useState<Awaited<ReturnType<typeof api.system>> | null>(null);
	const [toasts, setToasts] = useState<{id: string; text: string; color?: string}[]>([]);
	const prev = useRef<Record<string, string>>({});
	const loc = useLocation();

	useEffect(
		() =>
			onToast((t) => {
				setToasts((x) => [...x, t]);
				setTimeout(() => setToasts((x) => x.filter((y) => y.id !== t.id)), 7000);
			}),
		[],
	);

	useEffect(() => {
		const load = () => {
			api.jobs()
				.then((js) => {
					for (const j of js) {
						const was = prev.current[j.id];
						if (was && was !== j.status && ['done', 'error', 'waiting'].includes(j.status)) {
							const text = j.status === 'done' ? `✅ Finished: ${j.title}` : j.status === 'waiting' ? `💬 Claude has a question: ${j.title}` : `⚠️ Failed: ${j.title}`;
							const id = j.id + j.status;
							setToasts((t) => [...t, {id, text, color: j.status === 'done' ? '#34d3b4' : j.status === 'waiting' ? '#9b7bff' : '#ff6b81'}]);
							setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 6000);
						}
						prev.current[j.id] = j.status;
					}
					setJobs(js);
				})
				.catch(() => {});
			api.system().then(setSys).catch(() => setSys(null));
		};
		load();
		const t = setInterval(load, 4000);
		return () => clearInterval(t);
	}, []);

	const active = jobs.filter((j) => j.status === 'running' || j.status === 'queued' || j.status === 'waiting');
	return (
		<div className="flex h-full">
			<aside className="hidden w-[220px] shrink-0 flex-col border-r border-ink-800 bg-ink-900/60 px-3 py-5 md:flex">
				<div className="mb-7 flex items-center gap-2.5 px-2">
					<motion.div className="grid h-9 w-9 place-items-center rounded-xl bg-amber text-ink-950" animate={{rotate: active.some((j) => j.status === 'running') ? [0, 8, -8, 0] : 0}} transition={{duration: 2, repeat: Infinity}}>
						<svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor">
							<path d="M8 5l11 7-11 7z" />
						</svg>
					</motion.div>
					<div>
						<div className="text-[15px] font-extrabold leading-tight">Factory</div>
						<div className="text-[11px] text-ink-400">free AI marketing team</div>
					</div>
				</div>
				<nav className="space-y-1">
					{NAV.map((n) => (
						<NavLink
							key={n.to}
							to={n.to}
							end={n.to === '/'}
							className={({isActive}) => `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${isActive ? 'bg-ink-800 text-ink-100' : 'text-ink-400 hover:bg-ink-850 hover:text-ink-100'}`}
						>
							<span className="text-base">{n.icon}</span>
							{n.label}
							{n.to === '/runs' && active.length > 0 && (
								<span className="ml-auto rounded-full bg-amber px-2 text-[11px] font-bold text-ink-950">{active.length}</span>
							)}
						</NavLink>
					))}
				</nav>
				<div className="mt-auto space-y-2 px-2 text-[11px] text-ink-400">
					{sys ? (
						<>
							<div className="flex justify-between">
								<span>RAM free</span>
								<span className={sys.ram_free_mb < 1500 ? 'text-rose' : 'text-ink-300'}>{(sys.ram_free_mb / 1024).toFixed(1)} GB</span>
							</div>
							<div className="h-1.5 overflow-hidden rounded-full bg-ink-800">
								<div className="h-full rounded-full bg-teal" style={{width: `${(sys.ram_free_mb / sys.ram_total_mb) * 100}%`}} />
							</div>
							<div className="flex justify-between">
								<span>Disk free</span>
								<span className="text-ink-300">{sys.disk_free_gb} GB</span>
							</div>
							<div className="truncate" title={sys.claude}>
								{sys.claude ? `Claude Code ${sys.claude.split(' ')[0]}` : '⚠️ claude CLI missing'}
							</div>
							<div>Free only · no API key · local</div>
						</>
					) : (
						<div className="text-rose">Backend offline: run ./factory.sh</div>
					)}
				</div>
			</aside>
			<main className="min-w-0 flex-1 overflow-y-auto scroll-thin">
				<motion.div key={loc.pathname.split('/')[1]} initial={{opacity: 0, y: 6}} animate={{opacity: 1, y: 0}} transition={{duration: 0.25}} className="mx-auto max-w-[1500px] px-4 pb-24 pt-5 md:px-8 md:py-7">
					<Routes>
						<Route path="/" element={<CreatePage />} />
						<Route path="/runs" element={<RunsPage jobs={jobs} />} />
						<Route path="/runs/:id" element={<RunPage />} />
						<Route path="/gallery" element={<GalleryPage />} />
						<Route path="/gallery/:name" element={<OutputPage />} />
						<Route path="/brands" element={<BrandsPage />} />
						<Route path="/brands/:slug" element={<BrandPage />} />
						<Route path="/calendar" element={<CalendarPage />} />
						<Route path="/stats" element={<StatsPage />} />
					</Routes>
				</motion.div>
			</main>
			<nav className="fixed inset-x-0 bottom-0 z-40 flex border-t border-ink-800 bg-ink-950/95 backdrop-blur md:hidden" style={{paddingBottom: 'env(safe-area-inset-bottom)'}}>
				{NAV.map((n) => (
					<NavLink
						key={n.to}
						to={n.to}
						end={n.to === '/'}
						className={({isActive}) => `relative flex flex-1 flex-col items-center gap-0.5 py-2 text-[10px] font-medium ${isActive ? 'text-amber' : 'text-ink-400'}`}
					>
						<span className="text-lg leading-none">{n.icon}</span>
						{n.label.replace('Live runs', 'Runs')}
						{n.to === '/runs' && active.length > 0 && (
							<span className="absolute right-[22%] top-1 rounded-full bg-amber px-1.5 text-[9px] font-bold text-ink-950">{active.length}</span>
						)}
					</NavLink>
				))}
			</nav>
			<Toasts items={toasts} />
		</div>
	);
}
