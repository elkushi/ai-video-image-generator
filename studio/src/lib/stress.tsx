// Russian stress marks (U+0301) drawn as an overlay accent above the vowel.
// Why: Inter (both the Google static build and the official 4.1 release) has no Cyrillic mark
// positioning; Chrome renders "двери́" as "двери´", and the mark even eats the next space.
// Drawing the accent ourselves works with any brand font. Lowercase and capitals use different heights.
import React from 'react';

const RE = /(\S)́/gu;

export function st(v: React.ReactNode): React.ReactNode {
	if (typeof v !== 'string' || !v.includes('́')) return v;
	const out: React.ReactNode[] = [];
	let last = 0;
	for (const m of v.matchAll(RE)) {
		const i = m.index ?? 0;
		if (i > last) out.push(v.slice(last, i));
		const ch = m[1];
		const upper = ch !== ch.toLowerCase();
		out.push(
			<span key={i} style={{position: 'relative', display: 'inline-block'}}>
				{ch}
				<span
					aria-hidden
					style={{position: 'absolute', left: '50%', top: upper ? '-0.3em' : '-0.02em', transform: 'translateX(-30%)', lineHeight: 1, fontSize: '0.95em', pointerEvents: 'none'}}
				>
					{'´'}
				</span>
			</span>,
		);
		last = i + m[0].length;
	}
	if (last < v.length) out.push(v.slice(last));
	return out;
}
