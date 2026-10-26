// The illustrated "factory floor": one station per agent/tool, a conveyor belt, and the video box riding
// from station to station as the real pipeline advances. Driven only by PipelineState.
import {AnimatePresence, motion} from 'motion/react';
import {fmtSec, isRtl} from '../lib/api';
import {NODE, NODES, nodeDef, nodesFor} from '../lib/nodes';
import {focusNode, nodeSeconds, type PipelineState} from '../lib/pipeline';
import {StationArt} from './art/StationArt';

const SMALL = new Set(['validate', 'props', 'intake']);

export function stationsFor(kind: string, s: PipelineState): string[] {
	const ids = new Set([...nodesFor(kind), ...s.order.filter((id) => NODE[id])]);
	return NODES.filter((n) => ids.has(n.id))
		.sort((a, b) => a.col - b.col || a.row - b.row)
		.map((n) => n.id);
}

// what the box carries after each station
const CARGO: Record<string, string> = {
	brand: 'brand kit',
	planner: 'plan',
	strategist: 'strategy',
	scriptwriter: 'script',
	validate: 'script ✓',
	voice: 'voice',
	images: 'images',
	clips: 'clips',
	stock: 'footage',
	avatar: 'presenter',
	music: 'music',
	props: 'timeline',
	render: 'video',
	qa: 'video ✓',
	'qa-reviewer': 'approved',
	deliver: 'delivered',
	post: 'post copy',
	'post-copywriter': 'copy ×3',
	'post-designer': 'slides',
};
const CARGO_KIND: Record<string, Record<string, string>> = {
	post: {render: 'PNGs', validate: 'spec ✓', 'qa-reviewer': 'approved', intake: 'brief'},
};

