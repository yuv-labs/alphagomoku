import "dotenv/config";
import { neon } from "@neondatabase/serverless";

const sql = neon(process.env.DATABASE_URL!);

async function migrate() {
  await sql`
    CREATE TABLE IF NOT EXISTS games (
      game_id    TEXT PRIMARY KEY,
      rows       INTEGER NOT NULL DEFAULT 9,
      cols       INTEGER NOT NULL DEFAULT 9,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
  `;

  await sql`
    CREATE TABLE IF NOT EXISTS moves (
      id        SERIAL PRIMARY KEY,
      game_id   TEXT NOT NULL REFERENCES games(game_id) ON DELETE CASCADE,
      seq       INTEGER NOT NULL,
      row       INTEGER NOT NULL,
      col       INTEGER NOT NULL,
      color     CHAR(1) NOT NULL CHECK (color IN ('b', 'w')),
      placed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      UNIQUE (game_id, seq),
      UNIQUE (game_id, row, col)
    )
  `;

  await sql`
    CREATE TABLE IF NOT EXISTS webhooks (
      webhook_id TEXT PRIMARY KEY,
      game_id    TEXT NOT NULL REFERENCES games(game_id) ON DELETE CASCADE,
      url        TEXT NOT NULL,
      color      CHAR(1) NOT NULL CHECK (color IN ('b', 'w'))
    )
  `;

  await sql`CREATE INDEX IF NOT EXISTS idx_moves_game_id ON moves(game_id, seq)`;
  await sql`CREATE INDEX IF NOT EXISTS idx_webhooks_game_id ON webhooks(game_id)`;

  console.log("Migration completed successfully.");
}

migrate().catch((e) => {
  console.error(e);
  process.exit(1);
});
