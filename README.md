# Organizer

Organizer is a simple tool to organize your schedule in an automatic way and sets the changes in your Google Calendar.
It is possible to set a list of tasks to do , with their respective estimated time and priority and the *organizer* will 
fit them based on your preferences and create the events in your Google Calendar.

Basically it is like having a personal Assistant

## Calendar
This module contains the classes to interact with the Google Calendar API. It is possible to create events and to query them.

## Interface
This module defines a Stream interface to interact with the user. It is possible to define new tasks. Each task has;

1. A name
2. A priority
3. An estimated time
4. A category
5. A due date

It is also possible to define the slots in which the tasks can be done. Each slot has:

1. A start time
2. An end time

The tasks are assigned to the slots based on the priority and the estimated time. The events already set on calendar are
respected to not have any overlap with them. Regarding the slots the bounds can be chosen to be soft so that tasks can go 
*a bit* out of bounds if necessary.

It is possible to customize how much weight we give to complete tasks by priority.

## Installation
The used libraries for running the code are in the requirements.txt file. To install them run the following command:

```commandline
pip install -r requirements.txt
```

## Launching

### Interface
For launching the interface it is enough to run, using the virtual environment, the following command:

```commandline
cd Interface
streamlit run app.py
```

It will open in your browser the app for setting the schedule and the tasks.
### Organizer

For launching the organizer you can run the following command:

```commandline
python main.py 
```

It will automatically read the tasks in the database and the schedules, solve the organization task and set them in your
google calendar.

The first time it is run it is necessary to configure the Google Calendar API by saving your ```credentials.json``` file 
in the ```Calendar``` folder. It will be used to create the events in your calendar and to read from it.
It might be also necessary that you set up a google cloud project and enable the Google Calendar API. Check more information
[here](https://developers.google.com/calendar/api/quickstart/python)




## Todo

1. Add full support for Google Calendar. Use the API to create events
2. Add constraint for maximum due date
3. Create the interface for having events from several categories
3. Use ML models