import os, requests, time
import concurrent.futures
from datetime import datetime, timedelta

from PyQt5 import QtCore
from PyQt5.QtCore import QRunnable, QObject, pyqtSlot as Slot

MAX_WORKERS = 15

danbooru_URI_viewed = "https://danbooru.donmai.us/explore/posts/viewed.json?date={date}"
danbooru_URI_post = "https://danbooru.donmai.us/posts.json?page={page}&tags={tag}&limit=100"

lolibooru_URI_post = "https://lolibooru.moe/post.json?page={page}&tags={tag}&limit=100"

rule34_URI_post = "https://api.rule34.xxx/index.php?page=dapi&s=post&q=index&limit=100&pid={page}&tags={tag}&json=1"

headers = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0"
}

class Service:
    def __init__(self, service_name, folder) -> None:
        self.service_name = service_name
        self.folder = folder
        self.urls = []

    def getPage(self, url) -> dict:
        r = requests.get(url)
        return r.json()

class Danbooru(Service):
    def __init__(self, rating: str, tag: str, pages: int, start_page: int, folder: str, most_viewed: bool) -> None:
        super().__init__("Danbooru", folder)
        self.viewed = most_viewed
        self.pages = pages
        self.page = 0
        self.start_page = start_page
        self.ignore_rating = False
        if self.viewed:
            self.date = datetime.now() - timedelta(days=start_page-1)
        if rating == "Ignore Rating":
            self.ignore_rating = True
        elif rating == "General (Completely safe for work)":
            self.rating = "rating:g"
        elif rating == "Sensitive (Ecchi, sexy, suggestive, or mildly erotic)":
            self.rating = "rating:s"
        elif rating == "Questionable (Softcore erotica)":
            self.rating = "rating:q"
        elif rating == "Explicit (Hardcore erotica)":
            self.rating = "rating:e"
        tag = tag.strip()
        self.tag = f"{tag}" if self.ignore_rating else f"{tag}+{self.rating}"

    def checkRating(self, post) -> bool:
        return self.ignore_rating or self.rating[-1] == post["rating"]

    def getUrl(self) -> str:
        if self.viewed:
            url = danbooru_URI_viewed.format(date=self.date.strftime("%Y-%m-%d"))
            self.date -= timedelta(days=1)
        else:
            url = danbooru_URI_post.format(page=self.start_page + self.page, tag=self.tag)
            self.page += 1
        return url
    
    def getPage(self) -> list[str]:
        for _ in range(self.pages):
            url = self.getUrl()
            data = super().getPage(url)
            for post in data:
                _url = post.get("file_url")
                if _url is not None:
                    if self.checkRating(post):
                        self.urls.append(_url)
        return self.urls

class Lolibooru(Service):
    def __init__(self, rating: str, tag: str, pages: int, start_page: int, folder: str) -> None:
        super().__init__("Lolibooru", folder)
        self.pages = pages
        self.page = 0
        self.start_page = start_page
        self.ignore_rating = False
        if rating == "Ignore Rating":
            self.ignore_rating = True
        elif rating == "General (Completely safe for work)":
            self.rating = "rating:g"
        elif rating == "Sensitive (Ecchi, sexy, suggestive, or mildly erotic)":
            self.rating = "rating:s"
        elif rating == "Questionable (Softcore erotica)":
            self.rating = "rating:q"
        elif rating == "Explicit (Hardcore erotica)":
            self.rating = "rating:e"
        tag = tag.strip()
        self.tag = f"{tag}" if self.ignore_rating else f"{tag}+{self.rating}"

    def checkRating(self, post) -> bool:
        return self.ignore_rating or self.rating[-1] == post["rating"]

    def getUrl(self) -> str:
        url = lolibooru_URI_post.format(page=self.start_page + self.page, tag=self.tag)
        self.page += 1
        return url
    
    def getPage(self) -> list[str]:
        for _ in range(self.pages):
            url = self.getUrl()
            data = super().getPage(url)
            for post in data:
                _url = post.get("file_url")
                if _url is not None:
                    if self.checkRating(post):
                        self.urls.append(_url)
        return self.urls

class Rule34(Service):
    def __init__(self, rating: str, tag: str, pages: int, start_page: int, folder: str) -> None:
        super().__init__("Rule34", folder)
        self.pages = pages
        self.page = 0
        self.start_page = start_page
        self.ignore_rating = False
        if rating == "Ignore Rating":
            self.ignore_rating = True
            self.rating = "IGNORE"
        elif rating == "General (Completely safe for work)":
            self.rating = "rating:safe"
        elif rating == "Sensitive (Ecchi, sexy, suggestive, or mildly erotic)":
            self.rating = "rating:questionable"
        elif rating == "Questionable (Softcore erotica)":
            self.rating = "rating:questionable"
        elif rating == "Explicit (Hardcore erotica)":
            self.rating = "rating:explicit"
        self._rating = self.rating.split(":")[-1]
        tag = tag.strip()
        self.tag = f"{tag}" if self.ignore_rating else f"{tag}+{self.rating}"

    def checkRating(self, post) -> bool:
        return self.ignore_rating or self._rating == post["rating"]

    def getUrl(self) -> str:
        url = rule34_URI_post.format(page=self.start_page + self.page, tag=self.tag)
        self.page += 1
        return url
    
    def getPage(self) -> list[str]:
        for _ in range(self.pages):
            url = self.getUrl()
            data = super().getPage(url)
            for post in data:
                _url = post.get("file_url")
                if _url is not None:
                    if self.checkRating(post):
                        self.urls.append(_url)
        return self.urls

def downloadFile(url, output):
    r = requests.get(url)
    image = r.content
    print("Downloading", url, r.status_code)
    with open(f"{output}/{url.split('/')[-1]}", "wb") as f:
        f.write(image)

def getPage(url):
    r = requests.get(url)
    return r.json()

def main(service, rating, tag, pages, start_page, folder, most_viewed, signal):
    match service:
        case "Danbooru":
            serv = Danbooru(rating, tag, pages, start_page, folder, most_viewed)
        case "Lolibooru":
            serv = Lolibooru(rating, tag, pages, start_page, folder)
        case "Rule34":
            serv = Rule34(rating, tag, pages, start_page, folder)
        case _:
            exit()

    urls = serv.getPage()
    files_downloaded = 0
    signal.emit(50)

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_url = {
            executor.submit(downloadFile, url, folder): url
            for url in urls
        }
        for future in concurrent.futures.as_completed(
            future_to_url
        ):
            url = future_to_url[future]
            try:
                future.result()
            except Exception as exc:
                print(
                    "%r generated an exception: %s" % (url, exc)
                )
    signal.emit(100)
    time.sleep(2.2)
    signal.emit(0)

    executor.shutdown()

class Worker(QRunnable):
    '''
    Worker thread

    :param args: Arguments to make available to the run code
    :param kwargs: Keywords arguments to make available to the run code

    '''

    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    @Slot()
    def run(self):
        '''
        Initialise the runner function with passed self.args, self.kwargs.
        '''
        self.fn(*self.args, **self.kwargs)


if __name__ == "__main__":
    main("Danbooru", "General (Completely safe for work)", "genshin_impact", 2, 1, "output", False, None)
    #main("Danbooru", "Explicit (Hardcore erotica)", None, 2, 1, "output", True)
    #main("Rule34", "General (Completely safe for work)", "genshin_impact", 2, 1, "output", False)
    #main("Lolibooru", "Sensitive (Ecchi, sexy, suggestive, or mildly erotic)", "genshin_impact", 2, 1, "output", False)