// Hand-drawn SVG stations for the factory floor. Each is drawn in a 140×150 box (origin top-left).
// Agents are little characters at a desk; tools are machines. `active` animates them.
import {motion} from 'motion/react';

type ArtProps = {id: string; color: string; active: boolean; done: boolean; progress?: number; cargo?: string};

const loop = (active: boolean, duration: number, delay = 0) =>
	active ? {duration, repeat: Infinity, ease: 'easeInOut' as const, delay} : {duration: 0.3};

// ---------- a character (agents) ----------
function Character({color, active, done, accessory}: {color: string; active: boolean; done: boolean; accessory: React.ReactNode}) {
	return (
		<g>
			{/* desk */}
			<rect x={18} y={104} width={104} height={10} rx={4} fill="#2a3350" />
			<rect x={26} y={114} width={6} height={24} fill="#222a42" />
			<rect x={108} y={114} width={6} height={24} fill="#222a42" />
			{/* laptop */}
			<rect x={44} y={88} width={52} height={16} rx={3} fill="#3a4566" />
			<motion.rect x={48} y={91} width={44} height={10} rx={2} fill={color} animate={{opacity: active ? [0.35, 0.9, 0.35] : done ? 0.5 : 0.15}} transition={loop(active, 1.6)} />
			{/* body */}
			<motion.g animate={{y: active ? [0, -2.5, 0] : 0}} transition={loop(active, 1.1)}>
				<path d="M46 88 Q70 52 94 88 Z" fill={color} opacity={0.9} />
				{/* head */}
				<circle cx={70} cy={46} r={19} fill="#f3d7b6" />
				<path d="M51 42 Q56 24 72 26 Q88 26 89 42 Q80 34 70 34 Q60 34 51 42Z" fill="#2b2233" />
				{/* eyes (blink) */}
				<motion.g animate={{scaleY: [1, 1, 0.1, 1]}} transition={{duration: 3.2, repeat: Infinity, times: [0, 0.9, 0.95, 1]}} style={{originY: '48px'}}>
					<circle cx={63} cy={48} r={2.3} fill="#1b1b24" />
					<circle cx={77} cy={48} r={2.3} fill="#1b1b24" />
				</motion.g>
				<path d={done ? 'M63 56 Q70 61 77 56' : 'M64 57 Q70 59 76 57'} stroke="#8a4b3c" strokeWidth={2} fill="none" strokeLinecap="round" />
				{accessory}
				{/* typing hands */}
				<motion.circle cx={56} cy={92} r={4.5} fill="#f3d7b6" animate={{y: active ? [0, -3, 0] : 0}} transition={loop(active, 0.28)} />
				<motion.circle cx={84} cy={92} r={4.5} fill="#f3d7b6" animate={{y: active ? [-3, 0, -3] : 0}} transition={loop(active, 0.28)} />
			</motion.g>
		</g>
	);
}

const Glasses = () => (
	<g stroke="#1b1b24" strokeWidth={1.6} fill="none">
		<circle cx={63} cy={48} r={5} />
		<circle cx={77} cy={48} r={5} />
		<path d="M68 48 L72 48" />
	</g>
);

// ---------- machines (tools) ----------
function VoiceBooth({color, active}: ArtProps) {
	return (
		<g>
			<rect x={30} y={30} width={80} height={104} rx={14} fill="#1f2740" stroke="#33406a" />
			<rect x={66} y={70} width={8} height={40} fill="#59627e" />
			<rect x={54} y={108} width={32} height={6} rx={3} fill="#59627e" />
			<rect x={58} y={40} width={24} height={36} rx={12} fill={color} />
			{[0, 1, 2].map((i) => (
				<motion.path
					key={i}
					d={`M${92 + i * 8} ${48 - i * 4} Q${100 + i * 8} 58 ${92 + i * 8} ${68 + i * 4}`}
					stroke={color}
					strokeWidth={2.5}
					fill="none"
					strokeLinecap="round"
					animate={{opacity: active ? [0, 1, 0] : 0.15}}
					transition={loop(active, 1.2, i * 0.2)}
				/>
			))}
			{[0, 1, 2].map((i) => (
				<motion.path
					key={'l' + i}
					d={`M${48 - i * 8} ${48 - i * 4} Q${40 - i * 8} 58 ${48 - i * 8} ${68 + i * 4}`}
					stroke={color}
					strokeWidth={2.5}
					fill="none"
					strokeLinecap="round"
					animate={{opacity: active ? [0, 1, 0] : 0.15}}
					transition={loop(active, 1.2, i * 0.2)}
				/>
			))}
		</g>
	);
}

