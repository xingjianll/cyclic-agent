import asyncio
import os
import time
from dataclasses import dataclass
from typing import TypeAlias, Union

import cohere
from bilibili_api import search, Credential, comment, video, dynamic
from bilibili_api.comment import OrderType, CommentResourceType
from bilibili_api.dynamic import BuildDynamic
from overrides import overrides

from examples.bilibili.fifo import Fifo
from src.executor import CyclicExecutor
from src.state import State
from dotenv import load_dotenv

load_dotenv()
SESSDATA = os.getenv("SESSDATA")
BILI_JCT = os.getenv("BILI_JCT")
BUVID3 = os.getenv("BUVID3")
credential = Credential(sessdata=SESSDATA,
                        bili_jct=BILI_JCT,
                        buvid3=BUVID3)
initial_prompt = """You are a chinese young person who is browsing bilibili, you like anime and vtubers and acgn."""
co = cohere.Client(os.environ.get("COHERE_API_KEY"))


@dataclass
class BrowsingVideoInput:
    memory: Fifo


BrowsingVideoReachable: TypeAlias = Union['BrowsingVideo', 'ReadingComments']


class BrowsingVideo(State[BrowsingVideoInput, BrowsingVideoReachable]):
    @overrides
    def _evoke(self, state_input: BrowsingVideoInput) -> BrowsingVideoReachable:
        prompt = (f"Here is your past actions {state_input.memory.prompt()} Generate a keyword phrase for videos "
                  f"you want to watch, be creative and avoid repeating. Respond with a maximum of three words, in Chinese.")
        prompt = initial_prompt + prompt
        response = co.chat(
            temperature=1,
            message=prompt
        )

        res = asyncio.run(search.search_by_type(response.text,
                                                search_type=search.SearchObjectType.VIDEO,
                                                order_type=search.OrderUser.FANS,
                                                order_sort=0
                                                ))
        state_input.memory.add(f"searched for {response.text} while browsing video")

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
        c = asyncio.run(comment.get_comments(oid=video.Video(bvid=state_input.video_bvid).get_aid(),
                                             type_=CommentResourceType.VIDEO,
                                             order=OrderType.LIKE,
                                             credential=credential))

        top_10 = []
        for i in range(min(5, c['page']['count'])):
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

            after_text = (f"\n I am a bot, and this action was performed automatically. Please contact 八海haha8mi if you "
                          "have any questions or concerns.")
            asyncio.run(comment.send_comment(text=response.text + after_text,
                                             oid=video.Video(bvid=state_input.video_bvid).get_aid(),
                                             type_=CommentResourceType.VIDEO,
                                             credential=credential))
            state_input.memory.add(f"commented {response.text} to {state_input.video_title}")
            d = BuildDynamic.empty().add_text(f"reply to https://www.bilibili.com/video/{state_input.video_bvid} \n" + response.text + after_text)
            asyncio.run(dynamic.send_dynamic(d, credential=credential))

        next_state_input = BrowsingVideoInput(memory=state_input.memory)
        return BrowsingVideo(next_state_input)


if __name__ == "__main__":
    state_input = BrowsingVideoInput(memory=Fifo())
    state = BrowsingVideo(state_input)
    executor = CyclicExecutor(5)
    executor.start(state)
    time.sleep(1000)
