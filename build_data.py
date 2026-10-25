#!/usr/bin/env python3
"""Builds pokemon.json (full dex) and downloads sprites. Stdlib only, runs in Termux.
Usage: python build_data.py [--no-sprites]"""
import json, os, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor

API = "https://pokeapi.co/api/v2/"
SPR = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/%d.png"
GEN = {"i":1,"ii":2,"iii":3,"iv":4,"v":5,"vi":6,"vii":7,"viii":8,"ix":9}
chains = {}

def get(url):
    for _ in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 pokedle-builder'}), timeout=30) as r:
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

def build(i):
    p = get(f"{API}pokemon/{i}")
    s = get(p["species"]["url"])
    cu = s["evolution_chain"]["url"]
    if cu not in chains:
        chains[cu] = get(cu)["chain"]
    types = [t["type"]["name"] for t in sorted(p["types"], key=lambda t: t["slot"])]
    return {
        "id": i,
        "name": s["name"].replace("-", " ").title(),
        "t1": types[0], "t2": types[1] if len(types) > 1 else "",
        "gen": GEN[s["generation"]["name"].split("-")[1]],
        "stage": depth(chains[cu], s["name"]),
        "h": p["height"] / 10, "w": p["weight"] / 10,
        "bst": sum(st["base_stat"] for st in p["stats"]),
    }

def sprite(i):
    path = f"sprites/{i}.png"
    if not os.path.exists(path):
        open(path, 'wb').write(urllib.request.urlopen(urllib.request.Request(SPR % i, headers={'User-Agent': 'Mozilla/5.0 pokedle-builder'}), timeout=30).read())

if __name__ == "__main__":
    count = get(API + "pokemon-species?limit=1")["count"]
    print("species:", count)
    with ThreadPoolExecutor(8) as ex:
        dex = list(ex.map(build, range(1, count + 1)))
    json.dump(dex, open("pokemon.json", "w"), separators=(",", ":"))
    print("wrote pokemon.json")
    if "--no-sprites" not in sys.argv:
        os.makedirs("sprites", exist_ok=True)
        with ThreadPoolExecutor(8) as ex:
            list(ex.map(sprite, [d["id"] for d in dex]))
        print("sprites done")
