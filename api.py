import os
import json
import urllib.request
import urllib.parse
from typing import *

use_cache: bool = True
user_agent: dict[str, str] = {"User-Agent": "Not Enough Runes Scraper/1.0 (+HannahRyanster@gmail.com)"}


def get_wiki_api(args: dict[str, str], continue_key: str) -> Iterator[any]:
    args["format"] = "json"
    while True:
        url = "https://oldschool.runescape.wiki/api.php?" + urllib.parse.urlencode(args)
        print("Grabbing " + url)
        with urllib.request.urlopen(urllib.request.Request(url, headers=user_agent)) as raw:
            js = json.load(raw)

        yield js
        if "continue" in js:
            args[continue_key] = js["continue"][continue_key]
        else:
            return


def get_wiki_ask_api(args: dict[str, str]) -> Iterator[any]:
    args["format"] = "json"
    args["query"] += "|limit=500|offset=0"
    offset = 0

    while True:
        if offset > 5000:
            print("Offset beyond 5000. Aborting ask call")
            return
        args["query"] = args["query"][0:(args["query"].index("|offset=") + 8)] + str(offset)
        url = "https://oldschool.runescape.wiki/api.php?" + urllib.parse.urlencode(args)
        print("Grabbing " + url)
        with urllib.request.urlopen(urllib.request.Request(url, headers=user_agent)) as raw:
            js = json.load(raw)

        yield js
        if len(js["query"]["results"]) < 500:
            return
        else:
            offset += 500


def query_category(category_name: str) -> dict[str, str]:
    """
    query_category returns a dict of page title to page wikitext
    you can then use mwparserfromhell to parse the wikitext into
    an ast
    """
    cache_file_name = category_name + ".cache.json"
    if use_cache and os.path.isfile(cache_file_name):
        with open(cache_file_name, "r") as fi:
            return json.load(fi)

    pageids = []
    for res in get_wiki_api(
            {
                "action": "query",
                "list": "categorymembers",
                "cmlimit": "500",
                "cmtitle": "Category:" + category_name,
            }, "cmcontinue"):

        for page in res["query"]["categorymembers"]:
            pageids.append(str(page["pageid"]))

    pages = {}
    for i in range(0, len(pageids), 50):
        for res in get_wiki_api(
                {
                    "action": "query",
                    "prop": "revisions",
                    "rvprop": "content",
                    "pageids": "|".join(pageids[i:i + 50]),
                }, "rvcontinue"):
            for page_id, page in res["query"]["pages"].items():
                pages[page["title"]] = page["revisions"][0]["*"]

    with open(cache_file_name, "w+") as fi:
        json.dump(pages, fi)

    return pages


def ask_category_production(category_name: str) -> List[str]:
    """
    query_category_production returns a list of all Production JSON
    properties in a given category
    """
    cache_file_name = category_name + "-production" + ".cache.json"
    if use_cache and os.path.isfile(cache_file_name):
        with open(cache_file_name, "r") as fi:
            return json.load(fi)

    items = []
    for res in get_wiki_ask_api(
            {
                "action": "ask",
                "query": "[[Category:" + category_name + "]][[Production JSON::+]]|?Production JSON",
            }):

        for item in res["query"]["results"]:
            for recipe in res["query"]["results"][item]["printouts"]["Production JSON"]:
                items.append(json.loads(str(recipe)))

    with open(cache_file_name, "w+") as fi:
        json.dump(items, fi)

    return items
