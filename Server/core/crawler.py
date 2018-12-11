from multiprocessing import cpu_count, Manager
import os
import shutil
import time

from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
import requests

from database import PaintingDatabaseHandler, temp_dir
from core.pool import ProcessPool, ThreadPool

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

    except Exception as e:
        with print_lock:
            print(f"Failed to download: {url}")
            print(str(e))


def download(bound, shared):
    begin, end = bound
    pool = ThreadPool(shared["num_thread"], fetch, shared["urls"][begin: end], shared)
    pool.join()


def main(max_storage, target_dir, num_thread):
    print("Fetching urls")
    max_page = max_storage // 20
    grids_soup = parse_url(f"https://artuk.org/discover/artworks/view_as/grid/page/{max_page}", timeout=1000)
    lis = grids_soup.find("ul", class_="listing-grid listing masonary-grid").find_all("li")
    print()

    print("Parsing urls")
    shared = {"data_lock" : Manager().Lock(),
              "print_lock": Manager().Lock(),
              "urls"      : Manager().list(),
              "lis"       : lis,
              "db_handler": None,
              "target_dir": target_dir,
              "num_thread": num_thread}
    num_proc = cpu_count()
    pool = ProcessPool(num_proc, parse, ProcessPool.split_index(lis, num_proc), shared)
    pool.join()
    print()

    print("Download paintings")
    pool = ProcessPool(num_proc, download, ProcessPool.split_index(shared["urls"], num_proc), shared)
    pool.join()
    print()


def test_num_thread(num_threads):
    elapsed_time = []
    if not os.path.exists(temp_dir):
        os.mkdir(temp_dir)

    for num_thread in num_threads:
        shutil.rmtree(temp_dir)
        os.mkdir(temp_dir)
        print(f"Testing {num_thread} threads\n")
        start = time.time()
        main(500, temp_dir, num_thread)
        elapsed_time.append(time.time() - start)
        print(f"Finished testing {num_thread} threads\n")

    fig, ax = plt.subplots()
    ax.plot(num_threads, elapsed_time)
    ax.set_xlabel("Number of Threads")
    ax.set_ylabel("Elapsed Time of Downloading 1000 Images")
    save_path = os.path.join(temp_dir, "benchmark.png")
    plt.savefig(save_path)
    print(f"Benchmark saved to {save_path}")


if __name__ == "__main__":
    test_num_thread([1, 2, 4, 8, 16])
