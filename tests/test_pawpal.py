"""
Automated test suite for PawPal+ core logic.
Run with: python -m pytest
"""

from datetime import date, timedelta
import pytest

from pawpal_system import Task, Pet, Owner, Scheduler


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def today():
    return date.today()


@pytest.fixture
def sample_owner(today):
    owner = Owner("Jordan")
    mochi = Pet("Mochi", "dog")
    luna = Pet("Luna", "cat")

    mochi.add_task(Task("Evening walk",  "18:00", 30, "medium", "daily",    due_date=today))
    mochi.add_task(Task("Morning walk",  "07:30", 20, "high",   "daily",    due_date=today))
    mochi.add_task(Task("Flea treatment","09:00",  5, "high",   "weekly",   due_date=today))

    luna.add_task(Task("Breakfast",      "07:00", 10, "high",   "daily",    due_date=today))
    luna.add_task(Task("Playtime",       "14:30", 20, "medium", "one-time", due_date=today))

    owner.add_pet(mochi)
    owner.add_pet(luna)
    return owner


# ── Task tests ────────────────────────────────────────────────────────────────

class TestTask:
    def test_mark_complete_changes_status(self, today):
        """Marking a task complete must flip its completed flag."""
        task = Task("Walk", "08:00", 20, "high", "one-time", due_date=today)
        assert task.completed is False
        task.mark_complete()
        assert task.completed is True

    def test_one_time_task_returns_no_next(self, today):
        """A one-time task should not generate a follow-up task."""
        task = Task("Vet visit", "10:00", 60, "high", "one-time", due_date=today)
        next_task = task.mark_complete()
        assert next_task is None

    def test_daily_task_creates_tomorrow(self, today):
        """Completing a daily task should produce a new task for the next day."""
        task = Task("Feeding", "07:00", 10, "high", "daily", due_date=today)
        next_task = task.mark_complete()
        assert next_task is not None
        assert next_task.due_date == today + timedelta(days=1)
        assert next_task.completed is False

    def test_weekly_task_creates_next_week(self, today):
        """Completing a weekly task should produce a new task seven days later."""
        task = Task("Grooming", "10:00", 30, "medium", "weekly", due_date=today)
        next_task = task.mark_complete()
        assert next_task is not None
        assert next_task.due_date == today + timedelta(weeks=1)


# ── Pet tests ─────────────────────────────────────────────────────────────────

class TestPet:
    def test_add_task_increases_count(self, today):
        """Adding a task to a Pet must increase its task list length."""
        pet = Pet("Mochi", "dog")
        assert len(pet.get_tasks()) == 0
        pet.add_task(Task("Walk", "08:00", 20, "high", "daily", due_date=today))
        assert len(pet.get_tasks()) == 1

    def test_remove_task_decreases_count(self, today):
        """Removing a task from a Pet must decrease its task list length."""
        pet = Pet("Luna", "cat")
        task = Task("Brushing", "11:00", 15, "low", "weekly", due_date=today)
        pet.add_task(task)
        pet.remove_task(task)
        assert len(pet.get_tasks()) == 0


# ── Owner tests ───────────────────────────────────────────────────────────────

class TestOwner:
    def test_add_pet(self):
        owner = Owner("Jordan")
        owner.add_pet(Pet("Mochi", "dog"))
        assert len(owner.pets) == 1

    def test_get_all_tasks_aggregates_pets(self, sample_owner):
        """get_all_tasks must return tasks from every owned pet."""
        pairs = sample_owner.get_all_tasks()
        # 3 Mochi tasks + 2 Luna tasks = 5
        assert len(pairs) == 5

    def test_find_pet_returns_correct_pet(self, sample_owner):
        """find_pet must return the right Pet object by name."""
        pet = sample_owner.find_pet("Luna")
        assert pet is not None
        assert pet.name == "Luna"

    def test_find_pet_returns_none_for_unknown(self, sample_owner):
        """find_pet should return None when the name doesn't match any pet."""
        assert sample_owner.find_pet("Rex") is None


