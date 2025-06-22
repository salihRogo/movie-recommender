const express = require('express');
const { createRequestHandler } = require('@remix-run/express');
const { createProxyMiddleware } = require('http-proxy-middleware');
const path = require('path');

const app = express();
const port = process.env.PORT || 3000;
const backendInternalPort = process.env.BACKEND_INTERNAL_PORT || 8000;

// Proxy API requests to the Python backend
// All requests to /api/* will be forwarded to your Python backend
app.use(
  '/api',
  createProxyMiddleware({
    target: `http://localhost:${backendInternalPort}`,
    changeOrigin: true,
    pathRewrite: {
      '^/api': '', // Remove /api prefix before forwarding to FastAPI
    },
    onError: (err, req, res) => {
      console.error('Proxy error:', err);
      if (!res.headersSent) {
        res.writeHead(500, { 'Content-Type': 'text/plain' });
      }
      res.end('Proxy error occurred.');
    },
    onProxyReq: (proxyReq, req, res) => {
      console.log(`[Proxy] Request: ${req.method} ${req.originalUrl} -> ${proxyReq.protocol}//${proxyReq.host}${proxyReq.path}`);
    },
    onProxyRes: (proxyRes, req, res) => {
      console.log(`[Proxy] Response: ${req.method} ${req.originalUrl} -> ${proxyRes.statusCode}`);
    }
  })
);

// Serve all static assets from the Remix build directory
app.use(express.static(path.join(__dirname, 'frontend', 'build', 'client'), { maxAge: '1h' }));

// Remix request handler using dynamic import for ESM compatibility
async function startServer() {
  // We need to use a file URL for dynamic import()
  const remixBuildPath = path.resolve(__dirname, 'frontend', 'build', 'server', 'index.js');
  const remixBuildURL = new URL(remixBuildPath, 'file://');

  console.log(`Loading Remix server build from: ${remixBuildURL.href}`);

  // Dynamically import the ESM Remix server build
  const build = await import(remixBuildURL.href);

  app.all(
    '*',
    createRequestHandler({
      build: build,
      mode: process.env.NODE_ENV,
    })
  );

  app.listen(port, () => {
    console.log(`✅ Frontend server listening on port ${port}`);
    console.log(`✅ Proxying API requests from /api to http://localhost:${backendInternalPort}`);
  });
}

startServer().catch((error) => {
  console.error('❌ Failed to start server:', error);
  process.exit(1);
});
