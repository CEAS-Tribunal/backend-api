from collections import defaultdict
from dataclasses import dataclass, field

from ortools.sat.python import cp_model

from .models import JudgeModel, JudgingTimeslots, ProjectCategories, StudentModel

SLOT_KEYS = [key for key, _ in JudgingTimeslots]
CATEGORY_LABELS = dict(ProjectCategories)

_STATUS_NAMES = {
    cp_model.OPTIMAL: "optimal",
    cp_model.FEASIBLE: "feasible",
    cp_model.INFEASIBLE: "infeasible",
    cp_model.MODEL_INVALID: "model_invalid",
    cp_model.UNKNOWN: "unknown",
}


@dataclass
class PlannedAssignment:
    judge: JudgeModel
    student: StudentModel
    timeslot: str


@dataclass
class AssignmentResult:
    status: str
    assignments: list[PlannedAssignment] = field(default_factory=list)
    shortfalls: list[dict] = field(default_factory=list)


def generate_assignments(min_judges=3, max_judges=None, time_limit_s=15.0):
    judges = list(JudgeModel.objects.filter(is_backup_judge=False))
    teams = list(StudentModel.objects.all())
    return solve_assignments(judges, teams, min_judges, max_judges, time_limit_s)


def solve_assignments(judges, teams, min_judges=3, max_judges=None, time_limit_s=15.0):
    """Schedule judges onto teams with CP-SAT.

    Priorities, highest first: every team reaches `min_judges`; a team's judges
    are not in back-to-back slots; teams get extra judges up to `max_judges`
    (defaults to `min_judges`, i.e. no extras); load is spread evenly across
    judges relative to their `number_of_projects`.
    """
    max_judges = min_judges if max_judges is None else max(max_judges, min_judges)
    slot_index = {key: i for i, key in enumerate(SLOT_KEYS)}
    num_slots = len(SLOT_KEYS)

    model = cp_model.CpModel()
    x = {}
    by_judge = defaultdict(list)
    by_team = defaultdict(list)
    by_judge_slot = defaultdict(list)
    by_team_slot = defaultdict(list)
    by_judge_team = defaultdict(list)

    for j, judge in enumerate(judges):
        categories = set(judge.judging_category)
        slots = [slot_index[s] for s in judge.judging_timeslot if s in slot_index]
        for t, team in enumerate(teams):
            if team.team_category not in categories:
                continue
            for s in slots:
                var = model.NewBoolVar(f"x_{j}_{t}_{s}")
                x[j, t, s] = var
                by_judge[j].append(var)
                by_team[t].append(var)
                by_judge_slot[j, s].append(var)
                by_team_slot[t, s].append(var)
                by_judge_team[j, t].append(var)

    for group in (by_judge_slot, by_team_slot, by_judge_team):
        for vars_ in group.values():
            if len(vars_) > 1:
                model.AddAtMostOne(vars_)

    capacities = {}
    for j, judge in enumerate(judges):
        if not by_judge[j]:
            continue
        capacities[j] = min(judge.number_of_projects, len(set(judge.judging_timeslot)))
        model.Add(sum(by_judge[j]) <= capacities[j])

    team_counts = {}
    shorts = []
    extras = []
    for t in range(len(teams)):
        count = sum(by_team[t]) if by_team[t] else 0
        team_counts[t] = count
        if by_team[t]:
            model.Add(count <= max_judges)
        short = model.NewIntVar(0, min_judges, f"short_{t}")
        model.Add(short >= min_judges - count)
        shorts.append(short)
        if max_judges > min_judges and by_team[t]:
            extra = model.NewIntVar(0, max_judges - min_judges, f"extra_{t}")
            model.Add(extra <= count - min_judges + short)
            extras.append(extra)

    adjacencies = []
    for t in range(len(teams)):
        for s in range(num_slots - 1):
            here, after = by_team_slot.get((t, s)), by_team_slot.get((t, s + 1))
            if not here or not after:
                continue
            adj = model.NewBoolVar(f"adj_{t}_{s}")
            model.Add(adj >= sum(here) + sum(after) - 1)
            adjacencies.append(adj)

    max_load_pct = model.NewIntVar(0, 100, "max_load_pct")
    for j, cap in capacities.items():
        model.Add(100 * sum(by_judge[j]) <= max_load_pct * cap)

    # Lexicographic weights: each tier outweighs the full range of every tier below it.
    w_balance = 1
    w_extra = w_balance * 100 + 1
    w_adjacency = w_extra * (max_judges - min_judges) * len(teams) + w_balance * 100 + 1
    w_short = w_adjacency * len(adjacencies) + w_extra * (max_judges - min_judges) * len(teams) + w_balance * 100 + 1
    model.Minimize(
        w_short * sum(shorts)
        + w_adjacency * sum(adjacencies)
        - w_extra * sum(extras)
        + w_balance * max_load_pct
    )

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_s
    solver.parameters.num_workers = 8
    status = solver.Solve(model)
    result = AssignmentResult(status=_STATUS_NAMES.get(status, "unknown"))
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return result

    assigned_counts = defaultdict(int)
    for (j, t, s), var in x.items():
        if solver.Value(var):
            result.assignments.append(PlannedAssignment(judges[j], teams[t], SLOT_KEYS[s]))
            assigned_counts[t] += 1

    eligible_by_category = defaultdict(int)
    for judge in judges:
        if judge.judging_timeslot:
            for category in set(judge.judging_category):
                eligible_by_category[category] += 1

    for t, team in enumerate(teams):
        count = assigned_counts[t]
        if count >= min_judges:
            continue
        eligible = eligible_by_category[team.team_category]
        label = CATEGORY_LABELS.get(team.team_category, team.team_category)
        if eligible < min_judges:
            reason = f"Only {eligible} non-backup judge(s) cover {label}."
        else:
            reason = f"Not enough open judge timeslots in {label}."
        result.shortfalls.append({
            "student_id": team.id,
            "team_name": team.team_name,
            "booth_number": team.booth_number,
            "team_category": team.team_category,
            "assigned": count,
            "required": min_judges,
            "reason": reason,
        })

    result.assignments.sort(key=lambda a: (a.student.team_name, slot_index[a.timeslot]))
    return result
