"""
PawPal+ Streamlit UI
Connects Owner / Pet / Task / Scheduler backend to an interactive web app.
"""

import streamlit as st
from datetime import date

from pawpal_system import Owner, Pet, Task, Scheduler

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="wide")
st.title("🐾 PawPal+")
st.caption("Smart pet care scheduling — powered by Python classes and Streamlit.")

# ── Session-state bootstrap ────────────────────────────────────────────────────
# st.session_state acts as a persistent "vault" so objects survive re-runs.
if "owner" not in st.session_state:
    st.session_state.owner = None  # Owner is created once in the sidebar

# ── Sidebar: Owner + Pet management ───────────────────────────────────────────
with st.sidebar:
    st.header("Owner Setup")

    owner_name = st.text_input("Your name", value="Jordan")

    if st.button("Set / update owner"):
        if st.session_state.owner is None or st.session_state.owner.name != owner_name:
            st.session_state.owner = Owner(owner_name)
            st.success(f"Owner set to {owner_name}")

    if st.session_state.owner is None:
        st.info("Click 'Set / update owner' to get started.")
        st.stop()

    owner: Owner = st.session_state.owner

    st.divider()
    st.header("Add a Pet")

    pet_name_input = st.text_input("Pet name", key="new_pet_name")
    species_input = st.selectbox("Species", ["dog", "cat", "rabbit", "bird", "other"], key="new_pet_species")

    if st.button("Add pet"):
        if pet_name_input.strip():
            if owner.find_pet(pet_name_input.strip()) is not None:
                st.warning(f"'{pet_name_input}' already exists.")
            else:
                owner.add_pet(Pet(pet_name_input.strip(), species_input))
                st.success(f"Added {pet_name_input} ({species_input})")
        else:
            st.error("Please enter a pet name.")

    if owner.pets:
        st.divider()
        st.subheader("Your pets")
        for pet in owner.pets:
            st.markdown(f"- **{pet.name}** ({pet.species})")

# ── Main area ─────────────────────────────────────────────────────────────────
owner: Owner = st.session_state.owner
scheduler = Scheduler(owner)

tab_add, tab_schedule, tab_manage = st.tabs(["Add Task", "Today's Schedule", "All Tasks"])

# ── Tab 1: Add Task ────────────────────────────────────────────────────────────
with tab_add:
    st.subheader("Schedule a New Task")

    if not owner.pets:
        st.info("Add at least one pet in the sidebar first.")
    else:
        pet_names = [p.name for p in owner.pets]

        col1, col2 = st.columns(2)
        with col1:
            selected_pet_name = st.selectbox("Pet", pet_names, key="task_pet")
            task_desc = st.text_input("Task description", value="Morning walk", key="task_desc")
            task_time = st.text_input("Time (HH:MM)", value="07:30", key="task_time")
        with col2:
            duration = st.number_input("Duration (minutes)", min_value=1, max_value=480, value=20, key="task_dur")
            priority = st.selectbox("Priority", ["low", "medium", "high"], index=2, key="task_pri")
            frequency = st.selectbox("Frequency", ["one-time", "daily", "weekly"], key="task_freq")
            due = st.date_input("Due date", value=date.today(), key="task_due")

        if st.button("Add task"):
            # Validate HH:MM
            try:
                h, m = task_time.strip().split(":")
                if not (0 <= int(h) <= 23 and 0 <= int(m) <= 59):
                    raise ValueError
                time_str = f"{int(h):02d}:{int(m):02d}"
            except (ValueError, AttributeError):
                st.error("Time must be in HH:MM format (e.g. 09:30).")
                time_str = None

            if time_str and task_desc.strip():
                pet = owner.find_pet(selected_pet_name)
                new_task = Task(
                    description=task_desc.strip(),
                    time=time_str,
                    duration_minutes=int(duration),
                    priority=priority,
                    frequency=frequency,
                    due_date=due,
                )
                pet.add_task(new_task)
                st.success(f"Task '{task_desc}' added for {selected_pet_name} at {time_str}.")

                # Show conflict warning immediately
                conflicts = scheduler.detect_conflicts()
                if conflicts:
                    for w in conflicts:
                        st.warning(w)

# ── Tab 2: Today's Schedule ───────────────────────────────────────────────────
with tab_schedule:
    st.subheader(f"Today's Schedule — {date.today().strftime('%A, %B %d %Y')}")

    todays_tasks = scheduler.get_todays_schedule()
    conflicts = scheduler.detect_conflicts(todays_tasks)

    if conflicts:
        st.error("**Scheduling conflicts detected:**")
        for w in conflicts:
            st.warning(w)

    if not todays_tasks:
        st.info("No tasks scheduled for today. Add some in the 'Add Task' tab.")
    else:
        rows = []
        for pet, task in todays_tasks:
            rows.append({
                "Time": task.time,
                "Pet": pet.name,
                "Task": task.description,
                "Duration (min)": task.duration_minutes,
                "Priority": task.priority,
                "Frequency": task.frequency,
                "Status": "Done" if task.completed else "Pending",
            })
        st.table(rows)

        st.divider()
        st.subheader("Mark a task complete")

        pending_today = [(pet, task) for pet, task in todays_tasks if not task.completed]
        if pending_today:
            task_labels = [f"{task.time} - {pet.name}: {task.description}" for pet, task in pending_today]
            chosen_label = st.selectbox("Select task to complete", task_labels, key="complete_select")
            chosen_idx = task_labels.index(chosen_label)
            chosen_pet, chosen_task = pending_today[chosen_idx]

            if st.button("Mark complete"):
                next_task = scheduler.mark_task_complete(chosen_pet, chosen_task)
                st.success(f"'{chosen_task.description}' marked complete!")
                if next_task:
                    st.info(
                        f"Next occurrence scheduled: {next_task.description} "
                        f"on {next_task.due_date.strftime('%A, %B %d %Y')}"
                    )
                st.rerun()
        else:
            st.success("All tasks for today are complete!")

# ── Tab 3: All Tasks ──────────────────────────────────────────────────────────
with tab_manage:
    st.subheader("All Tasks")

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        pet_filter = st.selectbox(
            "Filter by pet",
            ["All"] + [p.name for p in owner.pets],
            key="filter_pet",
        )
    with col_f2:
        status_filter = st.selectbox(
            "Filter by status",
            ["All", "Pending", "Done"],
            key="filter_status",
        )

    all_tasks = scheduler.sort_by_time()

    if pet_filter != "All":
        all_tasks = scheduler.filter_by_pet(pet_filter, all_tasks)

    if status_filter == "Pending":
        all_tasks = scheduler.filter_by_status(completed=False, tasks=all_tasks)
    elif status_filter == "Done":
        all_tasks = scheduler.filter_by_status(completed=True, tasks=all_tasks)

    if not all_tasks:
        st.info("No tasks match the selected filters.")
    else:
        rows = []
        for pet, task in all_tasks:
            rows.append({
                "Due": str(task.due_date),
                "Time": task.time,
                "Pet": pet.name,
                "Task": task.description,
                "Duration (min)": task.duration_minutes,
                "Priority": task.priority,
                "Frequency": task.frequency,
                "Status": "Done" if task.completed else "Pending",
            })
        st.table(rows)

    st.divider()
    conflicts_all = scheduler.detect_conflicts()
    if conflicts_all:
        st.subheader("All Conflicts")
        for w in conflicts_all:
            st.warning(w)
    else:
        st.success("No scheduling conflicts across all tasks.")
