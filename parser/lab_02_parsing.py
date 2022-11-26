import json
import logging
import logging.config
import os
import random
import re
import shutil
import time
from pathlib import Path
from typing import List

import requests
import unidecode
from bs4 import BeautifulSoup
from tqdm.auto import tqdm


def filter_warning(level):
    level = getattr(logging, level)

    def filter(record):
        return record.levelno <= level

    return filter


with open("logger.json") as f_src:
    logger_conf = json.load(f_src)
logging.config.dictConfig(logger_conf)
logger = logging.getLogger(os.path.basename(__file__))

TITLE_BLACK_LIST = [
    "tt14230388", "tt16426418", "tt11399896", "tt15939198", "tt21438352", "tt2028582", "tt4495098", "tt7428530", "tt10767052", "tt11358390",
    "tt11057302", "tt17505010", "tt1856080", "tt2049403", "tt8917520", "tt14948432", "tt5112584", "tt13957560", "tt17277414", "tt15767808", 
    "tt15000156", "tt10128846", "tt1297123", "tt13055264", "tt0234463", "tt13368242", "tt12760338", "tt12176466", "tt21816732", "tt3443768",
    "tt16311594", "tt21806332", "tt18079362", "tt9817210", "tt6436620", "tt11858066", "tt21434318", "tt12226632", "tt5302918", "tt5177114",
    "tt5113010", "tt3542810", "tt5177120", "tt22773644", "tt2572212", "tt1756855", "tt7510222", "tt18310498", "tt6113186", "tt1037226",
    "tt22769820", "tt15153532", "tt1609486", "tt3083016", "tt17024450", "tt21454134", "tt21366490", "tt22872838", "tt13027412", "tt21064584",
    "tt11152168", "tt8521778", "tt15507512", "tt20202136", "tt9646562", "tt9613354", "tt14961624", "tt1340094", "tt19850008", "tt0800175",
    "tt14301644", "tt5950044", "tt4121026", "tt16357306", "tt8689532", "tt18251512", "tt12280510", "tt0421201", "tt10954646", "tt8814476",
    "tt6569988", "tt12985294", "tt19845348", "tt1262421", "tt1498780", "tt3402242", "tt5996672",
]

NEW_BLACK_LIST = []

BASE_URL = "https://www.imdb.com"
GENRE_URL = BASE_URL + "/feature/genre/"
TITLE_URL = BASE_URL + "/title/{id}"
SUMMARY_URL = TITLE_URL + "/plotsummary"


