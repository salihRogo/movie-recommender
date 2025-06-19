const express = require('express');
const { createRequestHandler } = require('@remix-run/express');
const { createProxyMiddleware } = require('http-proxy-middleware');
const path = require('path');

const app = express();
const port = process.env.PORT || 3000;
const backendInternalPort = process.env.BACKEND_INTERNAL_PORT || 8001;

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

// Serve static assets from Remix's build folder (inside frontend directory)
app.use(express.static(path.join(__dirname, 'frontend', 'public'), { maxAge: '1h' }));

// Remix request handler for all other requests
// Ensure the path to the server build is correct relative to the project root
const remixBuildPath = path.join(__dirname, 'frontend', 'build', 'server');
app.all(
  '*',
  process.env.NODE_ENV === 'development'
    ? (req, res, next) => {
        // In development, rebuild on every request
        // This requires your frontend/package.json to have a dev script that rebuilds
        // For simplicity in deployment, we assume a pre-built app here.
        // If you need live reload in dev with this setup, it's more complex.
        return createRequestHandler({
          build: require(remixBuildPath),
          mode: process.env.NODE_ENV,
        })(req, res, next);
      }
    : createRequestHandler({
        build: require(remixBuildPath),
        mode: process.env.NODE_ENV,
      })
);

app.listen(port, () => {
  console.log(`✅ Frontend server listening on port ${port}`);
  console.log(`✅ Proxying API requests from /api to http://localhost:${backendInternalPort}`);
  console.log(`Remix server build path: ${remixBuildPath}`);
});
