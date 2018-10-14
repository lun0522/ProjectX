from multiprocessing import Manager
import os

import requests
from bs4 import BeautifulSoup

from .detector import FaceDetector, LandmarksDetector
from database import PaintingDatabaseHandler

_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) "
                          "AppleWebKit/537.1 (KHTML, like Gecko) "
                          "Chrome/22.0.1207.1 Safari/537.1"}


def parse_url(url, timeout=10):
    return BeautifulSoup(requests.get(url, headers=_headers, timeout=timeout).text, "lxml")


def fetch_image(params):
    url, title, count = params
    try:
        # download the image
        img_url = parse_url(url).find("div", class_="artwork").find("img")["src"]
        img_data = requests.get(img_url, headers=_headers, timeout=10)

        # store the image
        with open(title + ".jpg", "wb") as f:
            f.write(img_data.content)
            count.value += 1
            print(f"No.{count.value} {title}")
            return title, url[:url.rfind("/view_as")]

    except requests.exceptions.Timeout:
        print(f"Timeout when download: {title}")
        return None, None


def crawl(max_storage):
    # view paintings as grids
    max_page = max_storage // 20
    grids_soup = parse_url(f"https://artuk.org/discover/artworks/view_as/grid/page/{max_page}", timeout=1000)
    all_li = grids_soup.find("ul", class_="listing-grid listing masonary-grid").find_all("li")

    # database handler
    db_handler = PaintingDatabaseHandler()

    try:
        # download paintings
        will_fetch = []
        pool = Manager().Pool()
        count = Manager().Value("d", 0)

        for li in all_li:
            url = li.find("a")["href"]
            title_info = li.find("span", class_="title")

            # remove the date info if necessary
            if title_info.find("span", class_="date"):
                title_info.find("span", class_="date").extract()

            # truncate title if necessary (max length of file name is 255)
            title = url[url.find("artworks/") + 9: url.rfind("/view_as")]
            if len(title) > 251:
                print("Title is too long, will be truncated: " + title)
                title = title[:251]

            # only download those haven't been seen before
            if db_handler.did_not_download(title):
                will_fetch.append((url, title, count))
            else:
                print(f"Already exists: {title}")

        for title, url in pool.map(fetch_image, will_fetch):
            if title and url:
                db_handler.store_painting_info(url)
        print("Download finished.")

    except Exception as e:
        print(f"Error in download: {e}")

    finally:
        db_handler.commit()
        db_handler.close()

if __name__ == "__main__":
    crawl(4000)
