from bilibili_api import search, sync



if __name__ == "__main__":
    print(sync(search.search("奥利给")))
