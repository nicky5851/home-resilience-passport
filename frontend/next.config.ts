import type { NextConfig } from "next"

// The browser only ever calls relative /api/v1/...; Next.js forwards it to the API, so the
// auth cookie is first-party and no CORS is needed (CONTRACT §3).
const API_ORIGIN = process.env.API_ORIGIN ?? "http://localhost:8000"

const nextConfig: NextConfig = {
  poweredByHeader: false,
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_ORIGIN}/api/:path*` }]
  },
}

export default nextConfig
