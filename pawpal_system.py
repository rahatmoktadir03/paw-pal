"""
PawPal+ Logic Layer
Core classes: Task, Pet, Owner, Scheduler
Includes: serialization, next-slot finder, priority-weighted scheduling,
          recurring tasks, and conflict detection.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple
import json
import os

# Priority weights used for weighted scheduling (Challenge 1 + 3)
PRIORITY_WEIGHT: Dict[str, int] = {"high": 3, "medium": 2, "low": 1}

# Emoji map for task-type detection (Challenge 4)
_TASK_EMOJI_MAP: List[Tuple[List[str], str]] = [
    (["walk", "run", "jog", "hike"],          "🐕"),
    # medicine before food so "flea treatment" isn't caught by "treat"
    (["med", "medicine", "pill", "tablet",
      "inject", "vaccination", "flea",
      "deworm", "treatment"],                 "💊"),
    (["feed", "food", "breakfast", "lunch",
      "dinner", "meal", "treat", "snack"],    "🍽️"),
    (["groom", "brush", "bath", "wash",
      "trim", "nail", "clip"],                "✂️"),
    (["play", "enrich", "game", "toy",
      "fetch", "train"],                      "🎾"),
    (["vet", "clinic", "checkup", "check"],   "🏥"),
    (["sleep", "nap", "rest", "bed",
      "crate"],                               "😴"),
]


def task_emoji(description: str) -> str:
    """Return a representative emoji for a task based on its description keywords."""
    lower = description.lower()
    for keywords, emoji in _TASK_EMOJI_MAP:
        if any(k in lower for k in keywords):
            return emoji
    return "📋"


def priority_badge(priority: str) -> str:
    """Return a coloured-dot prefix for a priority level."""
    return {"high": "🔴 High", "medium": "🟡 Medium", "low": "🟢 Low"}.get(
        priority, priority
    )


# ── Task ──────────────────────────────────────────────────────────────────────

@dataclass
class Task:
    """Represents a single pet care activity."""

    description: str
    time: str           # "HH:MM" 24-hour format
    duration_minutes: int
    priority: str       # "low", "medium", "high"
    frequency: str      # "one-time", "daily", "weekly"
    completed: bool = False
    due_date: date = field(default_factory=date.today)

    # ------------------------------------------------------------------
    # Recurrence
    # ------------------------------------------------------------------

    def mark_complete(self) -> Optional["Task"]:
        """Mark this task done; return next occurrence if recurring, else None."""
        self.completed = True
        if self.frequency == "daily":
            return Task(
                description=self.description,
                time=self.time,
                duration_minutes=self.duration_minutes,
                priority=self.priority,
                frequency=self.frequency,
                due_date=self.due_date + timedelta(days=1),
            )
        if self.frequency == "weekly":
            return Task(
                description=self.description,
                time=self.time,
                duration_minutes=self.duration_minutes,
                priority=self.priority,
                frequency=self.frequency,
                due_date=self.due_date + timedelta(weeks=1),
            )
        return None

    # ------------------------------------------------------------------
    # Serialization (Challenge 2)
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this Task to a JSON-safe dictionary."""
        return {
            "description": self.description,
            "time": self.time,
            "duration_minutes": self.duration_minutes,
            "priority": self.priority,
            "frequency": self.frequency,
            "completed": self.completed,
            "due_date": self.due_date.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        """Reconstruct a Task from a serialized dictionary."""
        return cls(
            description=data["description"],
            time=data["time"],
            duration_minutes=data["duration_minutes"],
            priority=data["priority"],
            frequency=data["frequency"],
            completed=data.get("completed", False),
            due_date=date.fromisoformat(data["due_date"]),
        )

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def __str__(self) -> str:
        """Human-readable task summary."""
        status = "done" if self.completed else "todo"
        return (
            f"[{status}] {self.time} - {self.description} "
            f"({self.duration_minutes} min, {self.priority} priority, {self.frequency})"
        )


# ── Pet ───────────────────────────────────────────────────────────────────────

class Pet:
    """Stores pet details and manages its task list."""

    def __init__(self, name: str, species: str) -> None:
        """Initialise a pet with a name and species."""
        self.name = name
        self.species = species
        self.tasks: List[Task] = []

    def add_task(self, task: Task) -> None:
        """Add a task to this pet's list."""
        self.tasks.append(task)

    def remove_task(self, task: Task) -> None:
        """Remove a task from this pet's list."""
        self.tasks.remove(task)

    def get_tasks(self) -> List[Task]:
        """Return all tasks for this pet."""
        return self.tasks

    # Serialization (Challenge 2)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this Pet to a JSON-safe dictionary."""
        return {
            "name": self.name,
            "species": self.species,
            "tasks": [t.to_dict() for t in self.tasks],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Pet":
        """Reconstruct a Pet from a serialized dictionary."""
        pet = cls(name=data["name"], species=data["species"])
        for task_data in data.get("tasks", []):
            pet.add_task(Task.from_dict(task_data))
        return pet

    def __str__(self) -> str:
        """Human-readable pet summary."""
        return f"{self.name} ({self.species})"


# ── Owner ─────────────────────────────────────────────────────────────────────

class Owner:
    """Manages multiple pets and provides access to all their tasks."""

    def __init__(self, name: str) -> None:
        """Initialise an owner with a name."""
        self.name = name
        self.pets: List[Pet] = []

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner's roster."""
        self.pets.append(pet)

    def remove_pet(self, pet: Pet) -> None:
        """Remove a pet from this owner's roster."""
        self.pets.remove(pet)

    def get_all_tasks(self) -> List[Tuple[Pet, Task]]:
        """Return every (pet, task) pair across all owned pets."""
        pairs: List[Tuple[Pet, Task]] = []
        for pet in self.pets:
            for task in pet.get_tasks():
                pairs.append((pet, task))
        return pairs

    def find_pet(self, name: str) -> Optional[Pet]:
        """Return the Pet with the given name, or None if not found."""
        for pet in self.pets:
            if pet.name == name:
                return pet
        return None

    # Serialization (Challenge 2)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this Owner (and all pets/tasks) to a JSON-safe dictionary."""
        return {
            "name": self.name,
            "pets": [p.to_dict() for p in self.pets],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Owner":
        """Reconstruct an Owner (with all pets and tasks) from a serialized dictionary."""
        owner = cls(name=data["name"])
        for pet_data in data.get("pets", []):
            owner.add_pet(Pet.from_dict(pet_data))
        return owner

    def __str__(self) -> str:
        """Human-readable owner summary."""
        return f"Owner: {self.name} | Pets: {', '.join(p.name for p in self.pets)}"


# ── Persistence helpers (Challenge 2) ─────────────────────────────────────────

DATA_FILE = "data.json"


def save_to_json(owner: Owner, path: str = DATA_FILE) -> None:
    """Persist owner, pets, and tasks to a JSON file."""
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"owner": owner.to_dict()}, fh, indent=2)


def load_from_json(path: str = DATA_FILE) -> Optional[Owner]:
    """Load an Owner from a JSON file; return None if the file does not exist."""
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    return Owner.from_dict(data["owner"]) if "owner" in data else None


# ── Scheduler ─────────────────────────────────────────────────────────────────

class Scheduler:
    """Retrieves, organises, and manages tasks across all of an owner's pets."""

    def __init__(self, owner: Owner) -> None:
        """Initialise the scheduler with an owner."""
        self.owner = owner

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get_all_tasks(self) -> List[Tuple[Pet, Task]]:
        """Return all (pet, task) pairs from the owner."""
        return self.owner.get_all_tasks()

    def get_todays_schedule(self) -> List[Tuple[Pet, Task]]:
        """Return today's incomplete tasks sorted by time."""
        today = date.today()
        todays = [
            (pet, task)
            for pet, task in self.get_all_tasks()
            if task.due_date == today and not task.completed
        ]
        return self.sort_by_time(todays)

    # ------------------------------------------------------------------
    # Sorting (Challenge 1 + 3)
    # ------------------------------------------------------------------

    def sort_by_time(
        self, tasks: Optional[List[Tuple[Pet, Task]]] = None
    ) -> List[Tuple[Pet, Task]]:
        """Return tasks sorted chronologically by their HH:MM time string."""
        if tasks is None:
            tasks = self.get_all_tasks()
        return sorted(tasks, key=lambda pair: pair[1].time)

    def sort_by_priority_then_time(
        self, tasks: Optional[List[Tuple[Pet, Task]]] = None
    ) -> List[Tuple[Pet, Task]]:
        """Return tasks sorted by priority (high first) then chronologically.

        Uses PRIORITY_WEIGHT to convert priority strings to numeric scores so
        'high' always appears before 'medium' and 'medium' before 'low'.
        Tasks with the same priority are sub-sorted by HH:MM time.
        """
        if tasks is None:
            tasks = self.get_all_tasks()
        return sorted(
            tasks,
            key=lambda pair: (
                -PRIORITY_WEIGHT.get(pair[1].priority, 0),  # higher weight → earlier
                pair[1].time,
            ),
        )

    # ------------------------------------------------------------------
    # Filtering
    # ------------------------------------------------------------------

    def filter_by_status(
        self,
        completed: bool,
        tasks: Optional[List[Tuple[Pet, Task]]] = None,
    ) -> List[Tuple[Pet, Task]]:
        """Return only tasks matching the given completion status."""
        if tasks is None:
            tasks = self.get_all_tasks()
        return [(pet, task) for pet, task in tasks if task.completed == completed]

    def filter_by_pet(
        self,
        pet_name: str,
        tasks: Optional[List[Tuple[Pet, Task]]] = None,
    ) -> List[Tuple[Pet, Task]]:
        """Return only tasks belonging to the named pet."""
        if tasks is None:
            tasks = self.get_all_tasks()
        return [(pet, task) for pet, task in tasks if pet.name == pet_name]

    # ------------------------------------------------------------------
    # Next available slot (Challenge 1)
    # ------------------------------------------------------------------

    def find_next_available_slot(
        self,
        duration_minutes: int,
        start_hour: int = 7,
        end_hour: int = 22,
    ) -> Optional[str]:
        """Find the earliest free HH:MM slot today that fits a task of given duration.

        Builds a list of occupied intervals from today's tasks (considering their
        actual durations) and walks forward from *start_hour* until a gap large
        enough to fit *duration_minutes* is found.  Returns None if no slot exists
        before *end_hour*.
        """
        today = date.today()
        today_tasks = [
            task
            for _, task in self.get_all_tasks()
            if task.due_date == today
        ]

        # Build sorted list of (start_min, end_min) intervals
        occupied: List[Tuple[int, int]] = []
        for task in today_tasks:
            h, m = map(int, task.time.split(":"))
            start_min = h * 60 + m
            occupied.append((start_min, start_min + task.duration_minutes))
        occupied.sort()

        cursor = start_hour * 60
        limit = end_hour * 60

        for occ_start, occ_end in occupied:
            if cursor + duration_minutes <= occ_start:
                # Gap before this task is large enough
                h, m = divmod(cursor, 60)
                return f"{h:02d}:{m:02d}"
            # Advance cursor past this task if it overlaps
            cursor = max(cursor, occ_end)

        # Check for a gap after the last task
        if cursor + duration_minutes <= limit:
            h, m = divmod(cursor, 60)
            return f"{h:02d}:{m:02d}"

        return None  # no slot available today

    # ------------------------------------------------------------------
    # Recurring tasks
    # ------------------------------------------------------------------

    def mark_task_complete(self, pet: Pet, task: Task) -> Optional[Task]:
        """Mark a task complete and auto-schedule the next occurrence if recurring."""
        next_task = task.mark_complete()
        if next_task is not None:
            pet.add_task(next_task)
        return next_task

    # ------------------------------------------------------------------
    # Conflict detection
    # ------------------------------------------------------------------

    def detect_conflicts(
        self, tasks: Optional[List[Tuple[Pet, Task]]] = None
    ) -> List[str]:
        """Return warning strings for any two tasks scheduled at the exact same time."""
        if tasks is None:
            tasks = self.get_all_tasks()

        warnings: List[str] = []
        seen: Dict[str, Tuple[Pet, Task]] = {}

        for pet, task in tasks:
            key = task.time
            if key in seen:
                prev_pet, prev_task = seen[key]
                warnings.append(
                    f"Conflict at {task.time}: '{prev_task.description}' "
                    f"({prev_pet.name}) and '{task.description}' ({pet.name})"
                )
            else:
                seen[key] = (pet, task)

        return warnings

    # ------------------------------------------------------------------
    # Terminal display
    # ------------------------------------------------------------------

    def print_schedule(
        self, tasks: Optional[List[Tuple[Pet, Task]]] = None, label: str = "Schedule"
    ) -> None:
        """Print a formatted schedule to the terminal."""
        if tasks is None:
            tasks = self.sort_by_time()

        print(f"\n{'=' * 55}")
        print(f"  {label}")
        print(f"{'=' * 55}")

        if not tasks:
            print("  (no tasks)")
        else:
            for pet, task in tasks:
                print(f"  [{pet.name:10s}] {task}")

        conflicts = self.detect_conflicts(tasks)
        if conflicts:
            print()
            for warning in conflicts:
                print(f"  WARNING: {warning}")

        print(f"{'=' * 55}\n")
