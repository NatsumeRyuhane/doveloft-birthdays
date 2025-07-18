import requests
from ics import Calendar, Event
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Load environment variables from .env file (only in local development)
if os.path.exists('.env'):
    load_dotenv()

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
        name = ""
        if "昵称" in props and props["昵称"]["title"]:
            name = props["昵称"]["title"][0]["plain_text"]

        # if the name cannot be extracted, assume the data is malformed
        # and jump to the next item
        if not name:
            continue
        
        # Extract birthday date
        birthday_str = props.get("生日", {}).get("date", {}).get("start", "")
        if not birthday_str:
            continue

        # Extract QQ
        qq = props.get("QQ号码", {}).get("number", "")
        
        # Extract age display option
        age_hide = props.get("隐藏年龄", {}).get("checkbox", True)

        birthdays.append((name, birthday_str, qq, age_hide))

    return birthdays

def generate_birthday_this_year(birth_date: datetime, reference: datetime) -> datetime:
    """Generate the birthday date this year or next if it's already passed."""
    def get_birthday_for_year(year: int) -> datetime:
        """Get birthday for a specific year, handling leap year edge cases."""
        try:
            return birth_date.replace(year=year)
        except ValueError:
            # This happens when birth_date is Feb 29 and target year is not a leap year
            # In non-leap years, celebrate Feb 29 birthdays on Feb 28
            return birth_date.replace(year=year, day=28)
    
    birthday_this_year = get_birthday_for_year(reference.year)
    
    # If birthday already passed this year, get next year's birthday
    if birthday_this_year < reference:
        return get_birthday_for_year(reference.year + 1)
    return birthday_this_year

def create_ics_file(birthdays, output_file="birthdays.ics"):
    c = Calendar()
    today = datetime.today()
    # Calculate exactly one year from today, accounting for leap years
    next_year_today = datetime(today.year + 1, today.month, today.day)

    for name, birthday_str, qq, age_hide in birthdays:
        birth_date = datetime.fromisoformat(birthday_str)
        upcoming = generate_birthday_this_year(birth_date, today)

        # Include today but exclude the same date next year
        if today <= upcoming < next_year_today:
            age = upcoming.year - birth_date.year
            e = Event()
            if not age_hide:
                e.name = f"{name}的{age}岁生日"
            else:
                e.name = f"{name}的生日"
            e.begin = upcoming  # Use datetime object directly
            e.make_all_day()
            if qq:
                e.description = f"QQ: {qq}"
                # Remove the problematic extra.append line
            c.events.add(e)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(c.serialize())  # Use serialize() method instead of str()
    print(f"✅ Generated `{output_file}` with {len(c.events)} upcoming birthday(s)")

if __name__ == "__main__":
    birthdays = fetch_birthdays()
    create_ics_file(birthdays)
