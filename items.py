import hashlib
import json
import os
import re
import traceback
from typing import Dict

import api
import mwparserfromhell as mw

import util

output_dir = "output/"


def get_production():
    print("Scraping recipes")
    item_production = api.ask_category_production("Items")
    name = "items-production.json"
    min_name = "items-production.min.json"

    with open(output_dir + name, "w+") as fi:
        json.dump(item_production, fi, indent=2, sort_keys=True)

    with open(output_dir + min_name, "w+") as fi:
        json.dump(item_production, fi, separators=(",", ":"), sort_keys=True)


def get_shop_items():
    print("Scraping shops")
    file_name = "items-shopitems.json"
    min_name = "items-shopitems.min.json"

    page_data = api.query_category("Shops")
    page_data.update(api.query_category("Merchants"))

    shop_items = []
    for name, page in page_data.items():
        if name.startswith("Category:"):
            continue

        try:
            items = []
            code = mw.parse(page, skip_style_tags=True)
            store_infobox = code.filter_templates(matches=lambda t: t.name.matches("Infobox Shop"))

            if len(store_infobox) < 1:
                store_infobox = code.filter_templates(matches=lambda t: t.name.matches("Infobox NPC"))
                if len(store_infobox) < 1:
                    continue

            infobox_data: Dict[str, str] = {}
            for param in store_infobox[0].params:
                infobox_data[param.name.strip()] = param.value.strip()

            store_table_head = code.filter_templates(matches=lambda t: t.name.matches("StoreTableHead"))
            store_lines = code.filter_templates(matches=lambda t: t.name.matches("StoreLine"))
            if len(store_table_head) < 1 or len(store_lines) < 1:
                continue

            store_table_data: Dict[str, str] = {}
            for param in store_table_head[0].params:
                store_table_data[param.name.strip()] = param.value.strip()

            if "smw" in store_table_data:
                if store_table_data["smw"].lower() == "no":
                    continue

            for store_line in store_lines:
                store_line_data: Dict[str, str] = {}
                for param in store_line.params:
                    store_line_data[param.name.strip()] = param.value.strip()
                if "smw" in store_line_data:
                    if store_line_data["smw"].lower() == "no":
                        continue

                shop_item = {
                    "name": store_line_data["name"],
                    "stock": store_line_data["stock"],
                    "currency": store_table_data["currency"] if "currency" in store_table_data else "Coins"
                }
                if "sell" in store_line_data:
                    shop_item["sellPrice"] = store_line_data["sell"]
                if "buy" in store_line_data:
                    shop_item["buyPrice"] = store_line_data["buy"]
                items.append(shop_item)

            shop_info = {
                "name": name,
                "location": format_location(infobox_data["location"]) if "location" in infobox_data else "",
                "isMembers": True if ("members" in infobox_data and infobox_data["members"] == "Yes") else False,
                "items": items
            }
            if "sellmultiplier" in store_table_data:
                shop_info["sellMultiplier"] = store_table_data["sellmultiplier"]
            if "buymultiplier" in store_table_data:
                shop_info["buyMultiplier"] = store_table_data["buymultiplier"]

            shop_items.append(shop_info)

        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            print("Item {} failed:".format(name))
            traceback.print_exc()

    with open(output_dir + file_name, "w+") as fi:
        json.dump(shop_items, fi, indent=2, sort_keys=True)

    with open(output_dir + min_name, "w+") as fi:
        json.dump(shop_items, fi, separators=(",", ":"), sort_keys=True)


def get_item_spawns():
    print("Scraping item spawns")
    item_pages = api.query_category("Items")
    file_name = "items-spawns.json"
    min_name = "items-spawns.min.json"

    item_spawns = []
    for name, obj in item_pages.items():
        page = obj["page"]
        if ":" in name:
            continue

        try:
            code = mw.parse(page, skip_style_tags=True)
            raw_page_spawns = code.filter_templates(matches=lambda t: t.name.matches("ItemSpawnLine"))
            if len(raw_page_spawns) < 1:
                continue
            page_spawns = {
                "group": name,
                "spawns": []
            }
            for raw_page_spawn in raw_page_spawns:
                base: Dict[str, str] = {}
                for param in raw_page_spawn.params:
                    base[param.name.strip()] = param.value.strip()

                coords = "?"
                if "1" in base:
                    coords = ""
                    coord_list = base["1"].split(",")
                    for item in coord_list:
                        if ":" not in item:
                            coords += item + ","
                    coords = coords[:-1]

                page_spawn = {
                    "name": base["name"],
                    "location": format_location(base["location"]),
                    "isMembers": True if base["members"] == "Yes" else False,
                    "coords": coords
                }
                page_spawns["spawns"].append(page_spawn)

            item_spawns.append(page_spawns)

        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            print("Item {} failed:".format(name))
            traceback.print_exc()

    with open(output_dir + file_name, "w+") as fi:
        json.dump(item_spawns, fi, indent=2, sort_keys=True)

    with open(output_dir + min_name, "w+") as fi:
        json.dump(item_spawns, fi, separators=(",", ":"), sort_keys=True)


