import os
import torch
import pickle
import numpy as np

from modules.mcts import MCTS
from modules.resnet import ResNet


def _get_next_move(game, mcts, state, player):
    neutral_state = game.change_perspective(state, player)
    mcts_probs = mcts.search(neutral_state)
    action = np.argmax(mcts_probs)
    return mcts_probs, action


def _play_game(game, mcts, player=1):
    state = game.get_initial_state()

    while True:
        print(state)

        if player == 1:
            valid_moves = game.get_valid_moves(state)
            print("valid_moves", [i for i in range(
                game.action_size) if valid_moves[i] == 1])
            action = int(input(f"{player}:"))

            if valid_moves[action] == 0:
                print("action not valid")
                continue

        else:
            mcts_probs, action = _get_next_move(game, mcts, state, player)

        state = game.get_next_state(state, action, player)

        value, is_terminal = game.get_value_and_terminated(state, action)

        if is_terminal:
            print(state)
            if value == 1:
                print(player, "won")
            else:
                print("draw")
            break

        player = game.get_opponent(player)


class Game:
    def __init__(self, game, play_args, iteration=None):
        self.game = game
        self.play_args = play_args
        self.mcts = self._load_mcts(iteration)

    def _find_latest_checkpoint(self, model_dir):
        """Find the latest model checkpoint in the directory."""
        checkpoints = [f for f in os.listdir(model_dir) if f.startswith("model_") and f.endswith(".pt")]
        if not checkpoints:
            return None
        latest = max(int(f.split("_")[1].split(".")[0]) for f in checkpoints)
        return latest

    def _load_mcts(self, iteration=None):
        model_dir = f"models/{self.game}"

        config_path = f"{model_dir}/model_config.pkl"
        if os.path.exists(config_path):
            with open(config_path, "rb") as fr:
                model_config = pickle.load(fr)
        else:
            model_config = {'num_resBlocks': 4, 'num_hidden': 64}

        if iteration is not None:
            target = iteration
        else:
            target = self._find_latest_checkpoint(model_dir)
        if target is None:
            raise FileNotFoundError(f"No model checkpoints found in {model_dir}")

        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Loading model_{target}.pt | config={model_config} | device={device}")

        model = ResNet(self.game, model_config['num_resBlocks'], model_config['num_hidden'], device)
        model.load_state_dict(torch.load(f"{model_dir}/model_{target}.pt", map_location=device))
        model.eval()

        self._model = model
        self._model_dir = model_dir
        self._model_config = model_config
        self._device = device
        self._current_iteration = target

        return MCTS(self.game, self.play_args, model)

    def reload_if_new_checkpoint(self):
        """Check for a newer checkpoint and reload the model if found."""
        latest = self._find_latest_checkpoint(self._model_dir)
        if latest is not None and latest > self._current_iteration:
            print(f"New checkpoint found: model_{latest}.pt (was model_{self._current_iteration}.pt)")
            self._model.load_state_dict(
                torch.load(f"{self._model_dir}/model_{latest}.pt", map_location=self._device))
            self._model.eval()
            self._current_iteration = latest
            return True
        return False

    def play(self, player=1):
        _play_game(self.game, self.mcts, player)

    def get_next_move(self, state, player=1):
        return _get_next_move(self.game, self.mcts, state, player)