def process_film(
    genre_dir: Path,
    film_card_soup: BeautifulSoup,
    sleep_range_seconds: List[int] = None,
) -> str:
    if sleep_range_seconds is None:
        sleep_range_seconds = [0, 2]

    # Извлечение заголовка, в котором содержатся title_id и name_raw
    # ================================================================================================================
    header = unidecode.unidecode(film_card_soup.find("h3", {"class": "lister-item-header"}).find("a"))

    href = header.attrs["href"]
    title_id = re.match(r"^\/title\/(\S+)\/$", href).group(1)
    film_url = TITLE_URL.format(id=title_id)
    # logger.debug(f"href: {repr(href)}")
    logger.debug(f"title_id: {repr(title_id)}")
    logger.debug(f"film_url: {repr(film_url)}")

    name_raw = unidecode.unidecode(header.text.strip())
    logger.debug(f"name_raw: {repr(name_raw)}")

    if title_id in TITLE_BLACK_LIST:
        logger.debug(f"Film {repr(name_raw)} in black list!")
        return title_id

    if title_id in NEW_BLACK_LIST:
        logger.debug(f"Film {repr(name_raw)} in NEW black list!")
        return title_id
    # ================================================================================================================

    # Создание директории для фильма, если там уже есть есть файлы info.json и poster.jpg, то пропуск
    # иначе содержимое этих файлов перезапишется
    # ================================================================================================================
    film_dir = Path(genre_dir, title_id)
    if not film_dir.exists():
        film_dir.mkdir()
        logger.debug(f"Folder '{film_dir}' was created")
    else:
        logger.debug(f"Folder '{film_dir}' already exists")
        if len(set(["info.json", "poster.jpg"]) - {p.name for p in film_dir.glob("./*")}) == 0:
            logger.debug(f"Film '{name_raw}'[{title_id}] already dumped")
            return title_id
    # ================================================================================================================

    # Извлечение оригинального названия фильма и ссылки на скачивание постера
    # ================================================================================================================
    time.sleep(random.randint(*sleep_range_seconds))
    film_response = requests.get(film_url)
    film_response.raise_for_status()

    film_soup = BeautifulSoup(film_response.content, "lxml")

    try:
        title_name_compile = re.compile("^Original title: (.+)$")
        name_text = unidecode.unidecode(film_soup.find("div", text=title_name_compile).text.strip())
        logger.debug(f"name_text: {repr(name_text)}")

        name = title_name_compile.match(name_text).group(1)
    except AttributeError:
        logger.debug(f"{title_id}: there is no original title (name_raw = {repr(name_raw)})")
        name = name_raw
    logger.debug(f"name: {repr(name)}")

    try:
        poster_url = film_soup.find("div", {"class": "ipc-media"}).find("img").attrs["srcset"].split()[-2]
        logger.debug(f"poster_url: {repr(poster_url)}")
    except AttributeError:
        logger.debug(f"{title_id}: there is no poster image (name = {repr(name)})")
        NEW_BLACK_LIST.append(title_id)

        return title_id

    # Извлечение описания
    # ================================================================================================================
    summary_soup = BeautifulSoup(requests.get(SUMMARY_URL.format(id=title_id)).content, "lxml")

    description = unidecode.unidecode(
        summary_soup.find("ul", attrs={"id": "plot-summaries-content"}).find("p").text.strip()
    )
    logger.debug(f"description: {repr(description)}")
    # ================================================================================================================

    logger.debug(" | ".join([title_id, genre_dir.name, name, description]))
    # ================================================================================================================

    # Сохранение информации о фильме и его постера
    # ================================================================================================================
    info_path = Path(film_dir, "info.json")
    info_json = {
        "title_id": title_id,
        "genre": genre_dir.name,
        "name": name,
        "description": description,
        "poster_url": poster_url,
    }
    with open(info_path, "w") as handler:
        json.dump(info_json, handler)
        logger.debug(f"File '{info_path}' was created")

    poster_path = Path(film_dir, "poster.jpg")
    poster_content = requests.get(poster_url).content
    with open(poster_path, "wb") as handler:
        handler.write(poster_content)
        logger.debug(f"File '{poster_path}' was created")
    # ================================================================================================================

    return title_id


def process_genre(
    root_dir: Path,
    film_genre: str,
    search_link: str,
    count_films: int = 7,
    max_attempt_num: int = 3,
    sleep_break_seconds: int = 5,
    max_count_on_page: int = 250,
) -> Path:
    logger.debug(f"Process: {film_genre}")

    genre_dir = Path(root_dir, film_genre)
    if not genre_dir.exists():
        genre_dir.mkdir()
        logger.debug(f"Folder '{genre_dir}' was created")
    else:
        genre_films = list(genre_dir.glob("./*"))
        if len(genre_films) < count_films:
            logger.debug(f"Continued dumping of the '{film_genre}' genre")
        else:
            logger.debug(f"Genre '{film_genre}' already dumped")
            return genre_dir

    page_count = count_films // max_count_on_page + (count_films % max_count_on_page > 0)

    for page_num in range(page_count):
        start_idx = page_num * max_count_on_page + 1
        count_on_page = min(max_count_on_page, count_films - start_idx + 1)

        search_genre_url = BASE_URL + search_link + f"&start={start_idx}&count={count_on_page}"
        logger.debug(f"search_genre_url: {repr(search_genre_url)}")

        response = requests.get(search_genre_url)
        response.raise_for_status()

        genre_soup = BeautifulSoup(response.content, "lxml")

        for film in tqdm(
            genre_soup.find("div", {"class": "lister list detail sub-list"}).find_all(
                "div", {"class": "lister-item mode-advanced"}
            ),
            desc=f"Films loop [{genre}]",
        ):
            attempt_num = 1
            film_title_id = None

            while film_title_id is None and attempt_num <= max_attempt_num:
                try:
                    film_title_id = process_film(genre_dir, film)
                except Exception as err:
                    logger.error(f"Attempt {attempt_num} out of {max_attempt_num} was failed: {err}")

                    attempt_num += 1
                    if attempt_num > max_attempt_num:
                        logger.error(f"Need to add this title_id to the black_list")
                    else:
                        time.sleep(sleep_break_seconds)

    return genre_dir


