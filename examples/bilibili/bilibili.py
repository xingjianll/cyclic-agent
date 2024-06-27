import os
from dataclasses import dataclass
from typing import TypeAlias, Union

import cohere
from bilibili_api import search, sync, Credential, comment, video
from bilibili_api.comment import OrderType, CommentResourceType
from overrides import overrides

from examples.bilibili.fifo import Fifo
from src.state import State
from dotenv import load_dotenv

load_dotenv()
SESSDATA = os.getenv("SESSDATA")
BILI_JCT = os.getenv("BILI_JCT")
BUVID3 = os.getenv("BUVID3")
credential = Credential(sessdata=SESSDATA,
                                bili_jct=BILI_JCT,
                                buvid3=BUVID3)
initial_prompt = """You are a chinese young person who is browsing bilibili, you like anime and vtubers. """
co = cohere.Client(os.environ.get("COHERE_API_KEY"))


@dataclass
class BrowsingVideoInput:
    memory: Fifo


BrowsingVideoReachable: TypeAlias = Union['BrowsingVideo', 'ReadingComments']


class BrowsingVideo(State[BrowsingVideoInput, BrowsingVideoReachable]):
    @overrides
    def _evoke(self, state_input: BrowsingVideoInput) -> BrowsingVideoReachable:
        prompt = (f"Here is your past actions {state_input.memory.prompt()} Generate a keyword phrase for videos "
                  f"you want to watch. Respond with a maximum of three words, in Chinese.")
        prompt = initial_prompt + prompt
        response = co.chat(
            temperature=1,
            message=prompt
        )
        state_input.memory.add(f"searched for {response.text} while browsing video")

        res = sync(search.search_by_type(response.text,
                                         search_type=search.SearchObjectType.VIDEO,
                                         order_type=search.OrderUser.FANS,
                                         order_sort=0
                                         ))
        top_10 = []
        for i in range(10):
            video = res['result'][i]
            top_10.append(f"{i + 1} {video['title']}, {video['play']} plays")
        top_10_str = "\n".join(top_10)

        prompt = initial_prompt + f"""Here are 10 videos: {top_10_str}, return the number that represents the video 
        you want to see the most. Give a number and nothing else."""
        response = co.chat(
            temperature=1,
            message=prompt
        )
        video = res['result'][int(response.text)]
        state_input.memory.add(f"finds {video['title']} interesting while browsing videos")

        next_state_input = ReadingCommentsInput(memory=state_input.memory,
                                                video_bvid=video['bvid'],
                                                video_title=video['title'],
                                                video_description=video['description'])
        return ReadingComments(state_input=next_state_input)


@dataclass
class ReadingCommentsInput:
    memory: Fifo
    video_bvid: str
    video_title: str
    video_description: str


ReadingCommentsReachable: TypeAlias = Union['BrowsingVideo', 'ReadingComments', 'PostComment']


class ReadingComments(State[ReadingCommentsInput, ReadingCommentsReachable]):
    @overrides
    def _evoke(self, state_input: ReadingCommentsInput) -> ReadingCommentsReachable:
        c = sync(comment.get_comments(oid=video.Video(bvid=state_input.video_bvid).get_aid(),
                                      type_=CommentResourceType.VIDEO,
                                      order=OrderType.LIKE,
                                      credential=credential))

        top_10 = []
        for i in range(5):
            cmt = c['replies'][i]
            top_10.append(f"{i + 1} {cmt['member']['uname']}: {cmt['content']['message']}")
        top_10_str = "\n".join(top_10)

        prompt = f"""Here is the context. You are browsing a video called {state_input.video_title}, the description is 
        {state_input.video_description}. Here are 10 comments: {top_10_str}, return the number that represents the 
        comment you want to reply the most. Give a number and nothing else."""
        prompt = initial_prompt + prompt
        response = co.chat(
            temperature=1,
            message=prompt
        )

        cmt = c['replies'][int(response.text)]
        state_input.memory.add(
            f"finds comment: {cmt['content']['message']} interesting while browsing {state_input.video_title}")

        next_state_input = PostCommentInput(memory=state_input.memory,
                                            video_bvid=state_input.video_bvid,
                                            video_title=state_input.video_title,
                                            video_description=state_input.video_description,
                                            reply_to=cmt['content']['message'],
                                            reply_to_oid=cmt['oid'])
        return PostComment(state_input=next_state_input)


@dataclass
class PostCommentInput:
    memory: Fifo
    video_bvid: str
    video_title: str
    video_description: str
    reply_to: str | None
    reply_to_oid: int | None


PostCommentReachable = ReadingComments | BrowsingVideo


class PostComment(State[PostCommentInput, PostCommentReachable]):
    @overrides
    def _evoke(self, state_input: PostCommentInput) -> PostCommentReachable:
        if state_input.reply_to:
            # reply to comment
            prompt = f"""Here is the context. You are browsing a video called {state_input.video_title}, the description 
            is {state_input.video_description}.  You are replying to a comment: {state_input.reply_to}. Return your 
            response to this comment only, in Chinese."""
            prompt = initial_prompt + prompt
            response = co.chat(
                temperature=1,
                message=prompt
            )

            sync(comment.send_comment(text=response.text,
                                      oid=video.Video(bvid=state_input.video_bvid).get_aid(),
                                      type_=CommentResourceType.VIDEO,
                                      credential=credential))

            state_input.memory.add(f"commented {response.text} to {state_input.video_title}")

        next_state_input = BrowsingVideoInput(memory=state_input.memory)
        return BrowsingVideo(next_state_input)


if __name__ == "__main__":
    state_input = BrowsingVideoInput(memory=Fifo())
    state = BrowsingVideo(state_input)
    new_state = state.evoke()
    new_state_2 = new_state.evoke()
    new_state_2.evoke()
    print(state_input.memory.prompt())
