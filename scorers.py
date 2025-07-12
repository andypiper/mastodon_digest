from __future__ import annotations

import importlib
import inspect
from abc import ABC, abstractmethod
from math import sqrt
from typing import TYPE_CHECKING, Self

from scipy import stats

if TYPE_CHECKING:
    from models import ScoredPost


class Weight(ABC):
    @classmethod
    @abstractmethod
    def weight(cls, scored_post: ScoredPost):
        pass


class UniformWeight(Weight):
    @classmethod
    def weight(cls, scored_post: ScoredPost) -> float:
        return 1.0


class InverseFollowerWeight(Weight):
    @classmethod
    def weight(cls, scored_post: ScoredPost) -> float:
        # Zero out posts by accounts with zero followers that somehow made it to my feed
        followers_count = scored_post.info["account"]["followers_count"]
        if followers_count == 0:
            return 0.0
        # inversely weight against how big the account is
        return 1.0 / sqrt(followers_count)


class Scorer(ABC):
    @classmethod
    @abstractmethod
    def score(cls, scored_post: ScoredPost):
        pass

    @classmethod
    def get_name(cls):
        return cls.__name__.replace("Scorer", "")


class SimpleScorer(UniformWeight, Scorer):
    @classmethod
    def score(cls, scored_post: ScoredPost) -> float:
        if scored_post.info["reblogs_count"] or scored_post.info["favourites_count"]:
            # If there's at least one metric
            # We don't want zeros in other metrics to multiply that out
            # Inflate every value by 1
            metric_average = stats.gmean(
                [
                    scored_post.info["reblogs_count"]+1,
                    scored_post.info["favourites_count"]+1,
                ]
            )
        else:
            metric_average = 0
        return metric_average * super().weight(scored_post)


class SimpleWeightedScorer(InverseFollowerWeight, SimpleScorer):
    @classmethod
    def score(cls, scored_post: ScoredPost) -> float:
        return super().score(scored_post) * super().weight(scored_post)


class ExtendedSimpleScorer(UniformWeight, Scorer):
    @classmethod
    def score(cls, scored_post: ScoredPost) -> float:
        if scored_post.info["reblogs_count"] or scored_post.info["favourites_count"] or scored_post.info["replies_count"]:
            # If there's at least one metric
            # We don't want zeros in other metrics to multiply that out
            # Inflate every value by 1
            metric_average = stats.gmean(
                [
                    scored_post.info["reblogs_count"]+1,
                    scored_post.info["favourites_count"]+1,
                    scored_post.info["replies_count"]+1,
                ],
            )
        else:
            metric_average = 0
        return metric_average * super().weight(scored_post)


class ExtendedSimpleWeightedScorer(InverseFollowerWeight, ExtendedSimpleScorer):
    @classmethod
    def score(cls, scored_post: ScoredPost) -> float:
        return super().score(scored_post) * super().weight(scored_post)


def get_scorers():
    all_classes = inspect.getmembers(importlib.import_module(__name__), inspect.isclass)
    scorers = [c for c in all_classes if c[1] != Scorer and issubclass(c[1], Scorer)]
    return {scorer[1].get_name(): scorer[1] for scorer in scorers}
