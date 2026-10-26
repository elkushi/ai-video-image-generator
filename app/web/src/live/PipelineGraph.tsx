// Live node graph: agents on the top row, tools on the bottom row, data packets travelling along edges.
import {Background, BaseEdge, Controls, Handle, Position, ReactFlow, getBezierPath, type Edge, type EdgeProps, type Node, type NodeProps} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import {motion} from 'motion/react';
import {useMemo} from 'react';
import {fmtSec} from '../lib/api';
import {NODE, nodeDef} from '../lib/nodes';
import {nodeSeconds, type NodeState, type PipelineState} from '../lib/pipeline';
import {stationsFor} from './FactoryFloor';

type Data = {id: string; st?: NodeState; now: number; kind: string};

function StationNode({data}: NodeProps<Node<Data>>) {
	const def = nodeDef(data.id, data.kind)!;
	const st = data.st;
	const active = st?.status === 'active';
	const done = st?.status === 'done';
	const err = st?.status === 'error';
	return (
		<motion.div
			className="relative w-[190px] rounded-2xl border px-3 py-2.5"
			style={{
				background: active ? `${def.color}1f` : '#111624',
				borderColor: active ? def.color : done ? '#34d3b466' : err ? '#ff6b81' : '#2e3956',
				boxShadow: active ? `0 0 28px ${def.color}55` : 'none',
				opacity: st ? 1 : 0.5,
			}}
			animate={active ? {scale: [1, 1.04, 1]} : {scale: 1}}
			transition={active ? {duration: 1.4, repeat: Infinity} : {duration: 0.3}}
		>
			<Handle type="target" position={Position.Left} style={{opacity: 0}} />
			<Handle type="source" position={Position.Right} style={{opacity: 0}} />
			<div className="flex items-center gap-2.5">
				<span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl text-[18px]" style={{background: `${def.color}26`}}>
					{def.emoji}
				</span>
				<div className="min-w-0 flex-1">
					<div className="text-[14px] font-semibold leading-tight text-ink-100">{def.label}</div>
					<div className="mt-0.5 flex items-center justify-between text-[11px]">
						<span className="uppercase tracking-wider" style={{color: def.kind === 'agent' ? '#9b7bff' : '#7d89a8'}}>
							{def.kind === 'agent' ? 'AI agent' : def.kind === 'claude' ? 'Claude' : 'tool'}
						</span>
						<span className="font-mono" style={{color: err ? '#ff6b81' : active ? def.color : done ? '#34d3b4' : '#56607c'}}>
							{err ? '✕ ' : done ? '✓ ' : ''}
							{st ? fmtSec(nodeSeconds(st, data.now)) : '–'}
						</span>
					</div>
				</div>
			</div>
			{st?.progress != null && st.progress < 100 && active && (
				<div className="mt-2 h-1.5 overflow-hidden rounded-full bg-ink-700">
					<motion.div className="h-full rounded-full" style={{background: def.color}} animate={{width: `${st.progress}%`}} />
				</div>
			)}
			{active && st?.detail && <div className="mt-1.5 line-clamp-2 text-[11px] leading-tight text-ink-300">{st.detail}</div>}
			{st?.fallback && <div className="mt-1.5 inline-block rounded-full border border-amber px-2 text-[10px] text-amber">↪ {st.fallback}</div>}
		</motion.div>
	);
}

function FlowEdge(props: EdgeProps<Edge<{live: boolean; done: boolean; color: string}>>) {
	const [path] = getBezierPath(props);
	const live = props.data?.live;
	const done = props.data?.done;
	return (
		<>
			<BaseEdge path={path} style={{stroke: done ? '#34d3b455' : live ? props.data!.color : '#2e3956', strokeWidth: live ? 2.5 : 1.5}} />
			{live &&
				[0, 0.5].map((d) => (
					<circle key={d} r={4} fill={props.data!.color} style={{filter: `drop-shadow(0 0 6px ${props.data!.color})`}}>
						<animateMotion dur="1.4s" begin={`${d * 1.4}s`} repeatCount="indefinite" path={path} />
					</circle>
				))}
		</>
	);
}

const nodeTypes = {station: StationNode};
const edgeTypes = {flow: FlowEdge};

export function PipelineGraph({s, kind}: {s: PipelineState; kind: string}) {
	const now = Date.now();
	const ids = stationsFor(kind, s);
	const key = ids.join(',');
	const layout = useMemo(() => {
		const cols = [...new Set(ids.map((id) => NODE[id].col))].sort((a, b) => a - b);
		return Object.fromEntries(ids.map((id) => [id, {x: cols.indexOf(NODE[id].col) * 225, y: NODE[id].row === 0 ? 0 : 150}]));
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [key]);
	const nodes: Node<Data>[] = ids.map((id) => ({id, type: 'station', position: layout[id], data: {id, st: s.nodes[id], now, kind}, draggable: true}));
	const edges: Edge<{live: boolean; done: boolean; color: string}>[] = ids.slice(1).map((id, i) => {
		const src = ids[i];
		const t = s.nodes[id];
		const so = s.nodes[src];
		return {
			id: `${src}-${id}`,
			source: src,
			target: id,
			type: 'flow',
			data: {live: t?.status === 'active' && so?.status === 'done', done: t?.status === 'done', color: NODE[id].color},
		};
	});
	return (
		<div className="h-[460px] w-full">
			<ReactFlow
				nodes={nodes}
				edges={edges}
				nodeTypes={nodeTypes}
				edgeTypes={edgeTypes}
				fitView
				fitViewOptions={{padding: 0.08}}
				proOptions={{hideAttribution: true}}
				colorMode="dark"
				nodesConnectable={false}
				minZoom={0.3}
			>
				<Background color="#1c2438" gap={24} />
				<Controls showInteractive={false} />
			</ReactFlow>
		</div>
	);
}
