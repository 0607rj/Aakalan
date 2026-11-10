"""Who is on the team (parameter sets v34+, formula staffing.v1, OPEN_QUESTIONS 229).

The work comes from the features (each block's task mix); this module only decides who does it.
Every role in `staffing.roles` is decided in order, from the work it would do (its own plus any
work handed to it by roles decided before it):

  joins  if a questionnaire answer requires it (required_when),
         or work_pd ≥ min_booking_pd (a booking's worth of work),
         or min_booking_pd × rate(role) ≤ work_pd × slowdown × rate(fallback)
            (booking the specialist for the minimum costs no more than handing the work over);
  else   the fallback does it: work_pd × slowdown is added to the fallback's work, decided later.

A role with no work is not on the team. The work is never dropped: a role left out hands all of
it on, priced at the person who does it, slowed by the slowdowns along the way. Pure: no trace,
no database; the callers record the decisions on the lines they change."""

from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from app.services.engine.money import ONE, ZERO
from app.services.engine.reference import Staffing, StaffRole

FORMULA_ID = "staffing.v1"


@dataclass(frozen=True)
class Decision:
    role: str
    work_pd: Decimal  # its own work plus work handed to it, before its own slowdown
    joins: bool
    reason: str


@dataclass(frozen=True)
class Team:
    staffing: Staffing
    decisions: dict[str, Decision] = field(default_factory=dict)

    def done_by(self, role: str) -> tuple[str, Decimal]:
        """(who does `role`'s work, the slowdown on it): down the fallbacks to a role that joins
        or is not decided at all (the developer, always on a team that builds anything)."""
        factor = ONE
        seen: set[str] = set()
        while role in self.decisions and not self.decisions[role].joins and role not in seen:
            seen.add(role)
            staff = self.staffing.roles[role]
            factor *= staff.slowdown
            role = staff.fallback
        return role, factor

    def notes(self, roles: set[str]) -> dict[str, dict[str, str]]:
        """For a line's inputs: each role left out, who does its work and why (read by the
        results page's "not booked" list)."""
        return {
            r: note(self.done_by(r)[0], self.decisions[r].work_pd,
                    self.staffing.roles[r].min_booking_pd, self.decisions[r].reason)
            for r in sorted(roles)
            if r in self.decisions
        }  # fmt: skip


def note(done_by: str, work_pd: Decimal, booking: Decimal, why: str) -> dict[str, str]:
    return {
        "done_by": done_by,
        "work_pd": f"{work_pd:.2f}",
        "min_booking_pd": f"{booking}",
        "why": why,
    }


def plain(role: str) -> str:
    return role.removeprefix("role.").replace("_", " ")


def choose(
    role: str,
    staff: StaffRole,
    work_pd: Decimal,
    rate: Callable[[str], Decimal],
    answer: Callable[[str], Any],
) -> tuple[bool, str]:
    """(joins, why) for one role with `work_pd` of work (see the module docstring)."""
    for key, values in staff.required_when.items():
        given = answer(key)
        if given in values:
            return True, f"needed: {key.replace('_', ' ')} is {given}"
    if work_pd >= staff.min_booking_pd:
        return True, f"{work_pd:.1f} person-days, at least a {staff.min_booking_pd} day booking"
    booked = staff.min_booking_pd * rate(role)
    shared = work_pd * staff.slowdown * rate(staff.fallback)
    if booked <= shared:
        return True, (
            f"{work_pd:.1f} person-days; booking the {plain(role)} for {staff.min_booking_pd}"
            f" days ({booked:.0f}) costs no more than the {plain(staff.fallback)} doing it"
            f" ({shared:.0f})"
        )
    return False, (
        f"only {work_pd:.1f} person-days, under a {staff.min_booking_pd} day booking: the"
        f" {plain(staff.fallback)} does it in {work_pd * staff.slowdown:.1f} ({shared:.0f},"
        f" against {booked:.0f} to book a {plain(role)})"
    )


def decide(
    staffing: Staffing,
    work: dict[str, Decimal],
    rate: Callable[[str], Decimal],
    answer: Callable[[str], Any],
) -> Team:
    """The team for the work by role (person-days before schedule compression)."""
    pools = dict(work)
    decisions: dict[str, Decision] = {}
    for role, staff in staffing.roles.items():
        pd = pools.get(role, ZERO)
        if pd <= ZERO:
            continue  # no work of this kind: not on the team
        joins, why = choose(role, staff, pd, rate, answer)
        decisions[role] = Decision(role=role, work_pd=pd, joins=joins, reason=why)
        if not joins:
            pools[staff.fallback] = pools.get(staff.fallback, ZERO) + pd * staff.slowdown
    return Team(staffing=staffing, decisions=decisions)