# ── Scheduler tests ───────────────────────────────────────────────────────────

class TestScheduler:
    def test_sort_by_time_chronological(self, sample_owner):
        """Tasks returned by sort_by_time must be in ascending HH:MM order."""
        scheduler = Scheduler(sample_owner)
        sorted_tasks = scheduler.sort_by_time()
        times = [task.time for _, task in sorted_tasks]
        assert times == sorted(times)

    def test_filter_by_status_pending(self, sample_owner):
        """filter_by_status(False) should return only incomplete tasks."""
        scheduler = Scheduler(sample_owner)
        pending = scheduler.filter_by_status(completed=False)
        assert all(not task.completed for _, task in pending)

    def test_filter_by_status_done(self, sample_owner):
        """filter_by_status(True) should return only completed tasks."""
        scheduler = Scheduler(sample_owner)
        mochi = sample_owner.find_pet("Mochi")
        walk = mochi.get_tasks()[1]  # Morning walk
        scheduler.mark_task_complete(mochi, walk)

        done = scheduler.filter_by_status(completed=True)
        assert len(done) == 1
        assert done[0][1].description == "Morning walk"

    def test_filter_by_pet_name(self, sample_owner):
        """filter_by_pet should return only tasks belonging to the named pet."""
        scheduler = Scheduler(sample_owner)
        luna_tasks = scheduler.filter_by_pet("Luna")
        assert all(pet.name == "Luna" for pet, _ in luna_tasks)
        assert len(luna_tasks) == 2

    def test_mark_task_complete_adds_next_occurrence(self, sample_owner):
        """Completing a daily task via Scheduler must add next occurrence to the pet."""
        mochi = sample_owner.find_pet("Mochi")
        scheduler = Scheduler(sample_owner)
        initial_count = len(mochi.get_tasks())

        daily_task = mochi.get_tasks()[1]  # Morning walk (daily)
        scheduler.mark_task_complete(mochi, daily_task)

        assert len(mochi.get_tasks()) == initial_count + 1

    def test_detect_conflicts_finds_same_time(self, today):
        """detect_conflicts must flag two tasks scheduled at the exact same time."""
        owner = Owner("Test")
        pet = Pet("Buddy", "dog")
        pet.add_task(Task("Walk",     "09:00", 20, "high",   "one-time", due_date=today))
        pet.add_task(Task("Feeding",  "09:00", 10, "medium", "one-time", due_date=today))
        owner.add_pet(pet)

        scheduler = Scheduler(owner)
        conflicts = scheduler.detect_conflicts()
        assert len(conflicts) == 1
        assert "09:00" in conflicts[0]

    def test_detect_no_conflicts_when_different_times(self, today):
        """detect_conflicts must return empty list when all times are distinct."""
        owner = Owner("Test")
        pet = Pet("Buddy", "dog")
        pet.add_task(Task("Walk",    "08:00", 20, "high",   "one-time", due_date=today))
        pet.add_task(Task("Feeding", "12:00", 10, "medium", "one-time", due_date=today))
        owner.add_pet(pet)

        scheduler = Scheduler(owner)
        assert scheduler.detect_conflicts() == []

    def test_no_tasks_pet(self, today):
        """A pet with no tasks should not cause errors in the scheduler."""
        owner = Owner("Edge")
        owner.add_pet(Pet("Empty", "rabbit"))
        scheduler = Scheduler(owner)
        assert scheduler.sort_by_time() == []
        assert scheduler.detect_conflicts() == []

    def test_get_todays_schedule_excludes_completed(self, sample_owner, today):
        """Today's schedule must not include tasks that are already complete."""
        scheduler = Scheduler(sample_owner)
        mochi = sample_owner.find_pet("Mochi")
        walk = mochi.get_tasks()[1]  # Morning walk
        scheduler.mark_task_complete(mochi, walk)

        todays = scheduler.get_todays_schedule()
        descriptions = [task.description for _, task in todays]
        assert "Morning walk" not in descriptions
