import requests
from ics import Calendar, Event
from datetime import datetime, timedelta
import os

# Set up Notion API
NOTION_TOKEN = os.getenv("NOTION_TOKEN", "")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "")

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

def fetch_birthdays():
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    response = requests.post(url, headers=HEADERS)

    if response.status_code != 200:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
        return []

    data = response.json()
    results = data.get("results", [])
    birthdays = []

    for item in results:
        props = item["properties"]

        # Extract name
        name = "(unknown)"
        if "姓名" in props and props["姓名"]["title"]:
            name = props["姓名"]["title"][0]["plain_text"]

        # Extract birthday date
        birthday_str = props.get("生日", {}).get("date", {}).get("start", "")
        if not birthday_str:
            continue

        # Extract QQ
        qq = props.get("QQ号码", {}).get("number", "")
        birthdays.append((name, birthday_str, qq))

    return birthdays

def generate_birthday_this_year(birth_date: datetime, reference: datetime) -> datetime:
    """Generate the birthday date this year or next if it's already passed."""
    try:
        birthday_this_year = birth_date.replace(year=reference.year)
    except ValueError:
        birthday_this_year = birth_date.replace(year=reference.year, day=28)  # Feb 29 fix

    if birthday_this_year < reference:
        try:
            return birth_date.replace(year=reference.year + 1)
        except ValueError:
            return birth_date.replace(year=reference.year + 1, day=28)
    return birthday_this_year

def create_ics_file(birthdays, output_file="birthdays.ics"):
    c = Calendar()
    today = datetime.today()
    next_year = today + timedelta(days=365)

    for name, birthday_str, qq in birthdays:
        birth_date = datetime.fromisoformat(birthday_str)
        upcoming = generate_birthday_this_year(birth_date, today)

        if today <= upcoming <= next_year:
            age = upcoming.year - birth_date.year
            e = Event()
            e.name = f"{name} 的 {age} 岁生日"
            e.begin = upcoming.strftime("%Y-%m-%d")
            e.make_all_day()
            if qq:
                e.description = f"QQ: {qq}"
                e.extra.append(("COMMENT", f"QQ ID: {qq}"))
            c.events.add(e)

    with open(output_file, "w", encoding="utf-8") as f:
        f.writelines(c)
    print(f"✅ Generated `{output_file}` with {len(c.events)} upcoming birthday(s)")

if __name__ == "__main__":
    birthdays = fetch_birthdays()
    create_ics_file(birthdays)
