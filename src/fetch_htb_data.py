import json

stats = {
    "rank": "Script Kiddie",
    "world_rank": 870,
    "country_rank": "Unranked currently!",
    "best_rank": 793,
    "owned_user": 6,
    "owned_root": 6,
    "prolab": "Dante",
    "prolab_progress": 0,
    "last_updated": "2025-03-18"
}

# Save to JSON file
with open("htb_data.json", "w") as f:
    json.dump(stats, f, indent=4)

print("HTB data successfully fetched and saved!")
