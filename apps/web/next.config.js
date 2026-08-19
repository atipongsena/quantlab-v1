/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // The dashboard is a static client that reads the API at runtime, so it exports to
  // plain files and needs no Node server of its own.
  output: "export",
  // Next 16 writes AGENTS.md and CLAUDE.md into the app directory on every build.
  // This project documents itself in docs/ and README.md.
  agentRules: false,
  // The floating dev badge overlays page content and ends up in screenshots.
  devIndicators: false,
};

module.exports = nextConfig;