def get_item_info():
    print("Scraping item info")
    item_pages = api.query_category("Items")
    file_name = "items-info.json"
    min_name = "items-info.min.json"

    item_info = []
    for name, obj in item_pages.items():
        page = obj["page"]
        url = obj["url"]
        if ":" in name:
            continue

        try:
            code = mw.parse(page, skip_style_tags=True)

            versions = {}

            for (vid, version) in util.each_version("Infobox Item", code, include_base=True):
                versions[vid] = version

            for (vid, version) in versions.items():
                if len(versions) > 1 and vid == -1:
                    continue

                base: Dict[str, str] = {}
                for param, value in version.items():
                    base[param.strip()] = value.strip()

                if "hist" in base["id"] or "beta" in base["id"] or base["name"].lower() == "null":
                    continue

                item_id = int(base["id"].split(",")[0])

                obj = {
                    "name": base["name"],
                    "group": name,
                    "isMembers": True if base["members"] == "Yes" else False,
                    "isTradeable": True if base["tradeable"] == "Yes" else False,
                    "examineText": base["examine"] if "examine" in base else "",
                    "itemID": item_id,
                    "url": url
                }

                item_info.append(obj)

        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            print("Item {} failed:".format(name))
            traceback.print_exc()

    with open(output_dir + file_name, "w+") as fi:
        json.dump(item_info, fi, indent=2, sort_keys=True)

    with open(output_dir + min_name, "w+") as fi:
        json.dump(item_info, fi, separators=(",", ":"), sort_keys=True)


def get_item_drops():
    print("Scraping drops")
    file_name = "items-drop-sources.json"
    min_name = "items-drop-sources.min.json"
    temp_item_drops = api.ask_category_drop_sources("Items")

    item_drops = []
    for name, results in temp_item_drops.items():
        if len(results["results"]) < 1:
            continue

        drop_object = {
            "name": name,
            "dropSources": []
        }

        try:
            for result in results["results"]:
                result_object = {
                    "source": result["Dropped from"],
                    "quantityLow": result["Quantity Low"] if "Quantity Low" in result else -1,
                    "quantityHigh": result["Quantity High"] if "Quantity High" in result else -1,
                    "rarity": result["Rarity"] if "Rarity" in result else "Unknown",
                    "dropLevel": result["Drop level"] if "Drop level" in result else "",
                    "dropType": result["Drop type"] if "Drop type" in result else ""
                }
                drop_object["dropSources"].append(result_object)

        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            print("Item {} failed:".format(name))
            traceback.print_exc()

        item_drops.append(drop_object)

    with open(output_dir + file_name, "w+") as fi:
        json.dump(item_drops, fi, indent=2, sort_keys=True)

    with open(output_dir + min_name, "w+") as fi:
        json.dump(item_drops, fi, separators=(",", ":"), sort_keys=True)


def generate_hashes():
    print("Generating checksums")
    path = os.getcwd() + "/output"
    BLOCKSIZE = 65536
    checksums = {}
    for file_name in os.listdir(path):
        file_path = os.path.join(path, file_name)
        if os.path.isfile(file_path):
            if "min" not in file_name or file_name == "checksums":
                continue

            hasher = hashlib.sha256()
            with open(file_path, 'rb') as afile:
                buf = afile.read(BLOCKSIZE)
                while len(buf) > 0:
                    hasher.update(buf)
                    buf = afile.read(BLOCKSIZE)

            checksum = hasher.hexdigest()
            checksums[file_name] = checksum

    with open(output_dir + "checksums", "w+") as fi:
        json.dump(checksums, fi, indent=2, sort_keys=True)


def format_location(location):
    floor_values = {
        0: "ground floor",
        1: "1st floor",
        2: "2nd floor",
        3: "3rd floor",  # current highest floor
        4: "4th floor",
        5: "5th floor"
    }
    bracket_regex = r"(?<=\[\[).*?(?=\]\])"
    bracket_matches = re.finditer(bracket_regex, location, re.MULTILINE)
    for matchNum, match in enumerate(bracket_matches, start=1):
        parts = match.group().split("|")
        if len(parts) > 1:
            part = parts[1]
        else:
            part = parts[0]
        location = location.replace(match.group(), part).replace("[", "").replace("]", "")

    brace_regex = r"(\{\{).*?(\d+)(\}\})"
    brace_matches = re.finditer(brace_regex, location, re.MULTILINE)
    for matchNum, match in enumerate(brace_matches, start=1):
        floor = int(match.group(2))
        location = location.replace(match.group(), floor_values.get(floor))

    return location


def run():
    print("running")
    get_production()
    get_item_spawns()
    get_shop_items()
    get_item_info()
    get_item_drops()
    generate_hashes()
