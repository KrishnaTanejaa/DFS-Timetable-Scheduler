import random
from flask import Flask, render_template, request

app = Flask(__name__)

# ------------------------------------------------------------------------
# CONSTANTS (synchronized with your index.html)
# ------------------------------------------------------------------------
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
DISPLAY_TIMES = ["8:45", "9:45", "10:45", "11:45", "Lunch Break", "1:00", "2:00", "3:00", "4:00"]
BREAK_TIME = "Lunch Break"
SOLVER_TIMES = [t for t in DISPLAY_TIMES if t != BREAK_TIME]

MAX_SUBJECTS = 10
MIN_SUBJECT_ROWS = 4

TOTAL_AVAILABLE_SLOTS = len(DAYS) * len(SOLVER_TIMES)  # 5 * 8 = 40

# ------------------------------------------------------------------------
# Helper (double-period adjacency)
# ------------------------------------------------------------------------
def get_time_index(time_str):
    try:
        return SOLVER_TIMES.index(time_str)
    except ValueError:
        return -1

def get_next_time_slot(time_str):
    """
    Return the immediate next solver time (string) that is adjacent to time_str,
    correctly skipping the break (Lunch Break). Returns None if none.
    """
    idx = get_time_index(time_str)
    if idx == -1 or idx >= len(SOLVER_TIMES) - 1:
        return None

    # Find the display index for time_str (so we can detect the break gap)
    display_index = -1
    for i, t in enumerate(DISPLAY_TIMES):
        if t == time_str:
            display_index = i
            break
    if display_index == -1:
        return None

    # Walk forward to find the next non-break display-time and check adjacency in SOLVER_TIMES
    for next_di in range(display_index + 1, len(DISPLAY_TIMES)):
        next_disp = DISPLAY_TIMES[next_di]
        if next_disp == BREAK_TIME:
            continue
        # if this next non-break display-time corresponds to the immediate next solver slot, accept it
        if (idx + 1) < len(SOLVER_TIMES) and SOLVER_TIMES[idx + 1] == next_disp:
            return next_disp
        else:
            return None
    return None

def generate_all_single_slots():
    slots = []
    for day in DAYS:
        for t in SOLVER_TIMES:
            slots.append({'day': day, 'time': t})
    return slots

def generate_all_double_slots():
    doubles = []
    for day in DAYS:
        for t1 in SOLVER_TIMES:
            t2 = get_next_time_slot(t1)
            if t2:
                doubles.append([{'day': day, 'time': t1}, {'day': day, 'time': t2}])
    return doubles

ALL_SINGLE_SLOTS = generate_all_single_slots()
ALL_DOUBLE_SLOTS = generate_all_double_slots()

# ------------------------------------------------------------------------
# DFS solver supporting single and double targets
# ------------------------------------------------------------------------
def is_valid_assignment(occupied_set, slot_or_slots):
    slots = slot_or_slots if isinstance(slot_or_slots, list) else [slot_or_slots]
    for s in slots:
        if (s['day'], s['time']) in occupied_set:
            return False
    return True

def dfs_targets_solver(targets, current_schedule, occupied_set):
    """
    targets: list of dicts with {'name':..., 'type': 'single'|'double'}
    current_schedule: dict mapping target_name -> slot(dict) or [dict,dict]
    occupied_set: set of (day,time) tuples already used
    Returns final schedule dict or None.
    """
    if not targets:
        return current_schedule.copy()

    target = targets[0]
    rest = targets[1:]
    tname = target['name']
    ttype = target['type']

    domain = ALL_DOUBLE_SLOTS if ttype == 'double' else ALL_SINGLE_SLOTS
    options = domain[:]
    random.shuffle(options)

    for opt in options:
        if is_valid_assignment(occupied_set, opt):
            # assign
            current_schedule[tname] = opt
            to_add = opt if isinstance(opt, list) else [opt]
            tuples = set((s['day'], s['time']) for s in to_add)
            occupied_set.update(tuples)

            result = dfs_targets_solver(rest, current_schedule, occupied_set)
            if result is not None:
                return result

            # backtrack
            del current_schedule[tname]
            occupied_set.difference_update(tuples)

    return None