def process_genre_by_keyword(
    root_dir: Path,
    film_genre: str,
    search_link: str,
    count_films: int = 7,
    max_attempt_num: int = 3,
    sleep_break_seconds: int = 5,
) -> Path:
    logger.debug(f"Process: {film_genre}")

    genre_dir = Path(root_dir, film_genre)
    if not genre_dir.exists():
        genre_dir.mkdir()
        logger.debug(f"Folder '{genre_dir}' was created")
    else:
        genre_films = list(genre_dir.glob("./*"))
        if len(genre_films) < count_films:
            logger.debug(f"Continued dumping of the '{film_genre}' genre")
        else:
            logger.debug(f"Genre '{film_genre}' already dumped")
            return genre_dir

    max_count_on_page = 50
    page_count = count_films // max_count_on_page + (count_films % max_count_on_page > 0)

    for page_num in range(page_count):
        search_genre_url = BASE_URL + search_link + f"&page={page_num + 1}"
        logger.debug(f"search_genre_url: {repr(search_genre_url)}")

        response = requests.get(search_genre_url)
        response.raise_for_status()

        genre_soup = BeautifulSoup(response.content, "lxml")

        for film in tqdm(
            genre_soup.find("div", {"class": "lister list detail sub-list"}).find_all(
                "div", {"class": "lister-item-content"}
            ),
            desc=f"Films loop [{genre}]",
        ):
            attempt_num = 1
            film_title_id = None

            while film_title_id is None and attempt_num <= max_attempt_num:
                try:
                    film_title_id = process_film(genre_dir, film)
                except Exception as err:
                    logger.error(f"Attempt {attempt_num} out of {max_attempt_num} was failed: {err}")

                    attempt_num += 1
                    if attempt_num > max_attempt_num:
                        logger.error(f"Need to add this title_id to the black_list")
                    else:
                        time.sleep(sleep_break_seconds)

    return genre_dir


def get_genre_links() -> dict:
    response = requests.get(GENRE_URL)
    soup = BeautifulSoup(response.content, "lxml")

    genres_dict = {}

    for g in [
        {s.find("a").text.strip().lower(): s.find("a").attrs["href"]}
        for s in soup.find("div", {"class": "ab_links"}).find_all("div", {"class": "table-cell primary"})
    ]:
        genres_dict.update(g)

    return genres_dict


if __name__ == "__main__":
    dataset_dir = Path("dataset")
    if not dataset_dir.exists():
        logger.warning(f"Folder '{dataset_dir}' is not exist")
        dataset_dir.mkdir()
        logger.info(f"Folder '{dataset_dir}' was created")

    genres_dict = get_genre_links()
    logger.debug(genres_dict)

    number_films = 500
    logger.info(f"Start downloading {number_films} films for each of {len(genres_dict.keys())} genres")

    try:
        for genre, link in tqdm(genres_dict.items(), desc="Genres loop: "):
            if "/keyword?" in link:
                genre_dir = process_genre_by_keyword(dataset_dir, genre, link, number_films)
            else:
                genre_dir = process_genre(dataset_dir, genre, link, number_films)

        folders_to_remove = [
            film_dir
            for film_dir in dataset_dir.glob("./*/*")
            if len(set(["info.json", "poster.jpg"]) - {f.name for f in film_dir.glob("./*")}) > 0
        ]
        if len(folders_to_remove) > 0:
            logger.warning(
                f"Folders {[f.as_posix() for f in folders_to_remove]} will be deleted because they are incorrect"
            )
            for film_dir in folders_to_remove:
                shutil.rmtree(film_dir, ignore_errors=True)

        if len(NEW_BLACK_LIST) > 0:
            logger.warning(f"Add titles id {NEW_BLACK_LIST} to the BLACK_LIST")

    except Exception as err:
        logger.error(err)
