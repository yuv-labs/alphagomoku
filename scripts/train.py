import argparse
import os
import pickle
import sys
import torch
from tqdm import trange

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.game.gomoku import Gomoku
from modules.resnet import ResNet
from modules.alphazero import AlphaZeroParallel


def main():
    parser = argparse.ArgumentParser(description="AlphaZero Gomoku Training")
    parser.add_argument("--rows", type=int, default=9, help="Board rows")
    parser.add_argument("--cols", type=int, default=9, help="Board cols")
    parser.add_argument("--in-a-row", type=int, default=5, help="Win condition")
    parser.add_argument("--res-blocks", type=int, default=5, help="Number of residual blocks")
    parser.add_argument("--hidden", type=int, default=64, help="Hidden channels")
    parser.add_argument("--iterations", type=int, default=8, help="Training iterations")
    parser.add_argument("--self-play-games", type=int, default=500, help="Self-play games per iteration")
    parser.add_argument("--parallel-games", type=int, default=20, help="Parallel games")
    parser.add_argument("--num-searches", type=int, default=100, help="MCTS searches per move")
    parser.add_argument("--epochs", type=int, default=4, help="Training epochs per iteration")
    parser.add_argument("--batch-size", type=int, default=64, help="Batch size")
    parser.add_argument("--lr", type=float, default=0.001, help="Learning rate")
    args = parser.parse_args()

    game = Gomoku(args.rows, args.cols, args.in_a_row)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")

    model = ResNet(game, args.res_blocks, args.hidden, device)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr, weight_decay=1e-4)

    train_args = {
        'C': 2,
        'num_searches': args.num_searches,
        'num_iterations': args.iterations,
        'num_selfPlay_iterations': args.self_play_games,
        'num_parallel_games': args.parallel_games,
        'num_epochs': args.epochs,
        'batch_size': args.batch_size,
        'temperature': 1.25,
        'dirichlet_epsilon': 0.25,
        'dirichlet_alpha': 0.03,
    }

    model_dir = f"models/{game}"
    os.makedirs(model_dir, exist_ok=True)

    with open(f"{model_dir}/model_config.pkl", "wb") as fw:
        pickle.dump({'num_resBlocks': args.res_blocks, 'num_hidden': args.hidden}, fw)

    # Resume from checkpoint
    start_iteration = 0
    existing = [f for f in os.listdir(model_dir) if f.startswith("model_") and f.endswith(".pt")]
    if existing:
        latest = max(int(f.split("_")[1].split(".")[0]) for f in existing)
        print(f"Resuming from iteration {latest + 1}")
        model.load_state_dict(torch.load(f"{model_dir}/model_{latest}.pt", map_location=device))
        optimizer.load_state_dict(torch.load(f"{model_dir}/optimizer_{latest}.pt", map_location=device))
        start_iteration = latest + 1

    print(f"Game: {game}")
    print(f"Model: {args.res_blocks} ResBlocks, {args.hidden} hidden")
    print(f"Iterations: {start_iteration} -> {args.iterations}")

    alphaZero = AlphaZeroParallel(model, optimizer, game, train_args)

    for iteration in range(start_iteration, args.iterations):
        print(f"\n=== Iteration {iteration}/{args.iterations - 1} ===")
        memory = []

        model.eval()
        for _ in trange(args.self_play_games // args.parallel_games, desc="Self-play"):
            memory += alphaZero.selfPlay()

        print(f"Self-play complete: {len(memory)} samples")

        model.train()
        for _ in trange(args.epochs, desc="Training"):
            alphaZero.train(memory)

        torch.save(model.state_dict(), f"{model_dir}/model_{iteration}.pt")
        torch.save(optimizer.state_dict(), f"{model_dir}/optimizer_{iteration}.pt")
        print(f"Checkpoint saved: model_{iteration}.pt")

    train_args['num_iterations'] = args.iterations
    with open(f"{model_dir}/train_args.pkl", "wb") as fw:
        pickle.dump(train_args, fw)

    print("\nTraining complete!")


if __name__ == "__main__":
    main()
