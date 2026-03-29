# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Features

- **Owner & pet management** — add multiple pets (dogs, cats, rabbits, etc.) under a single owner profile.
- **Task scheduling** — create care activities with a description, time, duration, priority, and frequency.
- **Sorting by time** — the daily schedule is always displayed in chronological (HH:MM) order using Python's `sorted()` with a lambda key.
- **Filtering** — view tasks filtered by pet name or completion status (Pending / Done).
- **Recurring tasks** — marking a daily or weekly task complete automatically schedules the next occurrence using Python's `timedelta`.
- **Conflict warnings** — the Scheduler detects when two tasks share the exact same time slot and surfaces a warning in the UI rather than crashing the app.
- **Session persistence** — `st.session_state` keeps your owner and pets alive across Streamlit re-runs within the same browser session.

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Run the app

```bash
streamlit run app.py
```

### Run the demo script (terminal only)

```bash
python main.py
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## Architecture

```
pawpal_system.py   — logic layer (Task, Pet, Owner, Scheduler)
app.py             — Streamlit UI (imports from pawpal_system)
main.py            — terminal demo / manual testing script
tests/
  test_pawpal.py   — automated pytest suite (19 tests)
reflection.md      — design decisions and AI collaboration notes
```

## Smarter Scheduling

PawPal+ goes beyond a simple task list with four algorithmic features:

| Feature                | Method                                                    | How it works                                                                                     |
| ---------------------- | --------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| **Sort by time**       | `Scheduler.sort_by_time()`                                | `sorted()` with `lambda pair: pair[1].time` on HH:MM strings                                     |
| **Filter tasks**       | `Scheduler.filter_by_pet()` / `filter_by_status()`        | Composable list comprehensions; accept an optional task list so filters chain                    |
| **Recurring tasks**    | `Task.mark_complete()` + `Scheduler.mark_task_complete()` | Returns a new Task with `due_date + timedelta(days=1 or weeks=1)` and auto-appends it to the pet |
| **Conflict detection** | `Scheduler.detect_conflicts()`                            | Dict-based O(n) scan; returns warning strings instead of raising exceptions                      |

## Testing PawPal+

```bash
python -m pytest
```

The test suite (`tests/test_pawpal.py`) covers:

- Task completion status changes
- Daily / weekly recurrence produces correct next due dates
- Task addition increases a pet's task count
- Chronological sort correctness
- Filtering by pet name and completion status
- Conflict detection flags same-time tasks; passes distinct times
- Edge case: scheduler with a zero-task pet
- Today's schedule excludes already-completed tasks

**Confidence level: ★★★★☆** — all 19 tests pass green.

## 📸 Demo

<a href="pawpal.png" target="_blank"><img src='pawpal.png' title='PawPal App' width='' alt='PawPal App' class='center-block' /></a>
