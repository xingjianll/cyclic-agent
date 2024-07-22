from __future__ import annotations
import asyncio
import os
import time
from abc import ABC
from typing import Union
from inspect import cleandoc as I

from bilibili_api import search, Credential, comment, video, dynamic
from bilibili_api.comment import OrderType, CommentResourceType
from bilibili_api.dynamic import BuildDynamic
from cohere import Client
from overrides import overrides
from pydantic import ConfigDict

from cyclic_agent import State
from examples.bilibili_surfer.fifo import Fifo
from cyclic_agent import CyclicExecutor
from dotenv import load_dotenv

load_dotenv()
SESSDATA = os.getenv("SESSDATA")
BILI_JCT = os.getenv("BILI_JCT")
BUVID3 = os.getenv("BUVID3")


class BilibiliStateBase(State[None], ABC):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    initial_prompt: str
    memory: Fifo
    co: Client
    credential: Credential

    def _infer_state_helper(self, *args: str) -> str:
        prompt = I(
            f"""
            {self.initial_prompt}
            Here are your past actions {self.memory.prompt()}.
            Here are the next states you can go to: {", ".join(args)}
            Give the state that you want to go to. 
            1. Give one word and nothing else.
            2. Be creative and try different routes.
            """
        )
        print(prompt)
        text = self.co.chat(temperature=1, message=prompt).text
        print(text)
        return text


type BrowsingVideoReachable = Union[BrowsingVideo, ReadingComments]


class BrowsingVideo(BilibiliStateBase):
    @overrides
    def next(self, signal: None = None) -> BrowsingVideoReachable:
        print('BrowsingVideo')
        prompt = I(
            f"""
            {self.initial_prompt}
            Here are your past actions {self.memory.prompt()} Generate a keyword phrase for videos you want to watch.
            Be creative and avoid repeating. Respond with a maximum of three words in Chinese.
            """
        )
        response = self.co.chat(temperature=1, message=prompt).text
        res = asyncio.run(search.search_by_type(response,
                                                search_type=search.SearchObjectType.VIDEO,
                                                order_type=search.OrderUser.FANS,
                                                order_sort=0
                                                )
                          )
        self.memory.add(f"searched for {response} while browsing video")

        top_10 = []
        for i in range(10):
            video = res['result'][i]
            top_10.append(f"{i + 1} {video['title']}, {video['play']} plays")
        top_10_str = "\n".join(top_10)

        prompt = I(
            f"""
            {self.initial_prompt}
            Here are your past actions {self.memory.prompt()}
            Here are 10 videos: {top_10_str}, return the number that represents the video 
            you want to see the most. Give a number and nothing else.
            """
        )
        response = self.co.chat(temperature=1, message=prompt).text
        video = res['result'][int(response)]
        self.memory.add(f"finds {video['title']} while browsing videos")

        match self._infer_state_helper('BrowsingVideo', 'ReadingComments'):
            case 'BrowsingVideo':
                return self
            case 'ReadingComments':
                return ReadingComments(**self.model_dump(),
                                       video_bvid=video['bvid'],
                                       video_title=video['title'],
                                       video_description=video['description'])


type ReadingCommentsReachable = Union[BrowsingVideo, ReadingComments, PostComment]


class ReadingComments(BilibiliStateBase):
    video_bvid: str
    video_title: str
    video_description: str

    @overrides
    def next(self, signal: None = None) -> ReadingCommentsReachable:
        print('ReadingComments')
        c = asyncio.run(comment.get_comments(oid=video.Video(bvid=self.video_bvid).get_aid(),
                                             type_=CommentResourceType.VIDEO,
                                             order=OrderType.LIKE,
                                             credential=self.credential))
        top_10 = []
        for i in range(min(5, c['page']['count'])):
            cmt = c['replies'][i]
            top_10.append(f"{i + 1} {cmt['member']['uname']}: {cmt['content']['message']}")
        top_10_str = "\n".join(top_10)

        prompt = I(
            f"""
            {self.initial_prompt}
            You are browsing a video called {self.video_title}, the description is {self.video_description}. 
            Here are 10 comments: {top_10_str}, return the number that represents the comment you want to reply most. 
            Give a number and nothing else.
            """
        )
        response = self.co.chat(temperature=1, message=prompt).text
        cmt = c['replies'][int(response)]
        self.memory.add(f"finds comment: {cmt['content']['message']} while browsing {self.video_title}")

        match self._infer_state_helper('BrowsingVideo', 'ReadingComments', 'PostComment'):
            case 'BrowsingVideo':
                return BrowsingVideo(**self.model_dump(exclude={'video_bvid', 'video_title', 'video_description'}))
            case 'ReadingComments':
                return self
            case 'PostComment':
                return PostComment(**self.model_dump(), reply_to=cmt['content']['message'], reply_to_oid=cmt['oid'])


type PostCommentReachable = Union[BrowsingVideo]


class PostComment(BilibiliStateBase):
    video_bvid: str
    video_title: str
    video_description: str
    reply_to: str | None
    reply_to_oid: int | None

    @overrides
    def next(self, signal: None = None) -> PostCommentReachable:
        print('PostComment')
        if self.reply_to:
            prompt = I(
                f"""
                {self.initial_prompt}
                You are browsing a video called {self.video_title}, the description is {self.video_description}.
                You are replying to a comment: {self.reply_to}. Return your response to this comment in Chinese.
                """
            )
            response = self.co.chat(temperature=1, message=prompt).text
            footnote = (
                f"\n I am a bot, and this action was performed automatically. Please contact {os.getenv("name")}"
                f" if you have any questions or concerns."
            )
            asyncio.run(comment.send_comment(text=f"{response} {footnote}",
                                             oid=video.Video(bvid=self.video_bvid).get_aid(),
                                             type_=CommentResourceType.VIDEO,
                                             credential=self.credential))
            self.memory.add(f"commented {response} to {self.video_title}")
            d = BuildDynamic.empty().add_text(
                f"reply to https://www.bilibili.com/video/{self.video_bvid} \n" + f"{response} {footnote}"
            )
            asyncio.run(dynamic.send_dynamic(d, credential=self.credential))

        return BrowsingVideo(memory=self.memory,
                             initial_prompt=self.initial_prompt,
                             co=self.co,
                             credential=self.credential
                             )


if __name__ == "__main__":
    initial_prompt = "You are a dude browsing Bilibili, A Chinese video sharing platform."

    initial_state = BrowsingVideo(memory=Fifo(),
                                  initial_prompt=initial_prompt,
                                  co=Client(os.environ.get("COHERE_API_KEY")),
                                  credential=Credential(sessdata=SESSDATA,
                                                        bili_jct=BILI_JCT,
                                                        buvid3=BUVID3
                                                        )
                                  )
    executor = CyclicExecutor(5)
    executor.start(initial_state)
    time.sleep(1000)
