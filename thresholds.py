from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from models import ScoredPost
    from scorers import Scorer


class Threshold(Enum):
    LAX = 90
    NORMAL = 95
    STRICT = 98

    def get_name(self):
        return self.name.lower()

    def posts_meeting_criteria(
        self, posts: list[ScoredPost], scorer: Scorer
    ) -> list[ScoredPost]:
        """Returns a list of ScoredPosts that meet this Threshold with the given Scorer
        
        Optimized version: Caches scores to avoid recalculation while preserving original logic
        """
        if not posts:
            return []
        
        # Score each post once and cache the result - O(n)
        scored_posts = [(post, post.get_score(scorer)) for post in posts]
        scores = np.array([score for _, score in scored_posts], dtype=float)

        if scores.size == 0:
            return []

        # Vectorized percentile-of-score equivalent
        _, inverse_indices = np.unique(scores, return_inverse=True)
        counts = np.bincount(inverse_indices)
        lt_counts = np.concatenate(([0], np.cumsum(counts[:-1])))
        percentiles = ((lt_counts + 0.5 * counts) / scores.size) * 100.0
        score_percentiles = percentiles[inverse_indices]

        threshold_posts = [
            post
            for (post, _), percentile in zip(scored_posts, score_percentiles)
            if percentile >= self.value
        ]

        return threshold_posts


def get_thresholds():
    """Returns a dictionary mapping lowercase threshold names to values"""

    return {i.get_name(): i.value for i in Threshold}


def get_threshold_from_name(name: str) -> Threshold:
    """Returns Threshold for a given named string"""

    return Threshold[name.upper()]