function ImageLab({color, active, progress}: ArtProps) {
	return (
		<g>
			{/* easel */}
			<path d="M50 130 L66 40 M90 130 L74 40 M70 40 L70 130" stroke="#59627e" strokeWidth={4} strokeLinecap="round" />
			<rect x={34} y={36} width={72} height={58} rx={6} fill="#0e1322" stroke="#3a4566" strokeWidth={2} />
			<clipPath id="canvas-clip">
				<rect x={38} y={40} width={64} height={50} rx={3} />
			</clipPath>
			<g clipPath="url(#canvas-clip)">
				<motion.rect x={38} y={40} width={64} height={50} fill={color} animate={{opacity: active ? [0.15, 0.4, 0.15] : 0.25}} transition={loop(active, 2)} />
				<motion.circle cx={84} cy={54} r={8} fill="#ffe8a3" animate={{opacity: active ? [0.3, 1, 0.3] : 0.8}} transition={loop(active, 2)} />
				<path d="M38 90 L58 66 L72 80 L82 70 L102 90 Z" fill="#2e3b63" />
				{/* scan line = diffusion steps */}
				{active && (
					<motion.rect x={38} width={64} height={3} fill="#fff" opacity={0.6} animate={{y: [40, 88, 40]}} transition={{duration: 2.4, repeat: Infinity, ease: 'linear'}} />
				)}
			</g>
			{/* GPU sparks */}
			{active &&
				[0, 1, 2, 3].map((i) => (
					<motion.circle
						key={i}
						cx={70}
						cy={100}
						r={2}
						fill={color}
						animate={{x: [0, (i - 1.5) * 22], y: [0, -30 - i * 6], opacity: [1, 0]}}
						transition={{duration: 1, repeat: Infinity, delay: i * 0.25}}
					/>
				))}
			{progress != null && progress > 0 && progress < 100 && <rect x={34} y={98} width={(72 * progress) / 100} height={4} rx={2} fill={color} />}
		</g>
	);
}

function RenderOven({color, active, progress = 0}: ArtProps) {
	const pct = Math.round(progress);
	return (
		<g>
			<rect x={22} y={28} width={96} height={108} rx={12} fill="#2a2030" stroke="#4a3550" strokeWidth={2} />
			<rect x={34} y={18} width={14} height={14} fill="#3a2d40" />
			{active &&
				[0, 1, 2].map((i) => (
					<motion.circle key={i} cx={41} cy={16} r={5} fill="#7d89a8" animate={{y: [-0, -26], opacity: [0.5, 0], scale: [0.6, 1.6]}} transition={{duration: 1.8, repeat: Infinity, delay: i * 0.6}} />
				))}
			{/* door window */}
			<rect x={36} y={48} width={68} height={56} rx={8} fill="#140d14" />
			<clipPath id="oven-clip">
				<rect x={36} y={48} width={68} height={56} rx={8} />
			</clipPath>
			<g clipPath="url(#oven-clip)">
				<motion.rect x={36} width={68} y={104 - (56 * pct) / 100} height={(56 * pct) / 100} fill={color} animate={{opacity: active ? [0.55, 0.95, 0.55] : 0.7}} transition={loop(active, 0.9)} />
				{active &&
					[0, 1, 2, 3].map((i) => (
						<motion.path
							key={i}
							d={`M${44 + i * 16} 104 q4 -14 0 -22 q8 8 4 22z`}
							fill="#ffd166"
							animate={{scaleY: [0.7, 1.15, 0.7], opacity: [0.7, 1, 0.7]}}
							style={{originY: '104px'}}
							transition={{duration: 0.6 + i * 0.1, repeat: Infinity}}
						/>
					))}
			</g>
			<text x={70} y={81} textAnchor="middle" fontSize={18} fontWeight={800} fill="#fff">
				{pct}%
			</text>
			<rect x={36} y={112} width={68} height={8} rx={4} fill="#3a2d40" />
			<motion.circle cx={104} cy={124} r={4} fill={active ? '#ff5f5f' : '#5b4a60'} animate={{opacity: active ? [1, 0.3, 1] : 1}} transition={loop(active, 0.8)} />
		</g>
	);
}

