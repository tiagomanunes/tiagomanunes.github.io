"""Fetching data from HTB API, writing to JSON."""

import asyncio
import os
import json
from datetime import datetime
import sys
import aiohttp


BASE_URL = "https://labs.hackthebox.com/api/v4/"
USER_NAME = "facsimilae"
USER_ID = 2103519
API_TOKEN = os.getenv("HTB_API_TOKEN")
CURRENT_PROLAB = "Dante"

ENDPOINTS = {
    "profile": (
        f"user/profile/basic/{USER_ID}",
        lambda d: {
            "rank_label": d["profile"]["rank"],
            "rank_global": d["profile"]["ranking"],
            "owns_user": d["profile"]["user_owns"],
            "owns_root": d["profile"]["system_owns"]
        }
    ),
    "prolab": (
        f"user/profile/progress/prolab/{USER_ID}",
        lambda d: next(({
            "owned_flags": x["owned_flags"],
            "total_flags": x["total_flags"]
        } for x in d["profile"]["prolabs"] if x["name"] == CURRENT_PROLAB))
    ),
    "best": (
        "rankings/user/best?period=1Y",
        lambda d: {
            "best_rank": d["data"]["rank"],
            "best_date": d["data"]["date"]
        }
    ),
    "country": (
        "rankings/country/ch/members",
        lambda d: next((
            x["rank"] for x in d["data"]["rankings"] if x["name"] == USER_NAME),
            "Not ranked currently!")
    )
}

SUFFIXES = {1: 'st', 2: 'nd', 3: 'rd'}
def make_ordinal(i: str) -> str:
    """ From https://codereview.stackexchange.com/questions/41298/producing-ordinal-numbers """
    if 10 <= int(i) % 100 <= 20:
        return i + 'th'
    return i + SUFFIXES.get(int(i) % 10, 'th')


class APIError(Exception):
    """Explicit exception."""


async def fetch(session, endpoint):
    """ Fetches data and raises an exception if the request fails. """
    url = f"{BASE_URL}{endpoint}"
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {API_TOKEN}"
    }

    try:
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                raise APIError(f"Failed to fetch {url}: {response.status}")
            return await response.json()
    except Exception as e:
        raise APIError(f"Request to {url} failed: {str(e)}") from e

async def get_data():
    """ Fetch all endpoints asynchronously and process their data. """
    async with aiohttp.ClientSession() as session:
        tasks = {name: fetch(session, endpoint) for name, (endpoint, _) in ENDPOINTS.items()}

        try:
            results = await asyncio.gather(*tasks.values())
            return {name: ENDPOINTS[name][1](data) for name, data in zip(tasks.keys(), results)}
        except APIError as e:
            print(f"API request failed: {e}")
            return None

data = asyncio.run(get_data())

if data is not None:
    stats = {
        "rank_label": data["profile"]["rank_label"],
        "rank_global": make_ordinal(data["profile"]["rank_global"]),
        "owns_user": data["profile"]["owns_user"],
        "owns_root": data["profile"]["owns_root"],
        "best_rank": make_ordinal(data["best"]["best_rank"]),
        "best_date": data["best"]["best_date"],
        "rank_country": make_ordinal(data["country"]),
        "current_prolab": CURRENT_PROLAB,
        "prolab_owned_flags": data["prolab"]["owned_flags"],
        "prolab_total_flags": data["prolab"]["total_flags"],
        "last_updated": datetime.today().strftime('%Y-%m-%d')
    }

    print(stats)

    with open("htb_data.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=4)

    print("HTB data successfully fetched and saved!")
else:
    sys.exit(1)
