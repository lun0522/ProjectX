import requests
from bs4 import BeautifulSoup
from multiprocessing import Lock, Pool, Manager
import os
from detector import detect
import dbHandler

lock = Lock()  # used for operating the database after each download
headers = {'User-Agent': "Mozilla/5.0 (Windows NT 6.1; WOW64) "
                         "AppleWebKit/537.1 (KHTML, like Gecko) "
                         "Chrome/22.0.1207.1 Safari/537.1"}


def parse_url(url, timeout=10):
    return BeautifulSoup(requests.get(url, headers=headers, timeout=timeout).text, "lxml")


def fetch_image(url, title, count):
    try:
        # download the image
        img_url = parse_url(url).find("div", class_="artwork").find("img")["src"]
        img_data = requests.get(img_url, headers=headers, timeout=10)

        # store the image
        with open(title + ".jpg", "wb") as f:
            f.write(img_data.content)
            lock.acquire()
            dbHandler.store_download_info(title, url[:url.find("/view_as")])
            count.value += 1
            print("No.{} {}".format(count.value, title))
            lock.release()

    except requests.exceptions.Timeout:
        print("Timeout when download: {}".format(title))


def crawl(directory=dbHandler.downloads_dir, max_storage=500, do_detection=True):
    # specify directory to store paintings
    if not os.path.exists(directory):
        os.makedirs(directory)
    os.chdir(directory)

    # view paintings as grids
    max_page = int(max_storage/20)
    grids_soup = parse_url("https://artuk.org/discover/artworks/view_as/grid/page/{}".format(max_page), timeout=1000)
    all_li = grids_soup.find("ul", class_="listing-grid listing masonary-grid").find_all("li")

    try:
        # download paintings
        pool = Pool()
        count = Manager().Value("d", 0)

        for li in all_li:
            url = li.find("a")["href"]
            title_info = li.find("span", class_="title")

            # remove the date info if necessary
            if title_info.find("span", class_="date"):
                title_info.find("span", class_="date").extract()

            # only use the first 30 characters of the title to identify paintings
            normed_title = dbHandler.normalize_title(title_info.get_text())

            # only download those haven't been seen before
            if not dbHandler.retrieve_download_url(normed_title):
                pool.apply_async(fetch_image, args=(url, normed_title, count))
            else:
                print("Already exists: {}".format(normed_title))

        pool.close()
        pool.join()
        print("Download finished.")

    except Exception as e:
        print("Error in download: {}".format(e))

    finally:
        if do_detection:
            detect(directory)


if __name__ == "__main__":
    crawl()