function Scanner({color, active}: ArtProps) {
	return (
		<g>
			<path d="M28 136 L28 46 Q70 14 112 46 L112 136" stroke="#3a4566" strokeWidth={10} fill="none" strokeLinecap="round" />
			<path d="M28 136 L28 46 Q70 14 112 46 L112 136" stroke={color} strokeWidth={2} fill="none" opacity={0.6} />
			{active && <motion.rect x={34} width={72} height={3} rx={2} fill={color} animate={{y: [44, 128, 44]}} transition={{duration: 1.6, repeat: Infinity, ease: 'easeInOut'}} />}
			<rect x={48} y={84} width={44} height={30} rx={4} fill="#1a2238" stroke="#33406a" />
			{[0, 1, 2].map((i) => (
				<motion.rect key={i} x={54} y={90 + i * 7} width={24} height={3} rx={1.5} fill={i === 2 ? '#ff6b81' : color} animate={{width: active ? [6, 30, 18] : 24}} transition={loop(active, 1.4, i * 0.2)} />
			))}
		</g>
	);
}

function MusicBox({color, active}: ArtProps) {
	return (
		<g>
			<rect x={36} y={52} width={68} height={84} rx={10} fill="#1f2740" stroke="#33406a" />
			<motion.circle cx={70} cy={100} r={22} fill="#141a2c" stroke={color} strokeWidth={3} animate={{scale: active ? [1, 1.08, 1] : 1}} transition={loop(active, 0.45)} />
			<circle cx={70} cy={100} r={7} fill={color} />
			<circle cx={70} cy={66} r={7} fill="#141a2c" stroke={color} strokeWidth={2} />
			{active &&
				['♪', '♫', '♪'].map((n, i) => (
					<motion.text key={i} x={60 + i * 14} y={46} fontSize={18} fill={color} animate={{y: [46, 10], opacity: [0, 1, 0], x: [60 + i * 14, 50 + i * 22]}} transition={{duration: 2, repeat: Infinity, delay: i * 0.6}}>
						{n}
					</motion.text>
				))}
		</g>
	);
}

function Assembly({color, active}: ArtProps) {
	return (
		<g>
			<rect x={50} y={120} width={40} height={14} rx={4} fill="#3a4566" />
			<motion.g animate={{rotate: active ? [-18, 18, -18] : 0}} transition={loop(active, 1.6)} style={{originX: '70px', originY: '120px'}}>
				<rect x={65} y={68} width={10} height={54} rx={5} fill="#59627e" />
				<circle cx={70} cy={68} r={8} fill={color} />
				<motion.g animate={{rotate: active ? [20, -30, 20] : 0}} transition={loop(active, 1.2)} style={{originX: '70px', originY: '68px'}}>
					<rect x={70} y={64} width={40} height={9} rx={4.5} fill="#59627e" />
					<path d="M108 60 l10 -6 M108 77 l10 6" stroke={color} strokeWidth={4} strokeLinecap="round" />
				</motion.g>
			</motion.g>
		</g>
	);
}

function Gate({color, active}: ArtProps) {
	return (
		<g>
			<rect x={44} y={56} width={52} height={70} rx={10} fill="#1f2740" stroke="#33406a" />
			<motion.circle cx={70} cy={80} r={12} fill="none" stroke={color} strokeWidth={4} strokeDasharray="20 60" animate={{rotate: active ? 360 : 0}} transition={active ? {duration: 1, repeat: Infinity, ease: 'linear'} : {duration: 0.3}} style={{originX: '70px', originY: '80px'}} />
			<path d="M63 80 l5 5 l9 -10" stroke={color} strokeWidth={3} fill="none" strokeLinecap="round" />
			<rect x={52} y={104} width={36} height={6} rx={3} fill="#33406a" />
		</g>
	);
}

