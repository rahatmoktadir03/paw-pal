"""
PawPal+ Streamlit UI
Full implementation with data persistence, priority scheduling,
conflict detection, next-slot finder, and polished visuals.
"""

import streamlit as st
from datetime import date

from pawpal_system import (
    Owner, Pet, Task, Scheduler,
    save_to_json, load_from_json,
    task_emoji, priority_badge,
)

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="wide")

# ── CSS: coloured priority rows ────────────────────────────────────────────────
st.markdown(
    """
    <style>
    .priority-high   { background:#fde8e8; border-left:4px solid #e53e3e;
                       padding:6px 10px; border-radius:4px; margin:2px 0; }
    .priority-medium { background:#fef9e7; border-left:4px solid #d4a017;
                       padding:6px 10px; border-radius:4px; margin:2px 0; }
    .priority-low    { background:#eafaf1; border-left:4px solid #27ae60;
                       padding:6px 10px; border-radius:4px; margin:2px 0; }
    .task-done       { opacity:0.45; text-decoration:line-through; }
    .conflict-box    { background:#fff3cd; border:1px solid #ffc107;
                       padding:8px 12px; border-radius:6px; margin:4px 0; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Session-state bootstrap ────────────────────────────────────────────────────
# Load persisted data on the very first run; fall back to None so the
# sidebar can prompt the user to create an owner.
if "owner" not in st.session_state:
    st.session_state.owner = load_from_json()


def _save() -> None:
    """Persist current owner state to data.json after every mutation."""
    if st.session_state.owner:
        save_to_json(st.session_state.owner)


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image(
        "https://img.icons8.com/color/96/dog.png",
        width=64,
    )
    st.title("PawPal+")
    st.caption("Smart pet care scheduling")
    st.divider()

    # ── Owner ──────────────────────────────────────────────────────────
    st.header("Owner")
    owner_name_input = st.text_input(
        "Your name",
        value=st.session_state.owner.name if st.session_state.owner else "Jordan",
        key="owner_name_input",
    )
    if st.button("Set owner", use_container_width=True):
        if st.session_state.owner is None or st.session_state.owner.name != owner_name_input:
            # Preserve pets if only the name changed
            existing_pets = st.session_state.owner.pets if st.session_state.owner else []
            st.session_state.owner = Owner(owner_name_input)
            for p in existing_pets:
                st.session_state.owner.add_pet(p)
        _save()
        st.success(f"Owner: {owner_name_input}")

    if st.session_state.owner is None:
        st.info("Set an owner name above to get started.")
        st.stop()

    owner: Owner = st.session_state.owner

    # ── Add Pet ────────────────────────────────────────────────────────
    st.divider()
    st.header("Add a Pet")
    new_pet_name = st.text_input("Pet name", key="sidebar_pet_name")
    new_species = st.selectbox(
        "Species", ["dog", "cat", "rabbit", "bird", "hamster", "other"],
        key="sidebar_species",
    )
    if st.button("Add pet", use_container_width=True):
        if new_pet_name.strip():
            if owner.find_pet(new_pet_name.strip()):
                st.warning(f"'{new_pet_name}' already exists.")
            else:
                owner.add_pet(Pet(new_pet_name.strip(), new_species))
                _save()
                st.success(f"Added {new_pet_name}!")
        else:
            st.error("Enter a pet name first.")

    # ── Pet list ───────────────────────────────────────────────────────
    if owner.pets:
        st.divider()
        st.subheader("Your pets")
        species_icon = {
            "dog": "🐶", "cat": "🐱", "rabbit": "🐰",
            "bird": "🐦", "hamster": "🐹",
        }
        for pet in owner.pets:
            icon = species_icon.get(pet.species, "🐾")
            task_count = len(pet.get_tasks())
            st.markdown(f"{icon} **{pet.name}** ({pet.species}) — {task_count} task(s)")


# ── Helpers ────────────────────────────────────────────────────────────────────
owner: Owner = st.session_state.owner
scheduler = Scheduler(owner)


def render_task_card(pet: Pet, task: Task, show_pet: bool = True) -> None:
    """Render a single task as a coloured, emoji-annotated card."""
    css_cls = f"priority-{task.priority}" + (" task-done" if task.completed else "")
    emoji = task_emoji(task.description)
    status_icon = "✅" if task.completed else "⏳"
    pet_label = f" &nbsp;|&nbsp; 🐾 {pet.name}" if show_pet else ""
    badge = priority_badge(task.priority)
    st.markdown(
        f'<div class="{css_cls}">'
        f"{status_icon} <strong>{task.time}</strong> &nbsp; {emoji} {task.description}"
        f"&nbsp;&nbsp;<small>({task.duration_minutes} min &nbsp;|&nbsp; {badge}"
        f"&nbsp;|&nbsp; {task.frequency}{pet_label})</small>"
        f"</div>",
        unsafe_allow_html=True,
    )


# ── Main header ────────────────────────────────────────────────────────────────
st.title(f"🐾 PawPal+ &nbsp; <small style='font-size:0.55em;color:#888'>for {owner.name}</small>",
         )
st.caption(f"Today is {date.today().strftime('%A, %B %d %Y')}")

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_today, tab_add, tab_all, tab_insights = st.tabs(
    ["📅 Today's Schedule", "➕ Add Task", "📋 All Tasks", "💡 Insights"]
)

# ══════════════════════════════════════════════════════════════════════════════
# Tab 1 — Today's Schedule
# ══════════════════════════════════════════════════════════════════════════════
with tab_today:
    st.subheader("Today's Schedule")

    sort_mode = st.radio(
        "Sort by",
        ["⏰ Time", "🔴 Priority first"],
        horizontal=True,
        key="today_sort",
    )

    todays_tasks = scheduler.get_todays_schedule()

    if sort_mode == "🔴 Priority first":
        todays_tasks = scheduler.sort_by_priority_then_time(todays_tasks)

    # Conflict banner
    conflicts = scheduler.detect_conflicts(todays_tasks)
    if conflicts:
        st.error(f"**{len(conflicts)} scheduling conflict(s) detected**")
        for w in conflicts:
            st.markdown(
                f'<div class="conflict-box">⚠️ {w}</div>', unsafe_allow_html=True
            )

    if not todays_tasks:
        st.info("No tasks scheduled for today. Add some in the 'Add Task' tab.")
    else:
        for pet, task in todays_tasks:
            render_task_card(pet, task)

        st.divider()
        st.subheader("Mark a task complete")
        pending = [(pet, task) for pet, task in todays_tasks if not task.completed]
        if pending:
            labels = [
                f"{task_emoji(t.description)} {t.time} — {p.name}: {t.description}"
                for p, t in pending
            ]
            chosen_label = st.selectbox("Select task", labels, key="mark_complete_select")
            chosen_pet, chosen_task = pending[labels.index(chosen_label)]

            if st.button("✅ Mark complete", use_container_width=True):
                next_task = scheduler.mark_task_complete(chosen_pet, chosen_task)
                _save()
                st.success(f"'{chosen_task.description}' marked complete!")
                if next_task:
                    st.info(
                        f"🔁 Next occurrence: **{next_task.description}** "
                        f"on {next_task.due_date.strftime('%A, %B %d')}"
                    )
                st.rerun()
        else:
            st.success("🎉 All tasks for today are done!")

# ══════════════════════════════════════════════════════════════════════════════
# Tab 2 — Add Task
# ══════════════════════════════════════════════════════════════════════════════
with tab_add:
    st.subheader("Schedule a New Task")

    if not owner.pets:
        st.info("Add at least one pet in the sidebar first.")
    else:
        col_left, col_right = st.columns(2)

        with col_left:
            selected_pet_name = st.selectbox("Pet", [p.name for p in owner.pets], key="add_pet")
            task_desc = st.text_input("Task description", value="Morning walk", key="add_desc")
            duration = st.number_input(
                "Duration (minutes)", min_value=1, max_value=480, value=20, key="add_dur"
            )
            priority = st.selectbox("Priority", ["low", "medium", "high"], index=2, key="add_pri")

        with col_right:
            frequency = st.selectbox(
                "Frequency", ["one-time", "daily", "weekly"], key="add_freq"
            )
            due = st.date_input("Due date", value=date.today(), key="add_due")
            task_time = st.text_input("Time (HH:MM)", value="07:30", key="add_time")

            # ── Next available slot suggestion (Challenge 1) ──────────
            if st.button("💡 Suggest next free slot", use_container_width=True):
                suggested = scheduler.find_next_available_slot(int(duration))
                if suggested:
                    st.success(f"Next available slot today: **{suggested}**")
                    st.session_state["add_time"] = suggested
                else:
                    st.warning("No free slot found today between 07:00 and 22:00.")

        if st.button("➕ Add task", use_container_width=True, type="primary"):
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
                _save()
                st.success(
                    f"{task_emoji(task_desc)} **'{task_desc}'** added for "
                    f"**{selected_pet_name}** at {time_str}."
                )

                # Show conflict warning immediately
                conflicts = scheduler.detect_conflicts()
                for w in conflicts:
                    st.markdown(
                        f'<div class="conflict-box">⚠️ {w}</div>',
                        unsafe_allow_html=True,
                    )

# ══════════════════════════════════════════════════════════════════════════════
# Tab 3 — All Tasks
# ══════════════════════════════════════════════════════════════════════════════
with tab_all:
    st.subheader("All Tasks")

    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        pet_filter = st.selectbox(
            "Pet", ["All"] + [p.name for p in owner.pets], key="all_filter_pet"
        )
    with col_f2:
        status_filter = st.selectbox(
            "Status", ["All", "Pending", "Done"], key="all_filter_status"
        )
    with col_f3:
        sort_all = st.selectbox(
            "Sort", ["Time", "Priority first"], key="all_sort"
        )

    all_tasks = (
        scheduler.sort_by_priority_then_time()
        if sort_all == "Priority first"
        else scheduler.sort_by_time()
    )

    if pet_filter != "All":
        all_tasks = scheduler.filter_by_pet(pet_filter, all_tasks)
    if status_filter == "Pending":
        all_tasks = scheduler.filter_by_status(False, all_tasks)
    elif status_filter == "Done":
        all_tasks = scheduler.filter_by_status(True, all_tasks)

    if not all_tasks:
        st.info("No tasks match the current filters.")
    else:
        for pet, task in all_tasks:
            render_task_card(pet, task)

    # Conflict summary
    all_conflicts = scheduler.detect_conflicts()
    if all_conflicts:
        st.divider()
        st.subheader("Conflicts")
        for w in all_conflicts:
            st.markdown(
                f'<div class="conflict-box">⚠️ {w}</div>', unsafe_allow_html=True
            )

# ══════════════════════════════════════════════════════════════════════════════
# Tab 4 — Insights
# ══════════════════════════════════════════════════════════════════════════════
with tab_insights:
    st.subheader("Schedule Insights")

    all_pairs = scheduler.get_all_tasks()
    if not all_pairs:
        st.info("Add some tasks first to see insights.")
    else:
        total = len(all_pairs)
        done = sum(1 for _, t in all_pairs if t.completed)
        pending = total - done
        total_min = sum(t.duration_minutes for _, t in all_pairs if not t.completed)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total tasks", total)
        c2.metric("Pending", pending)
        c3.metric("Completed", done)
        c4.metric("Time remaining (min)", total_min)

        st.divider()

        # Priority breakdown
        st.subheader("Tasks by priority")
        for lvl in ["high", "medium", "low"]:
            count = sum(1 for _, t in all_pairs if t.priority == lvl and not t.completed)
            label = priority_badge(lvl)
            st.markdown(f"**{label}** — {count} pending task(s)")

        st.divider()

        # Next available slot finder
        st.subheader("💡 Find next free slot")
        slot_dur = st.number_input(
            "Task duration (minutes)", min_value=5, max_value=240, value=30,
            key="insight_dur",
        )
        if st.button("Find slot", key="insight_find"):
            slot = scheduler.find_next_available_slot(int(slot_dur))
            if slot:
                st.success(
                    f"Next available slot for a **{slot_dur}-minute** task: **{slot}**"
                )
            else:
                st.warning("No free slot found between 07:00 and 22:00 today.")

        st.divider()

        # Priority-sorted schedule preview
        st.subheader("Priority-first view (today)")
        todays_priority = scheduler.sort_by_priority_then_time(
            scheduler.get_todays_schedule()
        )
        if todays_priority:
            for pet, task in todays_priority:
                render_task_card(pet, task)
        else:
            st.info("No pending tasks for today.")
