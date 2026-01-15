from __future__ import annotations

from typing import TYPE_CHECKING, Type

if TYPE_CHECKING:
    from scorers import Scorer


class ScoredPost:
    def __init__(self, info: dict) -> None:
        self.info = info
        self._score_cache: dict[Type["Scorer"], float] = {}

    @property
    def url(self) -> str:
        return self.info["url"]

    def get_home_url(self, mastodon_base_url: str) -> str:
        return f"{mastodon_base_url}/@{self.info['account']['acct']}/{self.info['id']}"

    def get_score(self, scorer: Scorer) -> float:
        scorer_type = type(scorer)
        if scorer_type not in self._score_cache:
            self._score_cache[scorer_type] = scorer.score(self)
        return self._score_cache[scorer_type]

    @property
    def data(self) -> dict:
        return self.info
