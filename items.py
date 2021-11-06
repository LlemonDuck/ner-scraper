import json
import traceback
from typing import Dict

import api
import mwparserfromhell as mw

import util

output_dir = "output/"


def get_production():
    item_production = api.ask_category_production("Items")
    name = "items-production.json"
    min_name = "items-production.min.json"

    with open(output_dir + name, "w+") as fi:
        json.dump(item_production, fi, indent=2)

    with open(output_dir + min_name, "w+") as fi:
        json.dump(item_production, fi, separators=(",", ":"))


def get_shop_items():
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
                "location": infobox_data["location"].replace("[", "").replace("]",
                                                                              "") if "location" in infobox_data else "",
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
    item_pages = api.query_category("Items")
    file_name = "items-spawns.json"
    min_name = "items-spawns.min.json"

    item_spawns = []
    for name, page in item_pages.items():
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
                    "location": base["location"].replace("[", "").replace("]", ""),
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
    item_pages = api.query_category("Items")
    file_name = "items-info.json"
    min_name = "items-info.min.json"

    item_info = []
    for name, page in item_pages.items():
        if ":" in name:
            continue

        # if name != "Absorption":
        #     continue

        try:
            code = mw.parse(page, skip_style_tags=True)

            for (vid, version) in util.each_version("Infobox Item", code, include_base=True):
                if vid == -1:
                    continue

                base: Dict[str, str] = {}
                for param, value in version.items():
                    base[param.strip()] = value.strip()

                if "removal" in base:
                    continue

                item_id = int(base["id"].split(",")[0])

                obj = {
                    "name": base["name"],
                    "group": name,
                    "isMembers": True if base["members"] == "Yes" else False,
                    "isTradeable": True if base["tradeable"] == "Yes" else False,
                    "examineText": base["examine"],
                    "itemID": item_id
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


def run():
    get_production()
    get_item_spawns()
    get_shop_items()
    get_item_info()
