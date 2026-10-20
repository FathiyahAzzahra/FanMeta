"""Model architectures used by the final FanMeta checkpoints.

These definitions intentionally mirror the research notebook.  They contain
only the layers required to load and run the trained checkpoints.
"""

import torch
import torch.nn as nn
from transformers import AutoModel


class RoBERTaSegmentMultiTask(nn.Module):
    """Stage 1 RoBERTa segment encoder with the checkpoint's three heads."""

    def __init__(
        self,
        encoder_model_name: str = "FacebookAI/roberta-base",
        num_rating_classes: int = 4,
        num_warning_labels: int = 4,
        num_tag_labels: int = 16,
    ) -> None:
        super().__init__()
        self.encoder = AutoModel.from_pretrained(encoder_model_name)
        # The research checkpoint was saved with a Transformers version where
        # RobertaEmbeddings persisted this standard buffer in its state dict.
        # Newer versions may omit it.  Restoring the same non-parameter buffer
        # preserves strict checkpoint compatibility without altering any layer
        # or learned weight.
        embeddings = self.encoder.embeddings
        if "position_ids" not in embeddings._buffers:
            embeddings.register_buffer(
                "position_ids",
                torch.arange(self.encoder.config.max_position_embeddings).expand((1, -1)),
                persistent=True,
            )
        else:
            # Transformers in the project virtual environment registers the
            # same [1, 514] buffer as non-persistent.  The training version
            # saved it, so it must be persistent for strict loading.
            embeddings._non_persistent_buffers_set.discard("position_ids")
        hidden = self.encoder.config.hidden_size

        self.dropout = nn.Dropout(0.2)
        self.rating_head = nn.Linear(hidden, num_rating_classes)
        self.warning_head = nn.Linear(hidden, num_warning_labels)
        self.tag_head = nn.Linear(hidden, num_tag_labels)

    def forward(self, input_ids, attention_mask):
        out = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
        cls_embedding = self.dropout(out.last_hidden_state[:, 0, :])

        return {
            "cls_embedding": cls_embedding,
            "rating_logits": self.rating_head(cls_embedding),
            "warning_logits": self.warning_head(cls_embedding),
            "tag_logits": self.tag_head(cls_embedding),
        }


class TaskSpecificLSTMMultiTask(nn.Module):
    """Stage 2 model with independent LSTMs for rating, warning, and tags."""

    def __init__(
        self,
        hidden_size: int = 100,
        input_size: int = 768,
        num_rating_classes: int = 4,
        num_warning_labels: int = 4,
        num_tag_labels: int = 16,
    ) -> None:
        super().__init__()

        self.rating_lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=1,
            batch_first=True,
        )
        self.warning_lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=1,
            batch_first=True,
        )
        self.tag_lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=1,
            batch_first=True,
        )

        self.dropout = nn.Dropout(0.2)
        self.rating_head = nn.Sequential(
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, num_rating_classes),
        )
        self.warning_head = nn.Sequential(
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, num_warning_labels),
        )
        self.tag_head = nn.Sequential(
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, num_tag_labels),
        )

    def _run_lstm(self, lstm, embeddings, lengths):
        packed = nn.utils.rnn.pack_padded_sequence(
            embeddings,
            lengths.cpu(),
            batch_first=True,
            enforce_sorted=False,
        )
        _, (hidden, _) = lstm(packed)
        return self.dropout(hidden[-1])

    def forward(self, embeddings, lengths):
        rating_vector = self._run_lstm(self.rating_lstm, embeddings, lengths)
        warning_vector = self._run_lstm(self.warning_lstm, embeddings, lengths)
        tag_vector = self._run_lstm(self.tag_lstm, embeddings, lengths)

        return {
            "rating_vector": rating_vector,
            "warning_vector": warning_vector,
            "tag_vector": tag_vector,
            "rating_logits": self.rating_head(rating_vector),
            "warning_logits": self.warning_head(warning_vector),
            "tag_logits": self.tag_head(tag_vector),
        }
