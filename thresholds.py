from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from scipy import stats

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
        all_scores = [score for _, score in scored_posts]
        
        # Use original percentileofscore logic but with cached scores - O(n)
        threshold_posts = [
            post for post, score in scored_posts 
            if stats.percentileofscore(all_scores, score) >= self.value
        ]

        return threshold_posts


def get_thresholds():
    """Returns a dictionary mapping lowercase threshold names to values"""

    return {i.get_name(): i.value for i in Threshold}


def get_threshold_from_name(name: str) -> Threshold:
    """Returns Threshold for a given named string"""

    return Threshold[name.upper()]
