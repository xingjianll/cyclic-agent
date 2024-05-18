import asyncio
import os

from bilibili_api import search, sync, video, comment, Credential
from dotenv import load_dotenv

load_dotenv()
SESSDATA = os.getenv("SESSDATA")
BILI_JCT = os.getenv("BILI_JCT")
BUVID3 = os.getenv("BUVID3")
credential = Credential(sessdata=SESSDATA,
                        bili_jct=BILI_JCT,
                        buvid3=BUVID3)


async def main():
    # 存储评论
    comments = []
    # 页码
    page = 1
    # 当前已获取数量
    count = 0
    while True:
        # 获取评论
        c = await comment.get_comments(video.Video(bvid='BV1qs4y1B75b').get_aid(),
                                       comment.CommentResourceType.VIDEO,
                                       page,
                                       credential=credential)
        if c['replies']:
            comments.extend(c['replies'])
        # 增加已获取数量
        count += c['page']['size']
        # 增加页码
        page += 1

        if count >= c['page']['count']:
            # 当前已获取数量已达到评论总数，跳出循环
            break

    # 打印评论
    for cmt in comments:
        print(f"{cmt['member']['uname']}: {cmt['content']['message']}")

    # 打印评论总数
    print(f"\n\n共有 {count} 条评论（不含子评论）")


async def main2() -> None:
    # 实例化 Credential 类
    credential = Credential(sessdata=SESSDATA, bili_jct=BILI_JCT, buvid3=BUVID3)
    # 实例化 Video 类
    v = video.Video(bvid="BV1qs4y1B75b", credential=credential)
    info = await v.get_info()
    print(info)
    # 给视频点赞
    await v.like(True)

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())