export function FactoryFloor({s, kind}: {s: PipelineState; kind: string}) {
	const ids = stationsFor(kind, s);
	const widths = ids.map((id) => (SMALL.has(id) ? 92 : 150));
	const W = Math.max(1100, widths.reduce((a, b) => a + b, 0) + 80);
	const H = 420;
	const xs: number[] = [];
	widths.reduce((x, w) => (xs.push(x + w / 2), x + w), 40);
	const focus = focusNode(s);
	const fi = focus ? ids.indexOf(focus) : -1;
	const running = s.status === 'running';
	const boxX = fi >= 0 ? xs[fi] : 0;
	const lastThought = [...s.thoughts].reverse().find((t) => t.node === focus || (focus && NODE[focus]?.kind === 'tool'));
	const bubble = focus && s.nodes[focus]?.status === 'active' ? s.nodes[focus]?.detail || lastThought?.text : undefined;
	const now = Date.now();

	return (
		<div className="relative w-full overflow-x-auto scroll-thin">
			<svg viewBox={`0 0 ${W} ${H}`} className="block min-w-[1000px] w-full" style={{height: 'auto'}}>
				<defs>
					<linearGradient id="floor" x1="0" y1="0" x2="0" y2="1">
						<stop offset="0" stopColor="#0d1220" />
						<stop offset="1" stopColor="#090c15" />
					</linearGradient>
					<pattern id="belt-stripes" width="40" height="22" patternUnits="userSpaceOnUse">
						<rect width="40" height="22" fill="#1a2135" />
						<path d="M0 22 L20 0 L30 0 L10 22 Z" fill="#232c45" />
						{running && <animateTransform attributeName="patternTransform" type="translate" from="0 0" to="40 0" dur="0.8s" repeatCount="indefinite" />}
					</pattern>
					<filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
						<feGaussianBlur stdDeviation="10" result="b" />
						<feMerge>
							<feMergeNode in="b" />
							<feMergeNode in="SourceGraphic" />
						</feMerge>
					</filter>
					<pattern id="grid" width="32" height="32" patternUnits="userSpaceOnUse">
						<path d="M32 0 L0 0 0 32" fill="none" stroke="#ffffff06" />
					</pattern>
				</defs>
				<rect width={W} height={H} fill="url(#floor)" />
				<rect width={W} height={H} fill="url(#grid)" />
				{/* wall pipes */}
				<path d={`M20 52 H${W - 20}`} stroke="#1c2438" strokeWidth={10} strokeLinecap="round" />
				{running && (
					<motion.circle r={5} cy={52} fill="#f5b942" filter="url(#glow)" animate={{cx: [20, W - 20]}} transition={{duration: 6, repeat: Infinity, ease: 'linear'}} />
				)}

				{/* belt */}
				<rect x={24} y={318} width={W - 48} height={22} rx={11} fill="url(#belt-stripes)" stroke="#2a3350" />
				{Array.from({length: Math.floor((W - 48) / 60)}).map((_, i) => (
					<circle key={i} cx={54 + i * 60} cy={349} r={6} fill="#151b2c" stroke="#2a3350" />
				))}

				{ids.map((id, i) => {
					const def = nodeDef(id, kind)!;
					const st = s.nodes[id];
					const active = st?.status === 'active';
					const done = st?.status === 'done';
					const err = st?.status === 'error';
					const small = SMALL.has(id);
					const x = xs[i] - (small ? 46 : 75);
					const secs = nodeSeconds(st, now);
					const scale = small ? 0.62 : 1;
					return (
						<g key={id} transform={`translate(${x},0)`}>
							{/* spotlight */}
							<motion.ellipse
								cx={small ? 46 : 75}
								cy={312}
								rx={small ? 40 : 66}
								ry={14}
								fill={def.color}
								animate={{opacity: active ? [0.18, 0.4, 0.18] : done ? 0.12 : 0.04}}
								transition={active ? {duration: 1.4, repeat: Infinity} : {duration: 0.4}}
							/>
							{active && <motion.rect x={4} y={86} width={small ? 84 : 142} height={226} rx={20} fill="none" stroke={def.color} strokeWidth={2} animate={{opacity: [0.2, 0.8, 0.2]}} transition={{duration: 1.4, repeat: Infinity}} />}
							<g transform={`translate(${small ? 2 : 5},${small ? 200 : 158}) scale(${scale})`} opacity={st || active ? 1 : 0.45}>
								<StationArt id={id} color={def.color} active={active} done={done} progress={st?.progress} cargo={kind === 'post' ? 'PNG' : undefined} />
							</g>
							{/* label */}
							<text x={small ? 46 : 75} y={372} textAnchor="middle" fontSize={small ? 12 : 14} fontWeight={700} fill={active ? '#fff' : done ? '#c8d0e4' : '#6b7595'}>
								{def.label}
							</text>
							<text x={small ? 46 : 75} y={390} textAnchor="middle" fontSize={12} fill={err ? '#ff6b81' : active ? def.color : '#56607c'} fontFamily="ui-monospace, monospace">
								{err ? 'failed' : st ? fmtSec(secs) : def.kind === 'agent' ? 'agent' : 'waiting'}
							</text>
							{/* status badge */}
							{done && (
								<motion.g initial={{scale: 0}} animate={{scale: 1}} transition={{type: 'spring', stiffness: 400, damping: 14}} style={{originX: `${small ? 80 : 128}px`, originY: '100px'}}>
									<circle cx={small ? 80 : 128} cy={100} r={11} fill="#34d3b4" />
									<path d={`M${(small ? 80 : 128) - 5} 100 l3.5 3.5 l6 -7`} stroke="#062a22" strokeWidth={2.6} fill="none" strokeLinecap="round" />
								</motion.g>
							)}
							{st?.fallback && (
								<g>
									<rect x={small ? 2 : 8} y={92} width={small ? 60 : 84} height={18} rx={9} fill="#f5b94222" stroke="#f5b942" />
									<text x={small ? 32 : 50} y={105} textAnchor="middle" fontSize={10} fill="#f5b942">
										↪ {st.fallback}
									</text>
								</g>
							)}
							{st?.count && st.count > 1 ? (
								<text x={small ? 10 : 14} y={300} fontSize={11} fill="#7d89a8">
									×{st.count}
								</text>
							) : null}
						</g>
					);
				})}

				{/* the video box riding the belt */}
				{fi >= 0 && (
					<motion.g initial={false} animate={{x: boxX - 34}} transition={{type: 'spring', stiffness: 60, damping: 14}}>
						<motion.g animate={{y: running ? [0, -4, 0] : 0}} transition={running ? {duration: 0.6, repeat: Infinity} : {duration: 0.3}}>
							<rect x={0} y={282} width={68} height={38} rx={6} fill="#c9a46a" stroke="#8c6d3f" strokeWidth={2} />
							<path d="M0 294 H68" stroke="#8c6d3f" strokeWidth={2} />
							<rect x={26} y={282} width={16} height={12} fill="#e3c48e" />
							<text x={34} y={312} textAnchor="middle" fontSize={10} fontWeight={800} fill="#3a2a12">
								{CARGO_KIND[kind]?.[ids[fi]] ?? CARGO[ids[fi]] ?? 'job'}
							</text>
						</motion.g>
					</motion.g>
				)}
			</svg>

			{/* speech bubble for the working station */}
			<AnimatePresence mode="wait">
				{bubble && fi >= 0 && (
					<motion.div
						key={focus + (bubble ?? '').slice(0, 40)}
						initial={{opacity: 0, y: 8, scale: 0.96}}
						animate={{opacity: 1, y: 0, scale: 1}}
						exit={{opacity: 0, y: -6}}
						transition={{duration: 0.25}}
						className="pointer-events-none absolute top-3 max-w-[340px] rounded-2xl border border-ink-600 bg-ink-800/95 px-4 py-2.5 text-[13px] leading-snug text-ink-100 shadow-xl backdrop-blur"
						style={{left: `clamp(8px, calc(${(boxX / W) * 100}% - 170px), calc(100% - 350px))`}}
						dir={isRtl(bubble) ? 'rtl' : 'ltr'}
					>
						<span className="mr-1.5 font-semibold" style={{color: NODE[focus!]?.color}}>
							{nodeDef(focus!, kind)?.label}:
						</span>
						{bubble.length > 220 ? bubble.slice(0, 220) + '…' : bubble}
					</motion.div>
				)}
			</AnimatePresence>
		</div>
	);
}
