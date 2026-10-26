import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import {defineConfig} from 'vite';

// Dev: the FastAPI backend runs on :8787; the UI proxies /api and /files to it.
export default defineConfig({
	plugins: [react(), tailwindcss()],
	server: {
		proxy: {
			'/api': 'http://127.0.0.1:8787',
			'/files': 'http://127.0.0.1:8787',
		},
	},
	build: {outDir: 'dist', chunkSizeWarningLimit: 900},
});
