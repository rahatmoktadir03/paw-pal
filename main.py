"""
PawPal+ Demo Script
Demonstrates core logic: owners, pets, tasks, scheduling, sorting, filtering,
recurring tasks, and conflict detection.
"""

from datetime import date
from pawpal_system import Owner, Pet, Task, Scheduler


def main() -> None:
    # ── Setup ──────────────────────────────────────────────────────────
    owner = Owner("Jordan")

    mochi = Pet("Mochi", "dog")
    luna = Pet("Luna", "cat")
    owner.add_pet(mochi)
    owner.add_pet(luna)

    # ── Add tasks (intentionally out of order) ─────────────────────────
    today = date.today()

    mochi.add_task(Task("Evening walk",    "18:00", 30,  "medium", "daily",    due_date=today))
    mochi.add_task(Task("Morning walk",    "07:30", 20,  "high",   "daily",    due_date=today))
    mochi.add_task(Task("Flea treatment",  "09:00", 5,   "high",   "weekly",   due_date=today))
    mochi.add_task(Task("Dental chew",     "09:00", 5,   "low",    "daily",    due_date=today))  # conflicts with flea treatment

    luna.add_task(Task("Breakfast",        "07:00", 10,  "high",   "daily",    due_date=today))
    luna.add_task(Task("Brushing",         "11:00", 15,  "weekly", "one-time", due_date=today))
    luna.add_task(Task("Playtime",         "14:30", 20,  "medium", "one-time", due_date=today))

    scheduler = Scheduler(owner)

    # ── Today's sorted schedule ────────────────────────────────────────
    scheduler.print_schedule(scheduler.get_todays_schedule(), "Today's Schedule")

    # ── Filtering demos ────────────────────────────────────────────────
    mochi_tasks = scheduler.filter_by_pet("Mochi")
    scheduler.print_schedule(mochi_tasks, "Mochi's Tasks")

    # ── Mark a recurring task complete ─────────────────────────────────
    morning_walk = mochi.get_tasks()[1]  # "Morning walk"
    print(f"Marking complete: {morning_walk.description}")
    next_task = scheduler.mark_task_complete(mochi, morning_walk)
    if next_task:
        print(f"  -> Next occurrence added: {next_task.description} on {next_task.due_date}\n")

    # ── Pending tasks after completion ────────────────────────────────
    pending = scheduler.filter_by_status(completed=False)
    scheduler.print_schedule(scheduler.sort_by_time(pending), "Pending Tasks")

    # ── Conflict detection ─────────────────────────────────────────────
    print("Conflict check:")
    conflicts = scheduler.detect_conflicts()
    if conflicts:
        for w in conflicts:
            print(f"  {w}")
    else:
        print("  No conflicts found.")
    print()


if __name__ == "__main__":
    main()
