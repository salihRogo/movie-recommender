// app/routes/$.tsx
import { type LoaderFunctionArgs } from "@remix-run/node";

export const loader = async ({ request }: LoaderFunctionArgs) => {
  // Log the request to see what's being caught
  console.log(`Caught unhandled request: ${request.method} ${request.url}`);

  // For /.well-known/ requests, it's often safe to just return a 404
  // or a specific response if you know what's expected.
  const url = new URL(request.url);
  if (url.pathname.startsWith("/.well-known")) {
    throw new Response("Not Found", { status: 404 });
  }

  // For other routes, you might want to handle them differently
  // or just throw a generic 404.
  throw new Response("Not Found", { status: 404 });
};

// You can also export a default component to render for these routes,
// but for API-like or special requests, a loader is often enough.
export default function SplatRoute() {
  return (
    <div style={{ padding: "20px", textAlign: "center" }}>
      <h1>404 - Not Found</h1>
      <p>The page you are looking for does not exist.</p>
    </div>
  );
}
