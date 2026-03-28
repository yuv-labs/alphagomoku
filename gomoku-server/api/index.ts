import type { VercelRequest, VercelResponse } from "@vercel/node";
import {
  createGame,
  getGame,
  getWebhooks,
  listGames,
  placeMove,
  undoMove,
  addWebhook,
  listWebhooks,
  removeWebhook,
  deleteGame,
} from "../lib/gameStore.js";
import { notifyWebhooks } from "../lib/webhook.js";

type Handler = (req: VercelRequest, res: VercelResponse, params: string[]) => Promise<void>;

const routes: [string, RegExp, Handler][] = [
  ["GET", /^\/api\/games$/, async (_req, res) => {
    res.json(await listGames());
  }],

  ["POST", /^\/api\/games$/, async (req, res) => {
    const { rows, cols } = req.body ?? {};
    res.status(201).json(await createGame(rows, cols));
  }],

  ["GET", /^\/api\/games\/([^/]+)$/, async (_req, res, [id]) => {
    const game = await getGame(id);
    if (!game) { res.status(404).json({ error: "Game not found" }); return; }
    res.json(game);
  }],

  ["DELETE", /^\/api\/games\/([^/]+)$/, async (_req, res, [id]) => {
    if (!(await deleteGame(id))) { res.status(404).json({ error: "Game not found" }); return; }
    res.json({ success: true });
  }],

  ["POST", /^\/api\/games\/([^/]+)\/move$/, async (req, res, [id]) => {
    const { row, col } = req.body ?? {};
    if (typeof row !== "number" || typeof col !== "number") {
      res.status(400).json({ error: "row and col are required numbers" }); return;
    }
    try {
      const result = await placeMove(id, row, col);
      const webhooks = await getWebhooks(id);
      if (webhooks.length) await notifyWebhooks(webhooks, result, result.lastMove);
      res.json(result);
    } catch (err: any) {
      res.status(400).json({ error: err.message });
    }
  }],

  ["POST", /^\/api\/games\/([^/]+)\/undo$/, async (_req, res, [id]) => {
    try {
      const result = await undoMove(id);
      const webhooks = await getWebhooks(id);
      if (webhooks.length) await notifyWebhooks(webhooks, result);
      res.json(result);
    } catch (err: any) {
      res.status(400).json({ error: err.message });
    }
  }],

  ["GET", /^\/api\/games\/([^/]+)\/webhooks$/, async (_req, res, [id]) => {
    const webhooks = await listWebhooks(id);
    if (!webhooks) { res.status(404).json({ error: "Game not found" }); return; }
    res.json(webhooks);
  }],

  ["POST", /^\/api\/games\/([^/]+)\/webhooks$/, async (req, res, [id]) => {
    const { url, color } = req.body ?? {};
    if (!url || !["b", "w"].includes(color)) {
      res.status(400).json({ error: "url and color ('b' or 'w') are required" }); return;
    }
    try {
      res.status(201).json(await addWebhook(id, url, color));
    } catch (err: any) {
      res.status(400).json({ error: err.message });
    }
  }],

  ["DELETE", /^\/api\/games\/([^/]+)\/webhooks\/([^/]+)$/, async (_req, res, [gameId, webhookId]) => {
    if (!(await removeWebhook(gameId, webhookId))) { res.status(404).json({ error: "Webhook not found" }); return; }
    res.json({ success: true });
  }],
];

export default async function handler(req: VercelRequest, res: VercelResponse) {
  const path = (req.url ?? "").split("?")[0];

  for (const [method, pattern, fn] of routes) {
    if (req.method !== method) continue;
    const match = path.match(pattern);
    if (!match) continue;
    return fn(req, res, match.slice(1));
  }

  res.status(404).json({ error: "Not found" });
}
