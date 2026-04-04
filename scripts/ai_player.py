import argparse
import os
import sys
import time
import numpy as np
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.game.gomoku import Gomoku
from modules.play import Game


def web_board_to_numpy(board, ai_color):
    """Convert web board format to numpy. AI stones = 1, opponent = -1, empty = 0."""
    rows, cols = len(board), len(board[0])
    state = np.zeros((rows, cols))
    for r in range(rows):
        for c in range(cols):
            cell = board[r][c]
            if cell == ai_color:
                state[r][c] = 1
            elif cell is not None:
                state[r][c] = -1
    return state


def check_game_over(game_logic, board, moves):
    """Check if the game is over using local game logic."""
    if not moves:
        return False, None

    # Build state with b=1, w=-1
    rows, cols = len(board), len(board[0])
    state = np.zeros((rows, cols))
    for r in range(rows):
        for c in range(cols):
            if board[r][c] == "b":
                state[r][c] = 1
            elif board[r][c] == "w":
                state[r][c] = -1

    last = moves[-1]
    action = last["row"] * cols + last["col"]
    value, is_terminal = game_logic.get_value_and_terminated(state, action)

    if is_terminal:
        if value == 1:
            return True, last["color"]
        return True, None  # draw
    return False, None


def main():
    parser = argparse.ArgumentParser(description="AlphaGomoku AI Player (polling)")
    parser.add_argument("--game-id", required=True, help="Game ID to join")
    parser.add_argument("--color", required=True, choices=["b", "w"], help="AI color")
    parser.add_argument("--rows", type=int, default=9, help="Board rows")
    parser.add_argument("--cols", type=int, default=9, help="Board cols")
    parser.add_argument("--in-a-row", type=int, default=5, help="Win condition")
    parser.add_argument("--api-base", default="https://alphagomoku.vercel.app", help="Game API base URL")
    parser.add_argument("--num-searches", type=int, default=400, help="MCTS searches per move")
    parser.add_argument("--poll-interval", type=float, default=2.0, help="Polling interval in seconds")
    parser.add_argument("--iteration", type=int, default=None, help="Model checkpoint iteration (default: latest)")
    parser.add_argument("--model", default="alpha", choices=["alpha", "nagi"], help="Model type: alpha (ours) or nagi (pretrained)")
    args = parser.parse_args()

    game_logic = Gomoku(args.rows, args.cols, args.in_a_row)

    if args.model == "nagi":
        from modules.nagi_net import NagiGame
        print(f"Loading Nagi pretrained model...")
        nagi = NagiGame(board_size=args.rows)
        game_engine = None
        print("Nagi model loaded!")
    else:
        print(f"Loading model for {game_logic}...")
        game_engine = Game(game=game_logic, play_args={
            'C': 2,
            'num_searches': args.num_searches,
            'dirichlet_epsilon': 0.0,
            'dirichlet_alpha': 0.03,
        }, iteration=args.iteration)
        nagi = None
        print("Model loaded!")
    print(f"Game: {args.api_base}/api/games/{args.game_id}")
    print(f"Color: {'Black' if args.color == 'b' else 'White'}")
    print(f"Polling every {args.poll_interval}s\n")

    while True:
        try:
            resp = requests.get(f"{args.api_base}/api/games/{args.game_id}")
            if not resp.ok:
                print(f"API error: {resp.status_code}")
                time.sleep(args.poll_interval)
                continue

            data = resp.json()

            # Check if game is over
            game_over, winner = check_game_over(game_logic, data["board"], data["moves"])
            if game_over:
                if winner:
                    result = "AI wins!" if winner == args.color else "Opponent wins!"
                    print(f"\nGame over! {result} (winner: {winner})")
                else:
                    print("\nGame over! Draw!")
                break

            if data["nextColor"] != args.color:
                time.sleep(args.poll_interval)
                continue

            state = web_board_to_numpy(data["board"], args.color)

            if args.model == "nagi":
                policy, value = nagi.predict(state)
                valid = (state.reshape(-1) == 0).astype(np.uint8)
                policy *= valid
                policy /= policy.sum()
                action = int(np.argmax(policy))
            else:
                if args.iteration is None:
                    game_engine.reload_if_new_checkpoint()
                _, action = game_engine.get_next_move(state, player=1)

            row, col = int(action // args.cols), int(action % args.cols)

            print(f"AI plays: ({row}, {col})")
            move_resp = requests.post(
                f"{args.api_base}/api/games/{args.game_id}/move",
                json={"row": row, "col": col}
            )
            if move_resp.ok:
                print("Move placed successfully")
            else:
                print(f"Move failed: {move_resp.status_code} {move_resp.text}")

        except KeyboardInterrupt:
            print("\nStopped.")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(args.poll_interval)


if __name__ == "__main__":
    main()
