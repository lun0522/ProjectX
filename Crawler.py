import requests
from multiprocessing import Pool, Manager
from bs4 import BeautifulSoup as bs
import os
from pathlib import Path

headers = {'User-Agent': "Mozilla/5.0 (Windows NT 6.1; WOW64) "
                         "AppleWebKit/537.1 (KHTML, like Gecko) "
                         "Chrome/22.0.1207.1 Safari/537.1"}


def fetch_image(url, filename, count):
    # open the page that contains the image
    img_html = requests.get(url, headers=headers)
    img_soup = bs(img_html.text, 'lxml')
    img_url = img_soup.find("div", class_="artwork").find("img")["src"]

    # download the image
    img_data = requests.get(img_url, headers=headers)
    with open(filename, "ab") as f:
        f.write(img_data.content)
        count.value += 1
        print("No.%d %s" % (count.value, filename[:-4]))


def crawl(directory="/Users/lun/Desktop/ProjectX/paintings/", max_storage=1000):
    # specify directory to store paintings
    if not os.path.exists(directory):
        os.makedirs(directory)
    os.chdir(directory)

    # view paintings as grids
    max_page = max_storage / 20
    base_url = "https://artuk.org/discover/artworks/view_as/grid//page/" + str(max_page)
    base_html = requests.get(base_url, headers=headers)
    base_soup = bs(base_html.text, 'lxml')
    all_li = base_soup.find("ul", class_="listing-grid listing masonary-grid").find_all("li")

    # download paintings
    pool = Pool()
    count = Manager().Value("d", 0)
    for li in all_li:
        title = li.find("span", class_="title")
        # remove the date info if necessary
        if title.find("span", class_="date"):
            title.find("span", class_="date").extract()
        filename = title.get_text().strip().replace(" ", "-") + ".jpg"
        # only download those not in the directory
        if not Path(filename).is_file():
            pool.apply_async(fetch_image, args=(li.find("a")["href"], filename, count))
    pool.close()
    pool.join()


if __name__ == "__main__":
    crawl()
