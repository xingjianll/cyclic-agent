from __future__ import annotations
import asyncio
import os
import time
from abc import ABC

import cohere
from bilibili_api import search, Credential, comment, video, dynamic
from bilibili_api.comment import OrderType, CommentResourceType
from bilibili_api.dynamic import BuildDynamic
from overrides import overrides
from pydantic import BaseModel, ConfigDict

from cyclic_agent.state import State
from examples.bilibili_surfer.fifo import Fifo
from cyclic_agent.executor import CyclicExecutor
from dotenv import load_dotenv

load_dotenv()
SESSDATA = os.getenv("SESSDATA")
BILI_JCT = os.getenv("BILI_JCT")
BUVID3 = os.getenv("BUVID3")
credential = Credential(sessdata=SESSDATA,
                        bili_jct=BILI_JCT,
                        buvid3=BUVID3)
initial_prompt = """You are a chinese young person who is browsing bilibili_surfer, you like anime and vtubers and 
acgn."""
co = cohere.Client(os.environ.get("COHERE_API_KEY"))


class BilibiliStateMixin(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    memory: Fifo


class BilibiliStateBase(State[None], BilibiliStateMixin, ABC):
    ...


type BrowsingVideoReachable = BrowsingVideo | ReadingComments


class BrowsingVideo(BilibiliStateBase):
    @overrides
    def next(self, signal: None = None) -> BrowsingVideoReachable:
        prompt = (f"Here is your past actions {self.memory.prompt()} Generate a keyword phrase for videos "
                  f"you want to watch, be creative and avoid repeating. Respond with a maximum of three words, "
                  f"in Chinese.")
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
        self.memory.add(f"searched for {response.text} while browsing video")

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
        self.memory.add(f"finds {video['title']} interesting while browsing videos")

        return ReadingComments(**self.model_dump(),
                               video_bvid=video['bvid'],
                               video_title=video['title'],
                               video_description=video['description'])


type ReadingCommentsReachable = BrowsingVideo | ReadingComments | PostComment


class ReadingComments(BilibiliStateBase):
    video_bvid: str
    video_title: str
    video_description: str

    @overrides
    def next(self, signal: None = None) -> ReadingCommentsReachable:
        c = asyncio.run(comment.get_comments(oid=video.Video(bvid=self.video_bvid).get_aid(),
                                             type_=CommentResourceType.VIDEO,
                                             order=OrderType.LIKE,
                                             credential=credential))

        top_10 = []
        for i in range(min(5, c['page']['count'])):
            cmt = c['replies'][i]
            top_10.append(f"{i + 1} {cmt['member']['uname']}: {cmt['content']['message']}")
        top_10_str = "\n".join(top_10)

        prompt = f"""Here is the context. You are browsing a video called {self.video_title}, the description is 
        {self.video_description}. Here are 10 comments: {top_10_str}, return the number that represents the 
        comment you want to reply the most. Give a number and nothing else."""
        prompt = initial_prompt + prompt
        response = co.chat(
            temperature=1,
            message=prompt
        )

        cmt = c['replies'][int(response.text)]
        self.memory.add(
            f"finds comment: {cmt['content']['message']} interesting while browsing {self.video_title}")

        return PostComment(**self.model_dump(),
                           video_bvid=self.video_bvid,
                           video_title=self.video_title,
                           video_description=self.video_description,
                           reply_to=cmt['content']['message'],
                           reply_to_oid=cmt['oid'])


PostCommentReachable = ReadingComments | BrowsingVideo


class PostComment(BilibiliStateBase):
    video_bvid: str
    video_title: str
    video_description: str
    reply_to: str | None
    reply_to_oid: int | None

    @overrides
    def next(self, signal: None = None) -> PostCommentReachable:
        if self.reply_to:
            # reply to comment
            prompt = f"""Here is the context. You are browsing a video called {self.video_title}, the description 
            is {self.video_description}.  You are replying to a comment: {self.reply_to}. Return your 
            response to this comment only, in Chinese."""
            prompt = initial_prompt + prompt
            response = co.chat(
                temperature=1,
                message=prompt
            )

            after_text = (
                f"\n I am a bot, and this action was performed automatically. Please contact {os.getenv("name")} if you "
                "have any questions or concerns.")
            asyncio.run(comment.send_comment(text=response.text + after_text,
                                             oid=video.Video(bvid=self.video_bvid).get_aid(),
                                             type_=CommentResourceType.VIDEO,
                                             credential=credential))
            self.memory.add(f"commented {response.text} to {self.video_title}")
            d = BuildDynamic.empty().add_text(
                f"reply to https://www.bilibili.com/video/{self.video_bvid} \n" + response.text + after_text)
            asyncio.run(dynamic.send_dynamic(d, credential=credential))

        return BrowsingVideo(memory=self.memory)


if __name__ == "__main__":
    initial_state = BrowsingVideo(memory=Fifo())
    executor = CyclicExecutor(5)
    executor.start(initial_state)
    time.sleep(1000)
