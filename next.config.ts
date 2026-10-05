import type { NextConfig } from 'next';
const config: NextConfig = { output: 'export', images: { unoptimized: true }, devIndicators: false, allowedDevOrigins: ['localhost', '127.0.0.1'], turbopack: { root: process.cwd() } };
export default config;