function Truck({color, active, done, cargo}: ArtProps) {
	return (
		<motion.g animate={{x: done ? [0, 6, 0] : active ? [0, 2, 0] : 0}} transition={loop(active || done, done ? 2 : 0.4)}>
			<rect x={18} y={66} width={70} height={52} rx={6} fill={color} />
			<text x={53} y={98} textAnchor="middle" fontSize={13} fontWeight={800} fill="#1b1406">
				{cargo ?? 'MP4'}
			</text>
			<path d="M88 80 L110 80 L124 98 L124 118 L88 118 Z" fill="#59627e" />
			<rect x={96} y={86} width={14} height={12} rx={2} fill="#9fb3d9" />
			<circle cx={40} cy={122} r={9} fill="#1b1b24" stroke="#7d89a8" strokeWidth={3} />
			<circle cx={106} cy={122} r={9} fill="#1b1b24" stroke="#7d89a8" strokeWidth={3} />
		</motion.g>
	);
}

function Folder({color}: ArtProps) {
	return (
		<g>
			<path d="M36 60 h26 l8 10 h34 v56 h-68z" fill={color} opacity={0.85} />
			<rect x={36} y={74} width={68} height={52} rx={4} fill={color} />
		</g>
	);
}

export function StationArt(p: ArtProps) {
	switch (p.id) {
		case 'strategist':
			return <Character {...p} accessory={<Glasses />} />;
		case 'scriptwriter':
			return (
				<Character
					{...p}
					accessory={<motion.path d="M92 60 l10 -22 l4 2 l-10 22 z" fill="#f5b942" animate={{rotate: p.active ? [-8, 8, -8] : 0}} transition={loop(p.active, 0.5)} style={{originX: '94px', originY: '60px'}} />}
				/>
			);
		case 'qa-reviewer':
			return (
				<Character
					{...p}
					accessory={
						<motion.g animate={{x: p.active ? [-6, 6, -6] : 0}} transition={loop(p.active, 2)}>
							<circle cx={86} cy={62} r={8} fill="#cfe9ff33" stroke="#e8ecf6" strokeWidth={2.5} />
							<path d="M91 68 l7 8" stroke="#e8ecf6" strokeWidth={3} strokeLinecap="round" />
						</motion.g>
					}
				/>
			);
		case 'planner':
			return <Character {...p} accessory={<rect x={86} y={56} width={16} height={18} rx={2} fill="#e8ecf6" stroke="#5cb8ff" strokeWidth={2} />} />;
		case 'designer':
			return <Character {...p} accessory={<path d="M88 58 l12 -12 l4 4 l-12 12z" fill="#e879f9" />} />;
		case 'post-copywriter':
			return (
				<Character
					{...p}
					accessory={<motion.path d="M92 60 l10 -22 l4 2 l-10 22 z" fill="#ff6b81" animate={{rotate: p.active ? [-8, 8, -8] : 0}} transition={loop(p.active, 0.5)} style={{originX: '94px', originY: '60px'}} />}
				/>
			);
		case 'post-designer':
			return (
				<Character
					{...p}
					accessory={
						<motion.g animate={{rotate: p.active ? [-6, 6, -6] : 0}} transition={loop(p.active, 1)} style={{originX: '94px', originY: '64px'}}>
							<rect x={84} y={52} width={20} height={24} rx={3} fill="#e8ecf6" />
							<rect x={87} y={56} width={14} height={7} rx={1.5} fill="#e879f9" />
							<rect x={87} y={66} width={10} height={3} rx={1.5} fill="#9b7bff" />
						</motion.g>
					}
				/>
			);
		case 'post':
			return <Character {...p} accessory={<rect x={84} y={58} width={18} height={14} rx={2} fill="#f5b942" />} />;
		case 'voice':
			return <VoiceBooth {...p} />;
		case 'images':
		case 'clips':
		case 'stock':
		case 'avatar':
		case 'brand':
			return <ImageLab {...p} />;
		case 'render':
			return <RenderOven {...p} />;
		case 'qa':
			return <Scanner {...p} />;
		case 'music':
			return <MusicBox {...p} />;
		case 'props':
			return <Assembly {...p} />;
		case 'deliver':
			return <Truck {...p} />;
		case 'intake':
			return <Folder {...p} />;
		default:
			return <Gate {...p} />;
	}
}