# ------------------------------------------------------------------------
# Helpers to parse/pack targets and format timetable
# ------------------------------------------------------------------------
def prepare_targets_from_form(form):
    """
    Parse submitted form and return:
      - predefined_schedule: dict name->slot dict (single only)
      - predefined_occupied: set of (day,time)
      - flexible_targets: list of {'name','type'}
      - total_requested: int
      - subjects_for_template: list for re-rendering
    Packing rule implemented here: num_doubles = count // 2; num_singles = count % 2
    """
    predefined_schedule = {}
    predefined_occupied = set()
    flexible_targets = []
    total_requested = 0

    subjects_for_template = [{'name': '', 'count': 0, 'is_predefined': False, 'predefined_slots': []} for _ in range(MAX_SUBJECTS)]

    for i in range(1, MAX_SUBJECTS + 1):
        name = form.get(f'subject_name_{i}', '').strip()
        count_raw = form.get(f'classes_per_week_{i}', '0').strip()
        try:
            count = int(count_raw) if count_raw != '' else 0
        except ValueError:
            count = 0
        if count < 0:
            count = 0
        is_pre = form.get(f'predefined_{i}') == 'on'

        subjects_for_template[i-1].update({'name': name, 'count': count, 'is_predefined': is_pre})
        subjects_for_template[i-1]['predefined_slots'] = [{'day': '', 'time': ''} for _ in range(count)]

        if not name:
            continue

        total_requested += count
        if is_pre:
            # read predefined slot pairs (treated as singles)
            for j in range(1, count + 1):
                d = form.get(f'predefined_day_{i}_{j}')
                t = form.get(f'predefined_time_{i}_{j}')
                if j-1 < len(subjects_for_template[i-1]['predefined_slots']):
                    subjects_for_template[i-1]['predefined_slots'][j-1] = {'day': d or '', 'time': t or ''}
                if d and t:
                    if t == BREAK_TIME:
                        raise ValueError(f"Cannot schedule '{name}' during {BREAK_TIME}.")
                    key = (d, t)
                    if key in predefined_occupied:
                        raise ValueError(f"Duplicate predefined slot: {d} {t}")
                    inst_name = f"{name}_P{j}"
                    predefined_schedule[inst_name] = {'day': d, 'time': t}
                    predefined_occupied.add(key)
                else:
                    # missing selection: treat that instance as flexible single
                    flexible_targets.append({'name': f"{name}_S{j}", 'type': 'single'})
        else:
            # pack into doubles & singles
            num_doubles = count // 2
            num_singles = count % 2
            for k in range(1, num_doubles + 1):
                flexible_targets.append({'name': f"{name}_D{k}", 'type': 'double'})
            for k in range(1, num_singles + 1):
                flexible_targets.append({'name': f"{name}_S{k}", 'type': 'single'})

    random.shuffle(flexible_targets)
    return predefined_schedule, predefined_occupied, flexible_targets, total_requested, subjects_for_template

def format_timetable_from_schedule(final_schedule):
    """
    final_schedule: mapping target->slot or list-of-slots
    return grid: {day: {time: value}} matching template expectation.
    """
    # initialize grid with FREE PERIOD and break filled empty
    grid = {day: {time: 'FREE PERIOD' for time in SOLVER_TIMES} for day in DAYS}
    for day in DAYS:
        grid[day][BREAK_TIME] = ''  # blank for break cell

    if final_schedule:
        for target, slotinfo in final_schedule.items():
            subj = target.split('_')[0]
            if isinstance(slotinfo, list):
                for s in slotinfo:
                    d = s.get('day'); t = s.get('time')
                    if d in grid and t in grid[d]:
                        grid[d][t] = subj
            elif isinstance(slotinfo, dict):
                d = slotinfo.get('day'); t = slotinfo.get('time')
                if d in grid and t in grid[d]:
                    grid[d][t] = subj
    return grid

# ------------------------------------------------------------------------
# Flask route
# ------------------------------------------------------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    error = None
    timetable_grid = None
    schedule_found = False
    total_requested = 0
    subjects_for_template = [{'name': '', 'count': 0, 'is_predefined': False, 'predefined_slots': []} for _ in range(MAX_SUBJECTS)]

    if request.method == "POST":
        try:
            predefined_schedule, predefined_occupied, flexible_targets, total_requested, subjects_for_template = prepare_targets_from_form(request.form)

            if total_requested == 0:
                error = "Please enter at least one subject and class count."

            # compute required flexible slots (double=2, single=1)
            flexible_slots_needed = sum(2 if t['type']=='double' else 1 for t in flexible_targets)
            free_slots_available = TOTAL_AVAILABLE_SLOTS - len(predefined_occupied)
            if flexible_slots_needed > free_slots_available:
                error = f"Too many classes requested ({total_requested}). Only {free_slots_available} flexible slots available."

            if error is None:
                # Build initial occupied set and schedule starting with predefined
                initial_schedule = predefined_schedule.copy()
                occupied = set(predefined_occupied)

                # Run DFS to place flexible_targets (which contain doubles & singles)
                final_schedule = dfs_targets_solver(flexible_targets, initial_schedule, occupied)

                if final_schedule is None:
                    error = "❌ NO SOLUTION FOUND! Try removing constraints or running again."
                    # show predefined-only grid to help debugging
                    timetable_grid = format_timetable_from_schedule(predefined_schedule)
                else:
                    timetable_grid = format_timetable_from_schedule(final_schedule)
                    schedule_found = True

        except ValueError as ve:
            error = str(ve)
            # attempt to repopulate subjects_for_template from submitted form (best-effort)
            try:
                _, _, _, total_requested, subjects_for_template = prepare_targets_from_form(request.form)
            except Exception:
                pass
        except Exception as e:
            error = f"An unexpected error occurred: {e}"
            try:
                _, _, _, total_requested, subjects_for_template = prepare_targets_from_form(request.form)
            except Exception:
                pass

    # Render template with same variable names your index.html expects
    return render_template(
        "index.html",
        subjects=subjects_for_template,
        max_subjects=MAX_SUBJECTS,
        days=DAYS,
        times=DISPLAY_TIMES,
        solver_times=SOLVER_TIMES,
        break_time_str=BREAK_TIME,
        timetable=timetable_grid,
        schedule_found=schedule_found,
        error=error,
        total_available_slots=TOTAL_AVAILABLE_SLOTS,
        total_requested_classes=(total_requested if total_requested else 0),
    )

# ------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
