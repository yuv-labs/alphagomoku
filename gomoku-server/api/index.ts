import type { VercelRequest, VercelResponse } from "@vercel/node";
import {
  createGame,
  getGame,
  getRawGame,
  listGames,
  placeMove,
  undoMove,
  addWebhook,
  listWebhooks,
  removeWebhook,
  deleteGame,
} from "../lib/gameStore.js";
import { notifyWebhooks } from "../lib/webhook.js";

type Handler = (req: VercelRequest, res: VercelResponse, params: string[]) => Promise<void> | void;

const routes: [string, RegExp, Handler][] = [
  ["GET", /^\/api\/games$/, (_req, res) => {
    res.json(listGames());
  }],

  ["POST", /^\/api\/games$/, (req, res) => {
    const { rows, cols } = req.body ?? {};
    res.status(201).json(createGame(rows, cols));
  }],

  ["GET", /^\/api\/games\/([^/]+)$/, (_req, res, [id]) => {
    const game = getGame(id);
    if (!game) return res.status(404).json({ error: "Game not found" });
    res.json(game);
  }],

  ["DELETE", /^\/api\/games\/([^/]+)$/, (_req, res, [id]) => {
    if (!deleteGame(id)) return res.status(404).json({ error: "Game not found" });
    res.json({ success: true });
  }],

  ["POST", /^\/api\/games\/([^/]+)\/move$/, async (req, res, [id]) => {
    const { row, col } = req.body ?? {};
    if (typeof row !== "number" || typeof col !== "number") {
      return res.status(400).json({ error: "row and col are required numbers" });
    }
    try {
      const result = placeMove(id, row, col);
      const game = getRawGame(id);
      if (game) await notifyWebhooks(game, result, result.lastMove);
      res.json(result);
    } catch (err: any) {
      res.status(400).json({ error: err.message });
    }
  }],

  ["POST", /^\/api\/games\/([^/]+)\/undo$/, async (_req, res, [id]) => {
    try {
      const result = undoMove(id);
      const game = getRawGame(id);
      if (game) await notifyWebhooks(game, result);
      res.json(result);
    } catch (err: any) {
      res.status(400).json({ error: err.message });
    }
  }],

  ["GET", /^\/api\/games\/([^/]+)\/webhooks$/, (_req, res, [id]) => {
    const webhooks = listWebhooks(id);
    if (!webhooks) return res.status(404).json({ error: "Game not found" });
    res.json(webhooks);
  }],

  ["POST", /^\/api\/games\/([^/]+)\/webhooks$/, (req, res, [id]) => {
    const { url, color } = req.body ?? {};
    if (!url || !["b", "w"].includes(color)) {
      return res.status(400).json({ error: "url and color ('b' or 'w') are required" });
    }
    try {
      res.status(201).json(addWebhook(id, url, color));
    } catch (err: any) {
      res.status(400).json({ error: err.message });
    }
  }],

  ["DELETE", /^\/api\/games\/([^/]+)\/webhooks\/([^/]+)$/, (_req, res, [gameId, webhookId]) => {
    if (!removeWebhook(gameId, webhookId)) return res.status(404).json({ error: "Webhook not found" });
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
