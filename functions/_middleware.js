/* Runs only for the paths listed in _routes.json. API requests pass straight through; repository-only files
 * (server source, migrations, tooling, seeds, docs, config) are deployed with the site because the build output
 * directory is the repository root, so they are answered with 404 here instead of being served. */
const PRIVATE = /^\/(functions|migrations|tools|seeds|docs|backups|node_modules|\.wrangler)(\/|$)|^\/(wrangler\.toml|package(-lock)?\.json|\.gitignore|\.dev\.vars|supabase-schema\.sql|README(\.md)?|ASSET-MANIFEST(\.md)?|DATA-STATUS(\.md)?)$/i;

export const onRequest = context => {
  const path = new URL(context.request.url).pathname;
  if (PRIVATE.test(path)) return new Response('Not found', { status: 404, headers: { 'Content-Type': 'text/plain; charset=utf-8', 'X-Robots-Tag': 'noindex', 'Cache-Control': 'no-store' } });
  return context.next();
};
