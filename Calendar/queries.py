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
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']



class Querier:
    def __init__(self,
                 token_path: str = "token.json",
                 credentials_path: str = "credentials.json"):

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

def main():
    querier = Querier()
    querier.get_next_events()


if __name__ == '__main__':
    main()