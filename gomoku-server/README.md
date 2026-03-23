# AlphaGomoku Server

In-memory Gomoku (Five-in-a-Row) game server with a React UI and REST API.
Build your own AI agent and connect it via the API or webhooks.

**Live:** https://alphagomoku.vercel.app

## Features

- **Flexible board size** — create games with any N×M board (default 9×9)
- **REST API** — create games, place moves, undo, and query board state
- **Webhooks** — get notified via POST when it's your color's turn
- **Auto-polling UI** — board syncs every 3 seconds for multi-player scenarios
- **Dark theme** — clean developer-focused interface

## API

Base URL: `https://alphagomoku.vercel.app`

### Games

| Method | Endpoint | Body | Description |
|--------|----------|------|-------------|
| `GET` | `/api/games` | — | List all active games |
| `POST` | `/api/games` | `{ rows?, cols? }` | Create a new game |
| `GET` | `/api/games/:id` | — | Get game state |
| `DELETE` | `/api/games/:id` | — | Delete a game |
| `POST` | `/api/games/:id/move` | `{ row, col }` | Place a stone (auto-alternates B/W) |
| `POST` | `/api/games/:id/undo` | — | Undo last move |

### Webhooks

| Method | Endpoint | Body | Description |
|--------|----------|------|-------------|
| `GET` | `/api/games/:id/webhooks` | — | List webhooks |
| `POST` | `/api/games/:id/webhooks` | `{ url, color }` | Subscribe (`color`: `"b"` or `"w"`) |
| `DELETE` | `/api/games/:id/webhooks/:wid` | — | Unsubscribe |

Webhook payload (POST to your URL):

```json
{
  "gameId": "a1b2c3d4",
  "event": "your_turn",
  "color": "b",
  "board": [["b", null, "w", ...]],
  "moves": [{ "row": 4, "col": 4, "color": "b" }],
  "lastMove": { "row": 4, "col": 5, "color": "w" }
}
```

### Quick Start

```bash
# Create a game
curl -X POST https://alphagomoku.vercel.app/api/games \
  -H "Content-Type: application/json" \
  -d '{ "rows": 9, "cols": 9 }'

# Place a move
curl -X POST https://alphagomoku.vercel.app/api/games/GAME_ID/move \
  -H "Content-Type: application/json" \
  -d '{ "row": 4, "col": 4 }'

# Get board state
curl https://alphagomoku.vercel.app/api/games/GAME_ID
```

## Development

```bash
npm install
npm run dev       # starts Vite (frontend) + Express (API) concurrently
```

- Frontend: http://localhost:5173
- API: http://localhost:3001/api (proxied through Vite)

## Architecture

```
gomoku-server/
├── api/index.ts          # Vercel serverless handler (single function)
├── lib/
│   ├── gameStore.ts      # In-memory game store + game logic
│   └── webhook.ts        # Webhook notification dispatcher
├── server.ts             # Express dev server (mirrors api/index.ts)
└── src/
    ├── App.tsx           # Router setup
    ├── pages/
    │   ├── HomePage.tsx  # Game list + create
    │   └── GamePage.tsx  # Board + controls + API guide + webhooks
    └── components/
        ├── Board.tsx     # Grid + stone rendering
        ├── Controls.tsx  # Game info + action buttons
        ├── ApiGuide.tsx  # Interactive curl command builder
        ├── WebhookManager.tsx
        ├── ActivityLog.tsx
        └── GameSetup.tsx
```

State is in-memory and resets on Vercel cold starts.

## Deploy

```bash
npx vercel --prod
```
