import os
from dataclasses import dataclass
from typing import TypeAlias, Union

import cohere
from bilibili_api import search, sync
from overrides import overrides

from src.state import State


@dataclass
class BrowsingVideoInput:
    ...


BrowsingVideoReachable: TypeAlias = Union['BrowsingVideo', 'ReadingComments']


class BrowsingVideo(State[BrowsingVideoInput, BrowsingVideoReachable]):
    @overrides
    def _evoke(self, state_input: BrowsingVideoInput) -> BrowsingVideoReachable:
        prompt = """You are a chinese young person who is browsing bilibili, you like anime and vtubers. Generate a 
        keyword phrase for videos you want to watch. Respond with a maximum of three words, in chinese."""

        co = cohere.Client(os.environ.get("COHERE_API_KEY"))

        response = co.chat(
            temperature=0.5,
            message=prompt
        )

        print(response.text)

        res = sync(search.search_by_type(response.text,
                                         search_type=search.SearchObjectType.VIDEO,
                                         order_type=search.OrderUser.FANS,
                                         order_sort=0
                                         ))

        print(res)
        return ReadingComments(state_input=ReadingCommentsInput())


@dataclass
class ReadingCommentsInput:
    ...


ReadingCommentsReachable: TypeAlias = Union['BrowsingVideo', 'ReadingComments', 'PostComment']


class ReadingComments(State[ReadingCommentsInput, ReadingCommentsReachable]):
    ...


@dataclass
class PostCommentInput:
    ...


PostCommentReachable = ReadingComments | BrowsingVideo


class PostComment(State[PostCommentInput, PostCommentReachable]):
    ...


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    state = BrowsingVideo(BrowsingVideoInput())
    state.evoke()