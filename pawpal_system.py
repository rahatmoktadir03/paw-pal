"""
PawPal+ Logic Layer
Core classes: Task, Pet, Owner, Scheduler
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import List, Optional, Tuple


@dataclass
class Task:
    """Represents a single pet care activity."""

    description: str
    time: str  # "HH:MM" 24-hour format
    duration_minutes: int
    priority: str  # "low", "medium", "high"
    frequency: str  # "one-time", "daily", "weekly"
    completed: bool = False
    due_date: date = field(default_factory=date.today)

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

    def __str__(self) -> str:
        """Human-readable task summary."""
        status = "done" if self.completed else "todo"
        return (
            f"[{status}] {self.time} - {self.description} "
            f"({self.duration_minutes} min, {self.priority} priority, {self.frequency})"
        )


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

    def __str__(self) -> str:
        """Human-readable pet summary."""
        return f"{self.name} ({self.species})"


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

    def __str__(self) -> str:
        """Human-readable owner summary."""
        return f"Owner: {self.name} | Pets: {', '.join(p.name for p in self.pets)}"


class Scheduler:
    """Retrieves, organises, and manages tasks across all of an owner's pets."""

    def __init__(self, owner: Owner) -> None:
        """Initialise the scheduler with an owner."""
        self.owner = owner

    # ------------------------------------------------------------------
    # Retrieval helpers
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
    # Sorting
    # ------------------------------------------------------------------

    def sort_by_time(
        self, tasks: Optional[List[Tuple[Pet, Task]]] = None
    ) -> List[Tuple[Pet, Task]]:
        """Return tasks sorted chronologically by their HH:MM time string."""
        if tasks is None:
            tasks = self.get_all_tasks()
        return sorted(tasks, key=lambda pair: pair[1].time)

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
        seen: dict = {}  # time -> (pet, task)

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
    # Display
    # ------------------------------------------------------------------

    def print_schedule(
        self, tasks: Optional[List[Tuple[Pet, Task]]] = None, label: str = "Schedule"
    ) -> None:
        """Print a formatted schedule to the terminal."""
        if tasks is None:
            tasks = self.sort_by_time()

        print(f"\n{'=' * 50}")
        print(f"  {label}")
        print(f"{'=' * 50}")

        if not tasks:
            print("  (no tasks)")
        else:
            for pet, task in tasks:
                print(f"  [{pet.name:10s}] {task}")

        conflicts = self.detect_conflicts(tasks)
        if conflicts:
            print()
            for warning in conflicts:
                # Strip emoji for terminals that don't support Unicode
                print(f"  {warning}")

        print(f"{'=' * 50}\n")
