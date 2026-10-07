/* Cloudflare Pages Function: every request under /api/* is handled by the router in functions/_lib/router.js.
 * Static pages, Loot Intel JSON, map data and images are served directly by Pages and never reach this code
 * (see _routes.json). */
import { handle } from '../_lib/router.js';

export const onRequest = context => handle(context);
