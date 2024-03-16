from datetime import datetime, timedelta
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar"]


def get_calendar_service():
    """Log in to the Google Calendar API and return the service object."""
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("donnaClient.json", SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    service = build("calendar", "v3", credentials=creds)
    return service


def main():
    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("donnaClient.json", SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        service = build("calendar", "v3", credentials=creds)

        # Call the Calendar API

        start_of_day = datetime.now()
        end_of_day = start_of_day + timedelta(days=1)
        print("Getting the upcoming 10 events")
        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=start_of_day.isoformat() + "Z",
                timeMax=end_of_day.isoformat() + "Z",
                maxResults=10,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = events_result.get("items", [])

        if not events:
            print("No upcoming events found.")
            return

        # Prints the start and name of the next 10 events
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            print(start, event["summary"])

    except HttpError as error:
        print(f"An error occurred: {error}")


# def get_event(event_id):
#     """Retrieve an event by its ID from the user's primary calendar."""
#     try:
#         service = get_calendar_service()
#         event = service.events().get(calendarId="primary", eventId=event_id).execute()
#         print("Event found: %s" % (event.get("summary")))
#         return event
#     except HttpError as error:
#         print(f"An error occurred: {error}")
#         page_token = None
#         return None


def set_event(event_details):
    """Creates a new event with the given details."""
    try:
        service = get_calendar_service()
        event = (
            service.events().insert(calendarId="primary", body=event_details).execute()
        )
        print("Event created: %s" % (event.get("htmlLink")))
    except HttpError as error:
        print(f"An error occurred: {error}")


def get_events():
    """Retrieve the upcoming events of the current day from the user's primary calendar."""
    service = get_calendar_service()
    start_of_day = datetime.now()
    end_of_day = start_of_day + timedelta(days=1)
    print("Getting today's events...")
    events_result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=start_of_day.isoformat() + "Z",
            timeMax=end_of_day.isoformat() + "Z",
            maxResults=10,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    events = events_result.get("items", [])

    if not events:
        print("No upcoming events found.")
        return

    # Prints the start and name of today's events
    for event in events:
        start = event["start"].get("dateTime", event["start"].get("date"))
        print(start, event["summary"])


def get_availability(date):
    """Check availability for a specific date and print free times."""
    try:
        # Define the whole day range
        service = get_calendar_service()
        datetime_format = "%Y-%m-%d"
        start_of_day = datetime.strptime(date, datetime_format)
        end_of_day = start_of_day + timedelta(days=1)

        # Prepare the request body for free/busy query
        body = {
            "timeMin": start_of_day.isoformat() + "Z",
            "timeMax": end_of_day.isoformat() + "Z",
            "items": [{"id": "primary"}],
        }

        # Query the free/busy info
        free_busy_result = service.freebusy().query(body=body).execute()
        busy_periods = free_busy_result.get("calendars").get("primary").get("busy")

        # Calculate and print the free times
        free_periods = calculate_free_periods(start_of_day, end_of_day, busy_periods)

        if not free_periods:
            print("Looks like the day is fully booked!")
        else:
            print("Free times:")
            for period in free_periods:
                print(f"{period[0]} to {period[1]}")
    except HttpError as error:
        print(f"An error occurred: {error}")


def calculate_free_periods(start_of_day, end_of_day, busy_periods):
    """Calculate free periods given the day's range and busy periods."""
    free_periods = []
    current_start = start_of_day

    for busy in busy_periods:
        busy_start = datetime.fromisoformat(busy["start"].rstrip("Z"))
        busy_end = datetime.fromisoformat(busy["end"].rstrip("Z"))

        # If the current start is before the busy period starts, we have a free period
        if current_start < busy_start:
            formatted_date = current_start.strftime("%B %d, %Y")
            formatted_time = current_start.strftime("%I:%M:%S %p")
            currStart = " ".join([formatted_date, formatted_time])
            formatted_dateB = busy_start.strftime("%B %d, %Y")
            formatted_timeB = busy_start.strftime("%I:%M:%S %p")
            busyStart = " ".join([formatted_dateB, formatted_timeB])
            free_periods.append((currStart, busyStart))
        current_start = max(current_start, busy_end)

    # Check for free time at the end of the day
    if current_start < end_of_day:
        formatted_date = current_start.strftime("%B %d, %Y")
        formatted_time = current_start.strftime("%I:%M:%S %p")
        currStart = " ".join([formatted_date, formatted_time])
        formatted_dateB = end_of_day.strftime("%B %d, %Y")
        formatted_timeB = end_of_day.strftime("%I:%M:%S %p")
        end = " ".join([formatted_dateB, formatted_timeB])
        free_periods.append((currStart, end))

    return free_periods


if __name__ == "__main__":
    # get_events()
    # set_event(
    #     {
    #         "summary": "Test event",
    #         "location": "Test location",
    #         "description": "Test description",
    #         "start": {
    #             "dateTime": "2024-03-16T09:00:00",
    #             "timeZone": "Europe/Bucharest",
    #         },
    #         "end": {"dateTime": "2024-03-16T17:00:00", "timeZone": "Europe/Bucharest"},
    #     }
    # )
    get_availability("2024-3-16")
