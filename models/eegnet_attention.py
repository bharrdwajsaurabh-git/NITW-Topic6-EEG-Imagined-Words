"""
models/eegnet_attention.py
==========================
Deep Spatial-Temporal Neural Network with Attention for EEG Imagined Speech Decoding.
Combines:
1. EEGNet-style 2D Spatio-Temporal Convolutions (Lawhern et al., J. Neural Eng)
2. Bidirectional LSTM for sequence dynamics
3. Scaled Dot-Product Temporal Attention pooling
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class TemporalSelfAttention(nn.Module):
    """
    Self-Attention pooling layer that computes attention weights across
    time steps to focus on peak cognitive intent epochs.
    """
    def __init__(self, hidden_dim: int):
        super().__init__()
        self.attn_weights = nn.Linear(hidden_dim, 1, bias=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x shape: (batch_size, time_steps, hidden_dim)
        scores = self.attn_weights(x)  # (batch_size, time_steps, 1)
        weights = F.softmax(scores, dim=1)
        context = torch.sum(x * weights, dim=1)  # (batch_size, hidden_dim)
        return context


class EEGNetAttention(nn.Module):
    """
    State-of-the-art End-to-End Deep Learning Architecture for EEG Decoding.
    
    Input shape: (Batch, 1, Channels, Time) -> (B, 1, 14, 128)
    Output shape: (Batch, Num_Classes)
    """
    def __init__(
        self,
        n_classes: int = 9,
        n_channels: int = 14,
        n_samples: int = 128,
        f1: int = 16,             # Temporal filters
        d: int = 2,               # Depth multiplier (spatial filters = f1 * d)
        f2: int = 32,             # Pointwise filters
        kernel_length: int = 32,  # Temporal filter length
        dropout_rate: float = 0.3
    ):
        super().__init__()
        self.n_classes = n_classes
        self.n_channels = n_channels

        # Block 1: Temporal Conv + Depthwise Spatial Conv
        self.conv1 = nn.Conv2d(
            in_channels=1,
            out_channels=f1,
            kernel_size=(1, kernel_length),
            padding=(0, kernel_length // 2),
            bias=False
        )
        self.bn1 = nn.BatchNorm2d(f1)

        # Depthwise Spatial Convolution across all EEG electrode channels
        self.depthwise = nn.Conv2d(
            in_channels=f1,
            out_channels=f1 * d,
            kernel_size=(n_channels, 1),
            groups=f1,
            bias=False
        )
        self.bn2 = nn.BatchNorm2d(f1 * d)
        self.pool1 = nn.AvgPool2d(kernel_size=(1, 4))
        self.drop1 = nn.Dropout(dropout_rate)

        # Block 2: Separable Convolution
        self.separable_depth = nn.Conv2d(
            in_channels=f1 * d,
            out_channels=f1 * d,
            kernel_size=(1, 16),
            padding=(0, 8),
            groups=f1 * d,
            bias=False
        )
        self.separable_point = nn.Conv2d(
            in_channels=f1 * d,
            out_channels=f2,
            kernel_size=(1, 1),
            bias=False
        )
        self.bn3 = nn.BatchNorm2d(f2)
        self.pool2 = nn.AvgPool2d(kernel_size=(1, 4))
        self.drop2 = nn.Dropout(dropout_rate)

        # Sequential Recurrent Block (BiLSTM)
        # Determine temporal output size dynamically
        with torch.no_grad():
            dummy = torch.zeros(1, 1, n_channels, n_samples)
            x = self.conv1(dummy)
            x = self.bn1(x)
            x = self.depthwise(x)
            x = self.bn2(x)
            x = F.elu(x)
            x = self.pool1(x)
            x = self.separable_depth(x)
            x = self.separable_point(x)
            x = self.bn3(x)
            x = F.elu(x)
            x = self.pool2(x)
            # x shape: (1, f2, 1, time_out)
            self.time_out = x.shape[3]

        self.lstm = nn.LSTM(
            input_size=f2,
            hidden_size=48,
            num_layers=1,
            batch_first=True,
            bidirectional=True
        )

        # Attention layer across BiLSTM states
        self.attention = TemporalSelfAttention(hidden_dim=48 * 2)

        # Final Classifier
        self.classifier = nn.Sequential(
            nn.Linear(48 * 2, 64),
            nn.ReLU(),
            nn.Dropout(dropout_rate),
            nn.Linear(64, n_classes)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # Input: (Batch, Channels, Time) or (Batch, 1, Channels, Time)
        if x.dim() == 3:
            x = x.unsqueeze(1)

        # Block 1: Temporal + Spatial
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.depthwise(x)
        x = self.bn2(x)
        x = F.elu(x)
        x = self.pool1(x)
        x = self.drop1(x)

        # Block 2: Separable Conv
        x = self.separable_depth(x)
        x = self.separable_point(x)
        x = self.bn3(x)
        x = F.elu(x)
        x = self.pool2(x)
        x = self.drop2(x)

        # Reshape for LSTM: (Batch, Channels, 1, Time) -> (Batch, Time, Channels)
        x = x.squeeze(2).permute(0, 2, 1)

        lstm_out, _ = self.lstm(x)  # (Batch, Time, 96)
        context = self.attention(lstm_out)  # (Batch, 96)
        logits = self.classifier(context)  # (Batch, n_classes)

        return logits


if __name__ == "__main__":
    model = EEGNetAttention(n_classes=9, n_channels=14, n_samples=128)
    test_input = torch.randn(8, 14, 128)
    out = model(test_input)
    print("EEGNetAttention successfully tested. Input:", test_input.shape, "-> Output:", out.shape)
