#!/usr/bin/env python3
"""Builds pokemon.json (all species + Mega/regional/Primal forms) and downloads sprites.
Stdlib only, runs in Termux.  Usage: python build_data.py [--no-sprites]"""
import json, os, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor

API = "https://pokeapi.co/api/v2/"
SPR = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/%d.png"
UA = {"User-Agent": "Mozilla/5.0 pokedle-builder"}
GEN = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7, "viii": 8, "ix": 9}
FORMS = {"mega": "Mega", "primal": "Primal", "alola": "Alolan",
         "galar": "Galarian", "hisui": "Hisuian", "paldea": "Paldean"}
chains = {}

def fetch(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30)

def get(url):
    err = None
    for _ in range(3):
        try:
            with fetch(url) as r:
                return json.load(r)
        except Exception as e:
            err = e
    raise RuntimeError("failed: %s (%s)" % (url, err))

def depth(node, name, d=1):
    if node["species"]["name"] == name:
        return d
    for n in node["evolves_to"]:
        r = depth(n, name, d + 1)
        if r:
            return r
    return 0

def maxdepth(node, d=1):
    return max([maxdepth(n, d + 1) for n in node["evolves_to"]] or [d])

def has_split(node):
    return len(node["evolves_to"]) > 1 or any(has_split(n) for n in node["evolves_to"])

def entry(p, s, name, form):
    cu = s["evolution_chain"]["url"]
    if cu not in chains:
        chains[cu] = get(cu)["chain"]
    ch = chains[cu]
    types = [t["type"]["name"] for t in sorted(p["types"], key=lambda t: t["slot"])]
    return {
        "id": p["id"], "name": name, "form": form,
        "t1": types[0], "t2": types[1] if len(types) > 1 else "",
        "gen": GEN[s["generation"]["name"].split("-")[1]],
        "stage": depth(ch, s["name"]), "evos": maxdepth(ch), "split": has_split(ch),
        "color": s["color"]["name"],
        "h": p["height"] / 10, "w": p["weight"] / 10,
    }

def build(i):
    p = get(f"{API}pokemon/{i}")
    s = get(p["species"]["url"])
    base = s["name"].replace("-", " ").title()
    out = [entry(p, s, base, "Base")]
    for v in s["varieties"]:
        if v["is_default"]:
            continue
        tail = v["pokemon"]["name"][len(s["name"]) + 1:].split("-")
        if tail[0] not in FORMS:
            continue
        form = FORMS[tail[0]]
        rest = " ".join(t.upper() if len(t) == 1 else t.title() for t in tail[1:])
        name = (form + " " + base + (" " + rest if rest else "")).strip()
        out.append(entry(get(v["pokemon"]["url"]), s, name, form))
    return out

def sprite(i):
    path = "sprites/%d.png" % i
    if os.path.exists(path):
        return
    try:
        with fetch(SPR % i) as r:
            open(path, "wb").write(r.read())
    except Exception:
        pass  # some forms have no sprite; the game hides missing images

if __name__ == "__main__":
    count = get(API + "pokemon-species?limit=1")["count"]
    print("species:", count, "- building, this takes a few minutes")
    with ThreadPoolExecutor(8) as ex:
        dex = [e for group in ex.map(build, range(1, count + 1)) for e in group]
    json.dump(dex, open("pokemon.json", "w"), separators=(",", ":"))
    print("wrote pokemon.json:", len(dex), "entries")
    if "--no-sprites" not in sys.argv:
        os.makedirs("sprites", exist_ok=True)
        with ThreadPoolExecutor(8) as ex:
            list(ex.map(sprite, [d["id"] for d in dex]))
        print("sprites done")
