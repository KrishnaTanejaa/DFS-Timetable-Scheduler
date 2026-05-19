# DFS Timetable Scheduler

A web-based timetable generation tool built with Python and Flask. This application uses a Depth-First Search (DFS) algorithm with backtracking to automatically schedule subjects into a weekly school timetable. 

## Features

* **Automated Scheduling**: Automatically assigns subjects to a 5-day week (Monday to Friday) across 8 available daily periods.
* **Double Period Support**: Automatically schedules back-to-back double periods for subjects when requested.
* **Fixed/Predefined Slots**: Allows users to manually lock specific subjects into exact days and times.
* **Constraint Satisfaction**: Ensures no overlapping classes and accurately skips over the predefined "Lunch Break".
* **Interactive UI**: A simple and intuitive web interface for inputting subjects, weekly occurrences, and constraints.

## Technologies Used

* **Backend**: Python 3, Flask
* **Algorithm**: Depth-First Search (DFS) with backtracking for constraint satisfaction
* **Frontend**: HTML (Jinja2 Templates)

## Prerequisites

Make sure you have Python 3.x installed on your system.

## Installation & Setup

1. **Navigate** to the project directory:
   ```bash
   cd dfs-scheduler-project
   ```
2. **(Optional) Create a virtual environment**:
   ```bash
   python -m venv venv
   # On Windows use:
   venv\Scripts\activate
   # On macOS/Linux use:
   source venv/bin/activate
   ```
3. **Install dependencies**:
   ```bash
   pip install flask
   ```
4. **Run the application**:
   ```bash
   python app.py
   ```
5. **Open your browser** and go to `http://127.0.0.1:5000/`.

## Usage

1. Enter the name of the subjects in the provided fields.
2. Specify the number of "Classes per Week" for each subject.
3. If you want a subject to take place at a specific time, check the "Predefined" box and select the day and time slots.
4. Click **Generate Timetable**. The DFS algorithm will attempt to find a valid schedule that satisfies all conditions.
5. The generated timetable will be displayed below the form, showing subject periods and free periods.
