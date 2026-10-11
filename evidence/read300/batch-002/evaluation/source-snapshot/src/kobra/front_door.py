"""English normalization using preserved rules and explicit client vocabulary."""

from dataclasses import dataclass

from . import _english_front_door as rules
from .contracts import Diagnostic, Request, Services, TextView


@dataclass(frozen=True)
class DomainVocabulary:
    """Surface words, not executable capabilities or inferred linguistic synonyms.

    Clients provide the forms they want recognized, including plurals. Known
    names participate in splitting only; they never license typo correction.
    Operations and dual verbs are vocabulary, not permission to execute anything.
    """

    nouns: frozenset[str] = frozenset()
    operations: frozenset[str] = frozenset()
    statuses: frozenset[str] = frozenset()
    protected_words: frozenset[str] = frozenset()
    dual_verbs: frozenset[str] = frozenset()
    non_verbs: frozenset[str] = frozenset()
    known_names: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        for field in self.__dataclass_fields__:
            words = getattr(self, field)
            if not isinstance(words, frozenset):
                raise TypeError(f"{field} must be a frozenset")
            if any(
                not isinstance(word, str) or not word or word != word.lower()
                for word in words
            ):
                raise ValueError(f"{field} must contain nonempty lowercase strings")


@dataclass(frozen=True)
class EnglishFrontDoor:
    """No Gorgon imports, model calls, global client state or world lookup."""

    vocabulary: DomainVocabulary

    def normalize(self, request: Request, services: Services) -> TextView:
        view = rules.read(
            request.text, board=self.vocabulary, known=self.vocabulary.known_names
        )
        return TextView(
            original=request.text,
            text=view.text,
            back=tuple(view.back),
            diagnostics=tuple(
                Diagnostic("front-door.notice", notice) for notice in view.notices
            ),
        )
