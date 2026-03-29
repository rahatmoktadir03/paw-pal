"""
Automated test suite for PawPal+ core logic.
Run with: python -m pytest
"""

import json
import os
import tempfile
from datetime import date, timedelta

import pytest

from pawpal_system import (
    Task, Pet, Owner, Scheduler,
    save_to_json, load_from_json,
    task_emoji, priority_badge,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def today():
    return date.today()


@pytest.fixture
def sample_owner(today):
    owner = Owner("Jordan")
    mochi = Pet("Mochi", "dog")
    luna = Pet("Luna", "cat")

    mochi.add_task(Task("Evening walk",   "18:00", 30, "medium", "daily",    due_date=today))
    mochi.add_task(Task("Morning walk",   "07:30", 20, "high",   "daily",    due_date=today))
    mochi.add_task(Task("Flea treatment", "09:00",  5, "high",   "weekly",   due_date=today))

    luna.add_task(Task("Breakfast",       "07:00", 10, "high",   "daily",    due_date=today))
    luna.add_task(Task("Playtime",        "14:30", 20, "medium", "one-time", due_date=today))

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
        assert task.mark_complete() is None

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

    def test_serialization_round_trip(self, today):
        """A Task serialized then deserialized must equal the original."""
        task = Task("Walk", "08:00", 20, "high", "daily", due_date=today)
        restored = Task.from_dict(task.to_dict())
        assert restored.description == task.description
        assert restored.time == task.time
        assert restored.due_date == task.due_date
        assert restored.completed == task.completed


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

    def test_serialization_round_trip(self, today):
        """A Pet with tasks serialized then deserialized must preserve all data."""
        pet = Pet("Buddy", "dog")
        pet.add_task(Task("Walk", "08:00", 20, "high", "daily", due_date=today))
        restored = Pet.from_dict(pet.to_dict())
        assert restored.name == pet.name
        assert len(restored.get_tasks()) == 1
        assert restored.get_tasks()[0].description == "Walk"


# ── Owner tests ───────────────────────────────────────────────────────────────

class TestOwner:
    def test_add_pet(self):
        owner = Owner("Jordan")
        owner.add_pet(Pet("Mochi", "dog"))
        assert len(owner.pets) == 1

    def test_get_all_tasks_aggregates_pets(self, sample_owner):
        """get_all_tasks must return tasks from every owned pet."""
        assert len(sample_owner.get_all_tasks()) == 5

    def test_find_pet_returns_correct_pet(self, sample_owner):
        pet = sample_owner.find_pet("Luna")
        assert pet is not None
        assert pet.name == "Luna"

    def test_find_pet_returns_none_for_unknown(self, sample_owner):
        assert sample_owner.find_pet("Rex") is None

    def test_serialization_round_trip(self, sample_owner):
        """An Owner round-tripped through to_dict / from_dict must preserve all pets and tasks."""
        restored = Owner.from_dict(sample_owner.to_dict())
        assert restored.name == sample_owner.name
        assert len(restored.pets) == len(sample_owner.pets)
        assert len(restored.get_all_tasks()) == len(sample_owner.get_all_tasks())


# ── Persistence tests (Challenge 2) ───────────────────────────────────────────

class TestPersistence:
    def test_save_and_load(self, sample_owner):
        """save_to_json / load_from_json must preserve full owner state."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            path = tmp.name
        try:
            save_to_json(sample_owner, path)
            loaded = load_from_json(path)
            assert loaded is not None
            assert loaded.name == sample_owner.name
            assert len(loaded.pets) == len(sample_owner.pets)
            assert len(loaded.get_all_tasks()) == len(sample_owner.get_all_tasks())
        finally:
            os.unlink(path)

    def test_load_missing_file_returns_none(self):
        """load_from_json must return None when the file does not exist."""
        assert load_from_json("/nonexistent/path/data.json") is None

    def test_json_file_structure(self, sample_owner):
        """Saved JSON must have an 'owner' key with correct nested structure."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as tmp:
            path = tmp.name
        try:
            save_to_json(sample_owner, path)
            with open(path) as fh:
                data = json.load(fh)
            assert "owner" in data
            assert "pets" in data["owner"]
            assert data["owner"]["name"] == sample_owner.name
        finally:
            os.unlink(path)


# ── Scheduler tests ───────────────────────────────────────────────────────────

class TestScheduler:
    def test_sort_by_time_chronological(self, sample_owner):
        """sort_by_time must return tasks in ascending HH:MM order."""
        scheduler = Scheduler(sample_owner)
        times = [t.time for _, t in scheduler.sort_by_time()]
        assert times == sorted(times)

    def test_sort_by_priority_then_time(self, sample_owner):
        """High-priority tasks must appear before medium, medium before low."""
        from pawpal_system import PRIORITY_WEIGHT
        scheduler = Scheduler(sample_owner)
        sorted_tasks = scheduler.sort_by_priority_then_time()
        weights = [PRIORITY_WEIGHT.get(t.priority, 0) for _, t in sorted_tasks]
        # Weights should be non-increasing
        assert weights == sorted(weights, reverse=True)

    def test_filter_by_status_pending(self, sample_owner):
        scheduler = Scheduler(sample_owner)
        assert all(not t.completed for _, t in scheduler.filter_by_status(False))

    def test_filter_by_status_done(self, sample_owner):
        scheduler = Scheduler(sample_owner)
        mochi = sample_owner.find_pet("Mochi")
        scheduler.mark_task_complete(mochi, mochi.get_tasks()[1])
        done = scheduler.filter_by_status(True)
        assert len(done) == 1

    def test_filter_by_pet_name(self, sample_owner):
        scheduler = Scheduler(sample_owner)
        luna_tasks = scheduler.filter_by_pet("Luna")
        assert all(pet.name == "Luna" for pet, _ in luna_tasks)
        assert len(luna_tasks) == 2

    def test_mark_task_complete_adds_next_occurrence(self, sample_owner):
        """Completing a daily task must add the next occurrence to the pet."""
        mochi = sample_owner.find_pet("Mochi")
        scheduler = Scheduler(sample_owner)
        before = len(mochi.get_tasks())
        scheduler.mark_task_complete(mochi, mochi.get_tasks()[1])
        assert len(mochi.get_tasks()) == before + 1

    def test_detect_conflicts_finds_same_time(self, today):
        owner = Owner("Test")
        pet = Pet("Buddy", "dog")
        pet.add_task(Task("Walk",    "09:00", 20, "high",   "one-time", due_date=today))
        pet.add_task(Task("Feeding", "09:00", 10, "medium", "one-time", due_date=today))
        owner.add_pet(pet)
        conflicts = Scheduler(owner).detect_conflicts()
        assert len(conflicts) == 1
        assert "09:00" in conflicts[0]

    def test_detect_no_conflicts_when_different_times(self, today):
        owner = Owner("Test")
        pet = Pet("Buddy", "dog")
        pet.add_task(Task("Walk",    "08:00", 20, "high",   "one-time", due_date=today))
        pet.add_task(Task("Feeding", "12:00", 10, "medium", "one-time", due_date=today))
        owner.add_pet(pet)
        assert Scheduler(owner).detect_conflicts() == []

    def test_no_tasks_pet(self):
        owner = Owner("Edge")
        owner.add_pet(Pet("Empty", "rabbit"))
        scheduler = Scheduler(owner)
        assert scheduler.sort_by_time() == []
        assert scheduler.detect_conflicts() == []

    def test_get_todays_schedule_excludes_completed(self, sample_owner):
        scheduler = Scheduler(sample_owner)
        mochi = sample_owner.find_pet("Mochi")
        scheduler.mark_task_complete(mochi, mochi.get_tasks()[1])
        descriptions = [t.description for _, t in scheduler.get_todays_schedule()]
        assert "Morning walk" not in descriptions

    # ── Next available slot (Challenge 1) ─────────────────────────────

    def test_next_slot_fits_before_first_task(self, today):
        """A short task should slot in before the first scheduled task."""
        owner = Owner("Test")
        pet = Pet("Rex", "dog")
        # Only task is at 10:00 for 30 min
        pet.add_task(Task("Walk", "10:00", 30, "high", "one-time", due_date=today))
        owner.add_pet(pet)
        slot = Scheduler(owner).find_next_available_slot(20)
        # Slot should be at 07:00 (the earliest allowed) or before 10:00
        assert slot is not None
        h, m = map(int, slot.split(":"))
        assert h * 60 + m + 20 <= 10 * 60

    def test_next_slot_after_all_tasks(self, today):
        """A task should be slotted after all existing tasks if no earlier gap exists."""
        owner = Owner("Test")
        pet = Pet("Rex", "dog")
        pet.add_task(Task("Walk",  "07:00", 60, "high", "one-time", due_date=today))
        pet.add_task(Task("Feed",  "08:00", 60, "high", "one-time", due_date=today))
        owner.add_pet(pet)
        slot = Scheduler(owner).find_next_available_slot(30)
        assert slot is not None
        assert slot >= "09:00"

    def test_next_slot_returns_none_when_full(self, today):
        """find_next_available_slot must return None when the day is fully booked."""
        owner = Owner("Test")
        pet = Pet("Rex", "dog")
        # Book a 15-hour block from 07:00
        pet.add_task(Task("Long task", "07:00", 15 * 60, "high", "one-time", due_date=today))
        owner.add_pet(pet)
        # Try to fit a 2-hour task — should fail
        assert Scheduler(owner).find_next_available_slot(120) is None


# ── Utility function tests (Challenge 4) ──────────────────────────────────────

class TestUtils:
    def test_task_emoji_walk(self):
        assert task_emoji("Morning walk") == "🐕"

    def test_task_emoji_feeding(self):
        assert task_emoji("Breakfast time") == "🍽️"

    def test_task_emoji_medicine(self):
        assert task_emoji("Flea treatment") == "💊"

    def test_task_emoji_default(self):
        assert task_emoji("Something random") == "📋"

    def test_priority_badge_high(self):
        assert "High" in priority_badge("high")
        assert "🔴" in priority_badge("high")

    def test_priority_badge_medium(self):
        assert "Medium" in priority_badge("medium")
        assert "🟡" in priority_badge("medium")

    def test_priority_badge_low(self):
        assert "Low" in priority_badge("low")
        assert "🟢" in priority_badge("low")
