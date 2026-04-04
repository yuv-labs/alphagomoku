import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np


class NagiGomokuNet(nn.Module):
    """Reimplementation of Nagi-ovo/alphazero-gomoku GomokuNNet."""

    def __init__(self, board_size=9, num_channels=512, dropout=0.1):
        super().__init__()
        self.board_x = board_size
        self.board_y = board_size
        self.action_size = board_size * board_size

        self.conv1 = nn.Conv2d(1, num_channels, 3, padding=1)
        self.conv2 = nn.Conv2d(num_channels, num_channels, 3, padding=1)
        self.conv3 = nn.Conv2d(num_channels, num_channels, 3)
        self.conv4 = nn.Conv2d(num_channels, num_channels, 3)

        self.bn1 = nn.BatchNorm2d(num_channels)
        self.bn2 = nn.BatchNorm2d(num_channels)
        self.bn3 = nn.BatchNorm2d(num_channels)
        self.bn4 = nn.BatchNorm2d(num_channels)

        fc_size = num_channels * (board_size - 4) * (board_size - 4)
        self.fc1 = nn.Linear(fc_size, 1024)
        self.fc_bn1 = nn.BatchNorm1d(1024)
        self.fc2 = nn.Linear(1024, 512)
        self.fc_bn2 = nn.BatchNorm1d(512)
        self.fc3 = nn.Linear(512, self.action_size)
        self.fc4 = nn.Linear(512, 1)
        self.dropout = dropout

    def forward(self, x):
        # x: (batch, 1, board_x, board_y)
        x = F.relu(self.bn1(self.conv1(x)))
        x = F.relu(self.bn2(self.conv2(x)))
        x = F.relu(self.bn3(self.conv3(x)))
        x = F.relu(self.bn4(self.conv4(x)))
        x = x.view(x.size(0), -1)
        x = F.dropout(F.relu(self.fc_bn1(self.fc1(x))), p=self.dropout, training=self.training)
        x = F.dropout(F.relu(self.fc_bn2(self.fc2(x))), p=self.dropout, training=self.training)
        policy = self.fc3(x)  # raw logits (not log_softmax)
        value = torch.tanh(self.fc4(x))
        return policy, value


def download_weights():
    """Download pretrained weights from HuggingFace if not cached."""
    from huggingface_hub import hf_hub_download
    return hf_hub_download("Nagi-ovo/alphazero-gomoku", "best.pth.tar")


class NagiGame:
    """Adapter to make NagiGomokuNet work with our MCTS/play.py interface."""

    def __init__(self, model_path=None, board_size=9, device='cpu'):
        self.board_size = board_size
        self.device = device

        if model_path is None:
            model_path = download_weights()

        self.model = NagiGomokuNet(board_size=board_size)
        ckpt = torch.load(model_path, map_location=device)
        self.model.load_state_dict(ckpt['state_dict'])
        self.model.to(device)
        self.model.eval()

    def predict(self, board_state):
        """
        board_state: numpy array (board_size, board_size) with 1=current player, -1=opponent, 0=empty
        Returns: (policy, value) where policy is action probabilities, value is float
        """
        with torch.no_grad():
            board = torch.tensor(board_state, dtype=torch.float32).unsqueeze(0).unsqueeze(0).to(self.device)
            policy, value = self.model(board)
            policy = torch.softmax(policy, dim=1).squeeze(0).cpu().numpy()
            value = value.item()
        return policy, value
