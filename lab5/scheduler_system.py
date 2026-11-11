"""Conference room and equipment scheduler."""
import itertools
import json
from datetime import datetime

# Global state
reservations = {}
equipment_pool = {"projector": 2, "microphone": 4, "webcam": 1}
conflicts = []
_RESERVATION_IDS = itertools.count(1)


def schedule_room(room_id, time_slot, equipment_list=None):
    """Book a room for a time slot and return the reservation id."""
    if equipment_list is None:
        equipment_list = []
    for reservation in reservations.values():
        if (reservation["room"] == room_id
                and reservation["slot"] == time_slot):
            conflicts.append(f"{room_id} double-booked at {time_slot}")
    for item in equipment_list:
        equipment_pool[item] -= 1
    reservation_id = next(_RESERVATION_IDS)
    reservations[reservation_id] = {
        "room": room_id,
        "slot": time_slot,
        "equipment": equipment_list,
    }
    return reservation_id


def cancel_reservation(reservation_id):
    """Cancel a reservation and return its equipment to the pool."""
    reservation = reservations.pop(reservation_id, None)
    if reservation is None:
        return False
    for item in reservation["equipment"]:
        equipment_pool[item] += 1
    return True


def slot_hours(time_slot):
    """Return the length in hours of a slot like '09-11'."""
    start, end = time_slot.split("-")
    return int(end) - int(start)


def export_schedule(file="schedule.json"):
    """Write all reservations to a JSON file."""
    with open(file, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(reservations))


def log_conflicts(file="conflicts.log"):
    """Append conflicts to a log file and print the log."""
    with open(file, "a", encoding="utf-8") as handle:
        for conflict in conflicts:
            handle.write(f"{datetime.now()} {conflict}\n")
    with open(file, encoding="utf-8") as handle:
        print(handle.read())


def main():
    """Run the demo bookings."""
    schedule_room("Board-1", "09-11")
    schedule_room("Board-1", "09-11")
    room_b = schedule_room("Huddle-3", "14-12")
    schedule_room("Huddle-3", 1530)
    print("Slot length for b:", slot_hours(reservations[room_b]["slot"]))
    cancel_reservation(77)
    slot = input("Slot for Board-2, like 10-12 (Enter for 10-12): ")
    slot = slot or "10-12"
    schedule_room("Board-2", slot, ["projector", "webcam"])
    export_schedule()
    log_conflicts()
    print("Equipment left:", equipment_pool)
    print("Reservations:", reservations)


if __name__ == "__main__":
    main()
