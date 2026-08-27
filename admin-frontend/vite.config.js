import { fileURLToPath, URL } from 'node:url';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';
// https://vitejs.dev/config/
export default defineConfig({
    plugins: [react()],
    resolve: {
        alias: {
            '@': fileURLToPath(new URL('./src', import.meta.url)),
        },
    },
    server: {
        port: 5173,
        proxy: {
            // 开发环境后端代理：转发 /api 到 admin 后端（:8002，标准端口）
            // 用 127.0.0.1 而非 localhost：node 会把 localhost 解析为 IPv6(::1)，而 uvicorn 绑 0.0.0.0 仅监听 IPv4
            '/api': {
                target: 'http://127.0.0.1:8002',
                changeOrigin: true,
            },
        },
    },
});
