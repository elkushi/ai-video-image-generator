// Live job state: replays the job's events over SSE and keeps folding new ones in.
import {useEffect, useReducer, useRef, useState} from 'react';
import {api, type Job} from './api';
import {applyEvent, emptyPipeline, type FactoryEvent, type PipelineState} from './pipeline';

export function useJob(jobId?: string) {
	const state = useRef<PipelineState>(emptyPipeline());
	const [, bump] = useReducer((x: number) => x + 1, 0);
	const [job, setJob] = useState<Job | null>(null);
	const [connected, setConnected] = useState(false);

	useEffect(() => {
		if (!jobId) return;
		state.current = emptyPipeline();
		bump();
		let es: EventSource | null = null;
		let seen = 0;
		let closed = false;
		let frame = 0;
		const schedule = () => {
			if (frame) return;
			frame = requestAnimationFrame(() => {
				frame = 0;
				bump();
			});
		};
		const open = () => {
			es = new EventSource(`/api/jobs/${jobId}/events?since=${seen}`);
			es.onopen = () => setConnected(true);
			es.onmessage = (m) => {
				seen = Number(m.lastEventId) + 1;
				try {
					applyEvent(state.current, JSON.parse(m.data) as FactoryEvent);
				} catch {
					/* ignore a malformed line */
				}
				schedule();
			};
			es.addEventListener('end', () => {
				es?.close();
				setConnected(false);
				api.job(jobId).then(setJob).catch(() => {});
			});
			es.onerror = () => {
				setConnected(false);
				es?.close(); // the 3 s poll reopens it while the job is active
			};
		};
		api.job(jobId).then(setJob).catch(() => {});
		open();
		// a waiting/finished job can be resumed (answer, revision): reconnect when it is active again
		const poll = setInterval(
			() =>
				api
					.job(jobId)
					.then((j) => {
						setJob(j);
						if (!closed && ['queued', 'running'].includes(j.status) && (!es || es.readyState === EventSource.CLOSED)) open();
					})
					.catch(() => {}),
			3000,
		);
		const tick = setInterval(() => state.current.status === 'running' && bump(), 1000);
		return () => {
			closed = true;
			es?.close();
			clearInterval(poll);
			clearInterval(tick);
			cancelAnimationFrame(frame);
		};
	}, [jobId]);

	return {s: state.current, job, connected, refresh: () => jobId && api.job(jobId).then(setJob)};
}
