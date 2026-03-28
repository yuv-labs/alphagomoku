import crypto from "node:crypto";
import { sql } from "./db.js";

export type Color = "b" | "w";

export interface Move {
  row: number;
  col: number;
  color: Color;
}

export interface Webhook {
  webhookId: string;
  url: string;
  color: Color;
}

export interface GameResponse {
  gameId: string;
  rows: number;
  cols: number;
  board: (Color | null)[][];
  moves: Move[];
  nextColor: Color;
}

export interface GameSummary {
  gameId: string;
  rows: number;
  cols: number;
  moveCount: number;
  nextColor: Color;
}

function buildBoard(rows: number, cols: number, moves: Move[]): (Color | null)[][] {
  const board: (Color | null)[][] = Array.from({ length: rows }, () =>
    Array(cols).fill(null)
  );
  for (const m of moves) {
    board[m.row][m.col] = m.color;
  }
  return board;
}

function deriveNextColor(moveCount: number): Color {
  return moveCount % 2 === 0 ? "b" : "w";
}

function parseMoveRows(rows: Record<string, unknown>[]): Move[] {
  return rows.map((r: any) => ({
    row: r.row,
    col: r.col,
    color: r.color as Color,
  }));
}

function parseWebhookRows(rows: Record<string, unknown>[]): Webhook[] {
  return rows.map((r: any) => ({
    webhookId: r.webhook_id,
    url: r.url,
    color: r.color as Color,
  }));
}

async function fetchGame(gameId: string) {
  const [game] = await sql`SELECT * FROM games WHERE game_id = ${gameId}`;
  return game ?? null;
}

async function fetchMoves(gameId: string): Promise<Move[]> {
  const rows = await sql`
    SELECT row, col, color FROM moves WHERE game_id = ${gameId} ORDER BY seq
  `;
  return parseMoveRows(rows);
}

export async function createGame(rows = 9, cols = 9): Promise<GameResponse> {
  const gameId = crypto.randomUUID().slice(0, 8);
  await sql`INSERT INTO games (game_id, rows, cols) VALUES (${gameId}, ${rows}, ${cols})`;
  return {
    gameId,
    rows,
    cols,
    board: buildBoard(rows, cols, []),
    moves: [],
    nextColor: "b",
  };
}

export async function listGames(): Promise<GameSummary[]> {
  const results = await sql`
    SELECT g.game_id, g.rows, g.cols, COUNT(m.id)::int AS move_count
    FROM games g
    LEFT JOIN moves m ON m.game_id = g.game_id
    GROUP BY g.game_id
    ORDER BY g.created_at DESC
  `;
  return results.map((r: any) => ({
    gameId: r.game_id,
    rows: r.rows,
    cols: r.cols,
    moveCount: r.move_count,
    nextColor: deriveNextColor(r.move_count),
  }));
}

export async function getGame(gameId: string): Promise<GameResponse | null> {
  const game = await fetchGame(gameId);
  if (!game) return null;

  const moves = await fetchMoves(gameId);
  return {
    gameId,
    rows: game.rows,
    cols: game.cols,
    board: buildBoard(game.rows, game.cols, moves),
    moves,
    nextColor: deriveNextColor(moves.length),
  };
}

export async function placeMove(
  gameId: string,
  row: number,
  col: number
): Promise<GameResponse & { lastMove: Move }> {
  const game = await fetchGame(gameId);
  if (!game) throw new Error("Game not found");
  if (row < 0 || row >= game.rows || col < 0 || col >= game.cols) {
    throw new Error("Position out of bounds");
  }

  const moves = await fetchMoves(gameId);
  const board = buildBoard(game.rows, game.cols, moves);
  if (board[row][col] !== null) {
    throw new Error("Position already occupied");
  }

  const color = deriveNextColor(moves.length);
  const seq = moves.length;
  await sql`
    INSERT INTO moves (game_id, seq, row, col, color)
    VALUES (${gameId}, ${seq}, ${row}, ${col}, ${color})
  `;

  const lastMove: Move = { row, col, color };
  moves.push(lastMove);
  board[row][col] = color;

  return {
    gameId,
    rows: game.rows,
    cols: game.cols,
    board,
    moves,
    nextColor: deriveNextColor(moves.length),
    lastMove,
  };
}

export async function undoMove(gameId: string): Promise<GameResponse> {
  const game = await fetchGame(gameId);
  if (!game) throw new Error("Game not found");

  const allMoves = await fetchMoves(gameId);
  if (allMoves.length === 0) throw new Error("No moves to undo");

  const lastSeq = allMoves.length - 1;
  await sql`DELETE FROM moves WHERE game_id = ${gameId} AND seq = ${lastSeq}`;

  const moves = allMoves.slice(0, -1);
  return {
    gameId,
    rows: game.rows,
    cols: game.cols,
    board: buildBoard(game.rows, game.cols, moves),
    moves,
    nextColor: deriveNextColor(moves.length),
  };
}

export async function deleteGame(gameId: string): Promise<boolean> {
  const result = await sql`DELETE FROM games WHERE game_id = ${gameId} RETURNING game_id`;
  return result.length > 0;
}

export async function listWebhooks(gameId: string): Promise<Webhook[] | null> {
  const game = await fetchGame(gameId);
  if (!game) return null;

  const rows = await sql`
    SELECT webhook_id, url, color FROM webhooks WHERE game_id = ${gameId}
  `;
  return parseWebhookRows(rows);
}

export async function addWebhook(gameId: string, url: string, color: Color): Promise<Webhook> {
  const game = await fetchGame(gameId);
  if (!game) throw new Error("Game not found");

  const webhookId = crypto.randomUUID().slice(0, 8);
  await sql`
    INSERT INTO webhooks (webhook_id, game_id, url, color)
    VALUES (${webhookId}, ${gameId}, ${url}, ${color})
  `;
  return { webhookId, url, color };
}

export async function removeWebhook(gameId: string, webhookId: string): Promise<boolean> {
  const result = await sql`
    DELETE FROM webhooks WHERE game_id = ${gameId} AND webhook_id = ${webhookId} RETURNING webhook_id
  `;
  return result.length > 0;
}

export async function getWebhooks(gameId: string): Promise<Webhook[]> {
  const rows = await sql`
    SELECT webhook_id, url, color FROM webhooks WHERE game_id = ${gameId}
  `;
  return parseWebhookRows(rows);
}
