from __future__ import print_function

import datetime
import os.path
from typing import List, Any, Dict

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar']

# Define the default paths for the token and the credentials
DEFAULT_PATH_TOKEN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "token.json")
DEFAULT_PATH_CREDENTIALS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "credentials.json")


class Querier:
    """
    Class to query the calendar.
    """

    def __init__(self,
                 token_path: str = DEFAULT_PATH_TOKEN,
                 credentials_path: str = DEFAULT_PATH_CREDENTIALS):
        """
        Initialize the querier.

        Args:
            token_path (str): The path to the token file.
            credentials_path (str): The path to the credentials file.

        """

        self.token_path = token_path
        self.credentials_path = credentials_path

        self.creds = self._credentials()

    def _credentials(self) -> Credentials:
        creds = None
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())
        return creds

    def get_next_events(self, days: int = 10) -> List[Dict]:
        """
        Get the events in the next 10 days in the calendar
        :return:
        """
        assert days > 0, "Days must be greater than 0"
        service = build('calendar', 'v3', credentials=self.creds)
        # Call the Calendar API
        now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
        ten_days_from_now = (datetime.datetime.now() + datetime.timedelta(days=days)).isoformat() + 'Z'
        print('Getting events in the next 10 days')
        events_result = service.events().list(calendarId='primary', timeMin=now,
                                              timeMax=ten_days_from_now, singleEvents=True,
                                              orderBy='startTime').execute()
        events = events_result.get('items', [])

        if not events:
            print('No events found in the next 10 days.')
            return []

        # Prints the start and name of all events in the next 10 days
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            print(start, event['summary'])

        return events

    def set_event(self,
                  summary: str,
                  description: str,
                  start: datetime.datetime,
                  end: datetime.datetime,
                  type: int = 0):
        """
        Set an event in the calendar
        Args:
            summary (str): The summary of the event
            description (str): The description of the event
            start (datetime.datetime): The start time of the event
            end (datetime.datetime): The end time of the event
        """

        service = build('calendar', 'v3', credentials=self.creds)

        start = start.strftime("%Y-%m-%dT%H:%M:%S")
        end = end.strftime("%Y-%m-%dT%H:%M:%S")
        # Create the event
        event = {
            'summary': summary,
            'description': description,
            'start': {
                'dateTime': start,
                'timeZone': 'Europe/Stockholm'
            },
            'end': {
                'dateTime': end,
                'timeZone': 'Europe/Stockholm'
            },
            'colorId': '9'
        }

        # Add the event to the calendar
        event = service.events().insert(calendarId='primary', body=event).execute()
        print(f'Event created: {event.get("htmlLink")}')

    def delete_events(self):
        """
        Deletes the events set by the calendar before.

        """
        events = self.get_next_events()

        service = build('calendar', 'v3', credentials=self.creds)

        for event in events:
            if event.get('colorId', '-1') == '9':
                service.events().delete(calendarId='primary', eventId=event['id']).execute()


def main():
    querier = Querier()
    events = querier.get_next_events()


if __name__ == '__main__':
    main()
