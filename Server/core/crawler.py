from multiprocessing import cpu_count, Manager
import os

from bs4 import BeautifulSoup
import requests

from database import PaintingDatabaseHandler, temp_dir
from pool import ProcessPool, ThreadPool

_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) "
                          "AppleWebKit/537.1 (KHTML, like Gecko) "
                          "Chrome/22.0.1207.1 Safari/537.1"}


def parse_url(url, timeout=10):
    return BeautifulSoup(requests.get(url, headers=_headers, timeout=timeout).text, "lxml")


def parse(bound, shared):
    data_lock, print_lock = shared["data_lock"], shared["print_lock"]
    lis, urls, db_handler = shared["lis"], shared["urls"], shared["db_handler"]
    begin, end = bound

    res = []
    for li in lis[begin: end]:
        url = li.find("a")["href"]
        url = url[:url.rfind("/view_as")]
        index = url[url.rfind("-") + 1:]
        if db_handler is None or not db_handler.did_download(index):
            res.append(url)
        else:
            with print_lock:
                print(f"Already exists: {url}")
    with data_lock:
        urls += res


def fetch(url, shared):
    print_lock = shared["print_lock"]
    db_handler, target_dir = shared["db_handler"], shared["target_dir"]
    title = url[url.rfind("/") + 1:]
    index = title[title.rfind("-") + 1:]

    try:
        url = parse_url(url).find("div", class_="artwork").find("img")["src"]
        data = requests.get(url, headers=_headers, timeout=10)
        with open(os.path.join(target_dir, index + ".jpg"), "wb") as f:
            f.write(data.content)

        if db_handler is not None:
            count = f"{db_handler.store_download(index, url)} "
        else:
            count = ""
        with print_lock:
            print(f"{count}{url}")

    except requests.exceptions.Timeout:
        with print_lock:
            print(f"Timeout when download: {url}")


def download(bound, shared):
    begin, end = bound
    pool = ThreadPool(shared["num_thread"], fetch, shared["urls"][begin: end], shared)
    pool.join()


def crawl(max_storage):
    print("Fetching urls")
    max_page = max_storage // 20
    grids_soup = parse_url(f"https://artuk.org/discover/artworks/view_as/grid/page/{max_page}", timeout=1000)
    lis = grids_soup.find("ul", class_="listing-grid listing masonary-grid").find_all("li")
    print()

    print("Parsing urls")
    shared = {"data_lock" : Manager().Lock(),
              "print_lock": Manager().Lock(),
              "lis"       : lis,
              "urls"      : Manager().list(),
              "db_handler": None,
              "target_dir": temp_dir,
              "num_thread": 12}
    num_proc = cpu_count()
    pool = ProcessPool(num_proc, parse, ProcessPool.split_index(lis, num_proc), shared)
    pool.join()
    print()

    print("Download paintings")
    pool = ProcessPool(num_proc, download, ProcessPool.split_index(shared["urls"], num_proc), shared)
    pool.join()
    print()


if __name__ == "__main__":
    crawl(4000)
