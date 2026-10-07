"""Create fictional demo records; no original respondent data is used."""
from pathlib import Path
import csv
root = Path(__file__).resolve().parents[1]
path = root / "RawData" / "demo_workshop.csv"
path.parent.mkdir(exist_ok=True)
with path.open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow(["FullName(AR)", "FullName(En)", "Email", "Phone", "Major", "Univeristy", "Academic lvl", "TimeStamp"])
    names = ["Amber Birch", "Cobalt Cedar", "Coral Elm", "Indigo Fern", "Ivory Maple", "Jade Moss", "Lilac Oak", "Onyx Pine", "Pearl Reed", "Ruby Spruce", "Silver Willow", "Topaz Yew"]
    for i in range(1, 13):
        writer.writerow(["", names[i-1], f"participant{i}@example.com", "", "Data Science", "University of Jeddah", "4", "2026-09-01 10:00:00"])
    writer.writerow(["", "", "", "", "Data Science", "University of Jeddah", "4", "2026-09-01 10:00:00"])
print("Created fictional demo: RawData/demo_workshop.csv")
