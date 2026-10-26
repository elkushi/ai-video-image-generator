// Tiny app-wide toast bus: anything can push a message; App renders them.
export type ToastMsg = {id: string; text: string; color?: string};
type Fn = (t: ToastMsg) => void;
const subs = new Set<Fn>();
let n = 0;

export const onToast = (fn: Fn) => {
	subs.add(fn);
	return () => {
		subs.delete(fn);
	};
};
export const toast = (text: string, color = '#ff6b81') => {
	const t = {id: `t${Date.now()}-${n++}`, text, color};
	subs.forEach((fn) => fn(t));
};
