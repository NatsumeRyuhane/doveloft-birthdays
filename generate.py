import requests
from ics import Calendar, Event
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import pytz

# Load environment variables from .env file (only in local development)
if os.path.exists('.env'):
    load_dotenv()

# Set up timezone
UTC8 = pytz.timezone('Asia/Shanghai')  # UTC+8 timezone

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

def get_week_start(date: datetime) -> datetime:
    """Get the start of the calendar week (Monday) for a given date."""
    # Calculate days since Monday (0=Monday, 6=Sunday)
    days_since_monday = date.weekday()
    week_start = date - timedelta(days=days_since_monday)
    return week_start.replace(hour=0, minute=0, second=0, microsecond=0)

def should_include_birthday(birth_date: datetime, upcoming: datetime, reference: datetime) -> bool:
    """
    Determine if a birthday should be included in the calendar.
    Include upcoming birthdays and passed birthdays within the current calendar week.
    """
    # Get the start of this week
    week_start = get_week_start(reference)
    
    # Include if upcoming birthday is in the future
    if upcoming >= reference:
        return True
    
    # Include if the birthday was this week (even if it passed)
    birthday_this_year = generate_birthday_this_year(birth_date, datetime(reference.year, 1, 1))
    if birthday_this_year >= week_start and birthday_this_year < reference:
        return True
    
    return False

def create_ics_file(birthdays, output_file="birthdays.ics"):
    c = Calendar()
    # Get current time in UTC+8 and convert to naive datetime for calculations
    now_utc8 = datetime.now(UTC8)
    today = now_utc8.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
    
    # Calculate exactly one year from today, accounting for leap years
    next_year_today = datetime(today.year + 1, today.month, today.day)

    for name, birthday_str, qq, age_hide in birthdays:
        birth_date = datetime.fromisoformat(birthday_str)
        upcoming = generate_birthday_this_year(birth_date, today)
        
        # Check if we should include this birthday
        if should_include_birthday(birth_date, upcoming, today):
            # For passed birthdays in this week, use the birthday from this year
            if upcoming > today:
                # Future birthday - use the upcoming date
                birthday_to_use = upcoming
            else:
                # Past birthday this week - use this year's birthday
                birthday_to_use = generate_birthday_this_year(birth_date, datetime(today.year, 1, 1))
            
            age = birthday_to_use.year - birth_date.year
            e = Event()
            if not age_hide:
                e.name = f"{name}的{age}岁生日"
            else:
                e.name = f"{name}的生日"
            e.begin = birthday_to_use  # Use datetime object directly
            e.make_all_day()
            if qq:
                e.description = f"QQ: {qq}"
            c.events.add(e)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(c.serialize())  # Use serialize() method instead of str()
    print(f"✅ Generated `{output_file}` with {len(c.events)} birthday(s) (UTC+8 timezone)")

if __name__ == "__main__":
    birthdays = fetch_birthdays()
    create_ics_file(birthdays)
