import json
import collections
import re
from typing import *

VERSION_EXTRACTOR = re.compile(r"(.*?)([0-9]+)?$")


def each_version(template_name: str, code, include_base: bool = False,
                 mergable_keys: List[str] = None) -> Iterator[Tuple[int, dict[str, any]]]:
    """
    each_version is a generator that yields each version of an infobox
    with variants, such as {{Infobox Item}} on [[Ring of charos]]
    """
    if mergable_keys is None:
        mergable_keys = ["version", "image", "caption"]
    infoboxes = code.filter_templates(matches=lambda t: t.name.matches(template_name))
    if len(infoboxes) < 1:
        return
    for infobox in infoboxes:
        base: dict[str, str] = {}
        versions: dict[int, dict[str, str]] = {}
        for param in infobox.params:
            matcher = VERSION_EXTRACTOR.match(str(param.name).strip())
            if matcher is None:
                raise AssertionError()
            primary = matcher.group(1)
            dic = base
            if matcher.group(2) is not None:
                version = int(matcher.group(2))
                if not version in versions:
                    versions[version] = {}
                dic = versions[version]
            dic[primary] = param.value
        if len(versions) == 0:
            yield (-1, base)
        else:
            all_mergable = True
            for version_id, versionDict in versions.items():
                for key in versionDict:
                    if not key in mergable_keys:
                        all_mergable = False
            if all_mergable:
                yield (-1, base)
            else:
                if include_base:
                    yield (-1, base)
                for version_id, versionDict in versions.items():
                    yield (version_id, {**base, **versionDict})


def write_json(name: str, min_name: str, docs: dict[any, dict[str, any]]):
    items = []
    for (id, doc) in docs.items():
        named = {k: v for (k, v) in doc.items() if not k.startswith("__")}
        nameless = named.copy()
        if "name" in nameless:
            del nameless["name"]
        if nameless != {}:
            items.append((id, named, nameless))
    items.sort(key=lambda k: int(k[0]))

    with_names = collections.OrderedDict([(k, v) for (k, v, _) in items])
    with open(name, "w+") as fi:
        json.dump(with_names, fi, indent=2)

    without_names = collections.OrderedDict([(k, v) for (k, _, v) in items])
    with open(min_name, "w+") as fi:
        json.dump(without_names, fi, separators=(",", ":"))


def get_doc_for_id_string(source: str, version: dict[str, str], docs: dict[str, dict],
                          allow_duplicates: bool = False) -> Optional[dict]:
    if not "id" in version:
        print("page {} is missing an id".format(source))
        return None

    ids = [id for id in map(lambda id: id.strip(), str(version["id"]).split(",")) if id != "" and id.isdigit()]

    if len(ids) == 0:
        print("page {} is has an empty id".format(source))
        return None

    doc = {}
    doc["__source__"] = source
    invalid = False
    for id in ids:
        if not allow_duplicates and id in docs:
            print("page {} is has the same id as {}".format(source, docs[id]["__source__"]))
            invalid = True
        docs[id] = doc

    if invalid:
        return None
    return doc


def copy(name: Union[str, Tuple[str, str]],
         doc: dict,
         version: dict[str, any],
         convert: Callable[[any], any] = lambda x: x) -> bool:
    src_name = name if isinstance(name, str) else name[0]
    dst_name = name if isinstance(name, str) else name[1]
    if not src_name in version:
        return False
    strval = str(version[src_name]).strip()
    if strval == "":
        return False
    newval = convert(strval)
    if not newval:
        return False
    doc[dst_name] = newval
    return True


def has_template(name: str, code) -> bool:
    return len(code.filter_templates(matches=lambda t: t.name.matches(name))) != 0
