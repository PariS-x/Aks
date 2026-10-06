import type { NextConfig } from "next";

// The browser talks to /api/* on the same origin; Next proxies it to FastAPI.
const API = process.env.AKS_API_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API}/api/:path*` }];
  },
};

export default nextConfig;
