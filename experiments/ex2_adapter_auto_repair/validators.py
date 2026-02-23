"""
Property-based validators for Ex2 tool outputs.

Each validator takes (tool_output: dict, bop_data: dict, tool_input: dict)
and returns a ValidationResult with pass/fail and details.
"""
import math
from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    """Result of property-based validation."""
    passed: bool
    checks_total: int = 0
    checks_passed: int = 0
    errors: list = field(default_factory=list)

    @property
    def score(self) -> float:
        if self.checks_total == 0:
            return 0.0
        return self.checks_passed / self.checks_total

    def add_check(self, name: str, passed: bool, detail: str = ""):
        self.checks_total += 1
        if passed:
            self.checks_passed += 1
        else:
            self.passed = False
            self.errors.append(f"[FAIL] {name}: {detail}")

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "checks_total": self.checks_total,
            "checks_passed": self.checks_passed,
            "score": round(self.score, 4),
            "errors": self.errors,
        }


# ============================================================
# Helper
# ============================================================

def _approx(a, b, tol=0.01):
    """Check if two floats are approximately equal."""
    if abs(b) < 1e-9:
        return abs(a) < tol
    return abs(a - b) / max(abs(a), abs(b)) < tol


def _get_bop_process_details(bop: dict) -> list:
    """Extract process_details from BOP (flat format)."""
    return bop.get("process_details", [])


def _get_bop_processes(bop: dict) -> list:
    """Extract processes from BOP."""
    return bop.get("processes", [])


# ============================================================
# 1. bottleneck_analyzer
# ============================================================

def validate_bottleneck_analyzer(output: dict, bop: dict, tool_input: dict) -> ValidationResult:
    r = ValidationResult(passed=True)

    # --- Check required fields exist ---
    required = ["bottleneck_process_id", "bottleneck_cycle_time_sec",
                "effective_cycle_time_sec", "current_max_uph",
                "is_target_achievable", "process_summary"]
    for f in required:
        r.add_check(f"field_exists:{f}", f in output, f"Missing field '{f}'")
    if not r.passed:
        return r

    # --- Recompute from BOP and verify ---
    details = _get_bop_process_details(bop)
    if not details:
        r.add_check("bop_has_details", False, "No process_details in BOP")
        return r

    # Group by process_id, compute effective cycle times
    groups = {}
    for d in details:
        pid = d.get("process_id", "")
        ct = d.get("cycle_time_sec", 0)
        groups.setdefault(pid, []).append(ct)

    effective_times = {}
    for pid, cts in groups.items():
        effective_times[pid] = max(cts) / len(cts)

    # Bottleneck = max effective time
    expected_bn = max(effective_times, key=effective_times.get)
    expected_eff = effective_times[expected_bn]

    r.add_check(
        "bottleneck_is_max",
        output["bottleneck_process_id"] == expected_bn,
        f"Expected bottleneck={expected_bn}, got={output['bottleneck_process_id']}"
    )
    r.add_check(
        "effective_cycle_time",
        _approx(output["effective_cycle_time_sec"], expected_eff),
        f"Expected {expected_eff:.2f}, got {output['effective_cycle_time_sec']:.2f}"
    )

    # UPH = 3600 / effective_cycle_time
    expected_uph = 3600.0 / expected_eff if expected_eff > 0 else 0
    r.add_check(
        "uph_calculation",
        _approx(output["current_max_uph"], expected_uph),
        f"Expected UPH={expected_uph:.2f}, got {output['current_max_uph']:.2f}"
    )

    # target_achievable consistency
    target = output.get("target_uph", tool_input.get("target_uph", 0))
    expected_achievable = expected_uph >= target
    r.add_check(
        "target_achievable_consistent",
        output["is_target_achievable"] == expected_achievable,
        f"Expected achievable={expected_achievable}, got {output['is_target_achievable']}"
    )

    # process_summary count matches unique processes
    r.add_check(
        "summary_count",
        len(output.get("process_summary", [])) == len(groups),
        f"Expected {len(groups)} processes in summary, got {len(output.get('process_summary', []))}"
    )

    return r


# ============================================================
# 2. line_balance_calculator
# ============================================================

def validate_line_balance_calculator(output: dict, bop: dict, tool_input: dict) -> ValidationResult:
    r = ValidationResult(passed=True)

    required = ["line_balance_rate", "takt_time_sec", "process_times",
                "total_effective_time_sec", "num_processes"]
    for f in required:
        r.add_check(f"field_exists:{f}", f in output, f"Missing field '{f}'")
    if not r.passed:
        return r

    target_uph = output.get("target_uph", tool_input.get("target_uph", 60))
    expected_takt = 3600.0 / target_uph if target_uph > 0 else 0

    r.add_check(
        "takt_time",
        _approx(output["takt_time_sec"], expected_takt),
        f"Expected takt={expected_takt:.2f}, got {output['takt_time_sec']:.2f}"
    )

    # Recompute line balance from BOP
    details = _get_bop_process_details(bop)
    groups = {}
    for d in details:
        pid = d.get("process_id", "")
        ct = d.get("cycle_time_sec", 0)
        groups.setdefault(pid, []).append(ct)

    eff_times = [max(cts) / len(cts) for cts in groups.values()]
    if eff_times:
        expected_balance = sum(eff_times) / (len(eff_times) * max(eff_times)) * 100
        r.add_check(
            "balance_rate",
            _approx(output["line_balance_rate"], expected_balance),
            f"Expected balance={expected_balance:.2f}%, got {output['line_balance_rate']:.2f}%"
        )

        r.add_check(
            "balance_rate_range",
            0 <= output["line_balance_rate"] <= 100,
            f"Balance rate {output['line_balance_rate']:.2f} outside [0, 100]"
        )

    # total_effective_time should equal sum
    r.add_check(
        "total_effective_time",
        _approx(output["total_effective_time_sec"], sum(eff_times)),
        f"Expected sum={sum(eff_times):.2f}, got {output['total_effective_time_sec']:.2f}"
    )

    # num_processes matches
    r.add_check(
        "num_processes",
        output["num_processes"] == len(groups),
        f"Expected {len(groups)}, got {output['num_processes']}"
    )

    return r


# ============================================================
# 3. equipment_utilization
# ============================================================

def validate_equipment_utilization(output: dict, bop: dict, tool_input: dict) -> ValidationResult:
    r = ValidationResult(passed=True)

    required = ["takt_time_sec", "equipment_utilization", "overall_utilization_pct"]
    for f in required:
        r.add_check(f"field_exists:{f}", f in output, f"Missing field '{f}'")
    if not r.passed:
        return r

    # takt_time consistency
    target_uph = output.get("target_uph", tool_input.get("target_uph", 60))
    if target_uph > 0:
        expected_takt = 3600.0 / target_uph
        r.add_check(
            "takt_time",
            _approx(output["takt_time_sec"], expected_takt),
            f"Expected takt={expected_takt:.2f}, got {output['takt_time_sec']:.2f}"
        )

    # overall_utilization = average of individual utilizations
    utils = output.get("equipment_utilization", [])
    if utils:
        util_values = [e.get("utilization_pct", 0) for e in utils]
        expected_avg = sum(util_values) / len(util_values)
        r.add_check(
            "overall_util_is_average",
            _approx(output["overall_utilization_pct"], expected_avg),
            f"Expected avg={expected_avg:.2f}, got {output['overall_utilization_pct']:.2f}"
        )

    # Utilization values are non-negative
    for e in utils:
        r.add_check(
            f"util_nonneg:{e.get('equipment_id', '?')}",
            e.get("utilization_pct", 0) >= 0,
            f"Negative utilization {e.get('utilization_pct')} for {e.get('equipment_id')}"
        )

    # Status consistency
    for e in utils:
        u = e.get("utilization_pct", 0)
        status = e.get("status", "")
        if u > 100:
            r.add_check(f"status_overloaded:{e.get('equipment_id')}", status == "overloaded",
                       f"util={u:.1f}% but status='{status}', expected 'overloaded'")
        elif u < 50:
            r.add_check(f"status_underutil:{e.get('equipment_id')}", status == "underutilized",
                       f"util={u:.1f}% but status='{status}', expected 'underutilized'")

    # underutilized/overloaded lists should match
    under = output.get("underutilized", [])
    over = output.get("overloaded", [])
    under_ids = {e.get("equipment_id") for e in under}
    over_ids = {e.get("equipment_id") for e in over}

    for e in utils:
        eid = e.get("equipment_id")
        u = e.get("utilization_pct", 50)
        if u < 50:
            r.add_check(f"in_underutilized:{eid}", eid in under_ids,
                       f"util={u:.1f}% but not in underutilized list")
        if u > 100:
            r.add_check(f"in_overloaded:{eid}", eid in over_ids,
                       f"util={u:.1f}% but not in overloaded list")

    return r


# ============================================================
# 4. process_distance_analyzer
# ============================================================

def validate_process_distance_analyzer(output: dict, bop: dict, tool_input: dict) -> ValidationResult:
    r = ValidationResult(passed=True)

    required = ["distances", "total_flow_distance_m", "avg_distance_m",
                "max_distance_pair", "min_distance_pair", "num_pairs"]
    for f in required:
        r.add_check(f"field_exists:{f}", f in output, f"Missing field '{f}'")
    if not r.passed:
        return r

    distances_list = output.get("distances", [])

    # total = sum of individual distances
    if distances_list:
        dist_values = [d.get("distance_m", 0) for d in distances_list]
        expected_total = sum(dist_values)
        r.add_check(
            "total_distance",
            _approx(output["total_flow_distance_m"], expected_total),
            f"Expected total={expected_total:.2f}, got {output['total_flow_distance_m']:.2f}"
        )

        # avg = total / count
        expected_avg = expected_total / len(dist_values) if dist_values else 0
        r.add_check(
            "avg_distance",
            _approx(output["avg_distance_m"], expected_avg),
            f"Expected avg={expected_avg:.2f}, got {output['avg_distance_m']:.2f}"
        )

        # num_pairs matches
        r.add_check(
            "num_pairs",
            output["num_pairs"] == len(dist_values),
            f"Expected {len(dist_values)}, got {output['num_pairs']}"
        )

        # max/min consistency
        max_d = max(dist_values)
        min_d = min(dist_values)
        r.add_check(
            "max_distance_value",
            _approx(output["max_distance_pair"].get("distance_m", 0), max_d),
            f"Expected max={max_d:.2f}, got {output['max_distance_pair'].get('distance_m', 0):.2f}"
        )
        r.add_check(
            "min_distance_value",
            _approx(output["min_distance_pair"].get("distance_m", 0), min_d),
            f"Expected min={min_d:.2f}, got {output['min_distance_pair'].get('distance_m', 0):.2f}"
        )

    # All distances should be non-negative
    for d in distances_list:
        r.add_check(
            f"dist_nonneg:{d.get('from_id')}->{d.get('to_id')}",
            d.get("distance_m", 0) >= 0,
            f"Negative distance {d.get('distance_m')}"
        )

    # Verify a sample distance with Euclidean formula from BOP
    processes = _get_bop_processes(bop)
    proc_details = _get_bop_process_details(bop)
    # Build location map from process_details (location field)
    loc_map = {}
    for pd in proc_details:
        pid = pd.get("process_id", "")
        loc = pd.get("location", {})
        if loc and pid not in loc_map:
            loc_map[pid] = loc

    if distances_list and loc_map:
        sample = distances_list[0]
        fid = sample.get("from_id", "")
        tid = sample.get("to_id", "")
        if fid in loc_map and tid in loc_map:
            fl = loc_map[fid]
            tl = loc_map[tid]
            dx = tl.get("x", 0) - fl.get("x", 0)
            dy = tl.get("y", 0) - fl.get("y", 0)
            dz = tl.get("z", 0) - fl.get("z", 0)
            expected_dist = math.sqrt(dx*dx + dy*dy + dz*dz)
            r.add_check(
                "sample_euclidean",
                _approx(sample.get("distance_m", 0), expected_dist, tol=0.05),
                f"Euclidean({fid}->{tid})={expected_dist:.2f}, output={sample.get('distance_m', 0):.2f}"
            )

    return r


# ============================================================
# 5. worker_skill_matcher
# ============================================================

MATCH_SCORES = {
    ("Senior", "High"): 100, ("Senior", "Medium"): 80, ("Senior", "Low"): 60,
    ("Mid", "High"): 70, ("Mid", "Medium"): 100, ("Mid", "Low"): 80,
    ("Junior", "High"): 40, ("Junior", "Medium"): 70, ("Junior", "Low"): 100,
}


def validate_worker_skill_matcher(output: dict, bop: dict, tool_input: dict) -> ValidationResult:
    r = ValidationResult(passed=True)

    required = ["matches", "overall_match_score", "mismatches",
                "skill_distribution", "num_evaluated"]
    for f in required:
        r.add_check(f"field_exists:{f}", f in output, f"Missing field '{f}'")
    if not r.passed:
        return r

    matches = output.get("matches", [])
    mismatches = output.get("mismatches", [])

    # overall = average of match scores
    if matches:
        scores = [m.get("match_score", 0) for m in matches]
        expected_avg = sum(scores) / len(scores)
        r.add_check(
            "overall_score",
            _approx(output["overall_match_score"], expected_avg),
            f"Expected avg={expected_avg:.2f}, got {output['overall_match_score']:.2f}"
        )

    # num_evaluated matches
    r.add_check(
        "num_evaluated",
        output["num_evaluated"] == len(matches),
        f"Expected {len(matches)}, got {output['num_evaluated']}"
    )

    # mismatches subset: all should have score < 70
    for mm in mismatches:
        r.add_check(
            f"mismatch_score:{mm.get('worker_id', '?')}",
            mm.get("match_score", 100) < 70,
            f"Mismatch has score {mm.get('match_score')} >= 70"
        )

    # Verify match scores against lookup table
    for m in matches:
        skill = m.get("skill_level", "")
        complexity = m.get("complexity_level", "")
        expected_score = MATCH_SCORES.get((skill, complexity))
        if expected_score is not None:
            r.add_check(
                f"score_lookup:{m.get('worker_id', '?')}",
                m.get("match_score", 0) == expected_score,
                f"{skill}/{complexity} expected {expected_score}, got {m.get('match_score')}"
            )

    # skill_distribution should sum to num_evaluated
    dist = output.get("skill_distribution", {})
    if dist:
        dist_sum = sum(dist.values())
        r.add_check(
            "skill_dist_sum",
            dist_sum == len(matches),
            f"Skill distribution sum={dist_sum}, matches count={len(matches)}"
        )

    return r


# ============================================================
# 6. material_flow_analyzer
# ============================================================

def validate_material_flow_analyzer(output: dict, bop: dict, tool_input: dict) -> ValidationResult:
    r = ValidationResult(passed=True)

    required = ["material_flows", "flow_paths", "summary"]
    for f in required:
        r.add_check(f"field_exists:{f}", f in output, f"Missing field '{f}'")
    if not r.passed:
        return r

    flows = output.get("material_flows", [])
    summary = output.get("summary", {})

    # total_materials count
    r.add_check(
        "total_materials_count",
        summary.get("total_materials", 0) == len(flows),
        f"Summary says {summary.get('total_materials')}, actual flows count={len(flows)}"
    )

    # total_quantity_by_unit consistency
    qty_by_unit = {}
    for f_item in flows:
        unit = f_item.get("unit", "ea")
        qty = f_item.get("total_quantity", 0)
        qty_by_unit[unit] = qty_by_unit.get(unit, 0) + qty

    summary_qty = summary.get("total_quantity_by_unit", {})
    for unit, qty in qty_by_unit.items():
        r.add_check(
            f"qty_by_unit:{unit}",
            _approx(summary_qty.get(unit, 0), qty),
            f"Expected {unit}={qty}, summary says {summary_qty.get(unit, 0)}"
        )

    # All quantities should be positive
    for f_item in flows:
        r.add_check(
            f"qty_positive:{f_item.get('material_id', '?')}",
            f_item.get("total_quantity", 0) > 0,
            f"Material {f_item.get('material_id')} has quantity={f_item.get('total_quantity')}"
        )

    # Each material's used_in_processes should be non-empty
    for f_item in flows:
        procs = f_item.get("used_in_processes", [])
        r.add_check(
            f"used_in_nonempty:{f_item.get('material_id', '?')}",
            len(procs) > 0,
            f"Material {f_item.get('material_id')} used in no processes"
        )

    # flow_paths: from/to should reference real processes
    bop_procs = {p.get("process_id") for p in _get_bop_processes(bop)}
    for fp in output.get("flow_paths", []):
        from_p = fp.get("from_process", "")
        to_p = fp.get("to_process", "")
        if bop_procs:
            r.add_check(
                f"flow_from_valid:{from_p}",
                from_p in bop_procs,
                f"from_process '{from_p}' not in BOP processes"
            )
            r.add_check(
                f"flow_to_valid:{to_p}",
                to_p in bop_procs,
                f"to_process '{to_p}' not in BOP processes"
            )

    return r


# ============================================================
# 7. safety_zone_checker
# ============================================================

def validate_safety_zone_checker(output: dict, bop: dict, tool_input: dict) -> ValidationResult:
    r = ValidationResult(passed=True)

    required = ["violations", "safe_processes", "violation_count", "all_safe"]
    for f in required:
        r.add_check(f"field_exists:{f}", f in output, f"Missing field '{f}'")
    if not r.passed:
        return r

    violations = output.get("violations", [])
    safe_procs = output.get("safe_processes", [])
    violation_count = output.get("violation_count", -1)
    all_safe = output.get("all_safe", None)

    # violation_count matches
    r.add_check(
        "violation_count",
        violation_count == len(violations),
        f"violation_count={violation_count}, actual violations={len(violations)}"
    )

    # all_safe consistency
    r.add_check(
        "all_safe_consistent",
        all_safe == (len(violations) == 0),
        f"all_safe={all_safe} but violations count={len(violations)}"
    )

    # All violations should have is_violation=True
    for v in violations:
        r.add_check(
            f"is_violation:{v.get('process_id', '?')}-{v.get('obstacle_id', '?')}",
            v.get("is_violation", False) is True,
            "Entry in violations list has is_violation=False"
        )

    # Violation distances should be less than required_distance
    for v in violations:
        dist = v.get("distance", float('inf'))
        req = v.get("required_distance", 0)
        r.add_check(
            f"dist_lt_required:{v.get('process_id', '?')}-{v.get('obstacle_id', '?')}",
            dist < req,
            f"distance={dist:.2f} >= required={req:.2f}"
        )

    # safe_processes should not appear in violations
    violated_pids = {v.get("process_id") for v in violations}
    for sp in safe_procs:
        r.add_check(
            f"safe_not_violated:{sp}",
            sp not in violated_pids,
            f"Process {sp} in safe_processes but also has violations"
        )

    # Verify a sample distance with AABB calculation from BOP
    obstacles = bop.get("obstacles", [])
    proc_details = _get_bop_process_details(bop)
    if violations and obstacles and proc_details:
        v = violations[0]
        pid = v.get("process_id", "")
        oid = v.get("obstacle_id", "")

        proc = next((p for p in proc_details if p.get("process_id") == pid), None)
        obs = next((o for o in obstacles if o.get("obstacle_id") == oid), None)

        if proc and obs:
            ploc = proc.get("location", {})
            psz = proc.get("computed_size", proc.get("size", {}))
            opos = obs.get("position", obs.get("location", {}))
            osz = obs.get("size", {})

            if ploc and opos and psz and osz:
                # AABB gap calculation
                def _aabb_dist(p_min, p_size, o_min, o_size):
                    p_max = p_min + p_size
                    o_max = o_min + o_size
                    gap = max(0, max(p_min - o_max, o_min - p_max))
                    return gap

                gx = _aabb_dist(ploc.get("x", 0), psz.get("width", 0),
                               opos.get("x", 0), osz.get("width", 0))
                gy = _aabb_dist(ploc.get("y", 0), psz.get("height", 0),
                               opos.get("y", 0), osz.get("height", 0))
                gz = _aabb_dist(ploc.get("z", 0), psz.get("depth", 0),
                               opos.get("z", 0), osz.get("depth", 0))
                expected_dist = math.sqrt(gx*gx + gy*gy + gz*gz)

                r.add_check(
                    "sample_aabb_distance",
                    _approx(v.get("distance", 0), expected_dist, tol=0.1),
                    f"AABB dist({pid},{oid})={expected_dist:.2f}, output={v.get('distance', 0):.2f}"
                )

    return r


# ============================================================
# 8. takt_time_optimizer
# ============================================================

def validate_takt_time_optimizer(output: dict, bop: dict, tool_input: dict) -> ValidationResult:
    r = ValidationResult(passed=True)

    required = ["optimized_processes", "achieved_uph", "target_uph",
                "improvement_pct", "bottleneck_after"]
    for f in required:
        r.add_check(f"field_exists:{f}", f in output, f"Missing field '{f}'")
    if not r.passed:
        return r

    procs = output.get("optimized_processes", [])
    if not procs:
        r.add_check("has_processes", False, "No optimized_processes")
        return r

    # achieved_uph = 3600 / max(new_effective_time)
    new_effs = []
    for p in procs:
        nef = p.get("new_effective_time", p.get("new_effective_time_sec", 0))
        new_effs.append(nef)

    if new_effs and max(new_effs) > 0:
        expected_uph = 3600.0 / max(new_effs)
        r.add_check(
            "achieved_uph",
            _approx(output["achieved_uph"], expected_uph),
            f"Expected UPH={expected_uph:.2f}, got {output['achieved_uph']:.2f}"
        )

    # bottleneck_after should be the process with max new_effective_time
    max_eff = max(new_effs)
    max_idx = new_effs.index(max_eff)
    expected_bn = procs[max_idx].get("process_id", "")
    r.add_check(
        "bottleneck_after",
        output["bottleneck_after"] == expected_bn,
        f"Expected bottleneck={expected_bn}, got {output['bottleneck_after']}"
    )

    # new_effective_time = cycle_time / recommended_parallel
    for p in procs:
        rec = p.get("recommended_parallel", 1)
        # Try to find cycle_time - might be stored differently
        ct = p.get("original_effective_time", 0) * p.get("original_parallel", 1)
        if ct > 0 and rec > 0:
            expected_nef = ct / rec
            actual_nef = p.get("new_effective_time", p.get("new_effective_time_sec", 0))
            r.add_check(
                f"eff_time:{p.get('process_id', '?')}",
                _approx(actual_nef, expected_nef),
                f"cycle_time/parallel = {ct:.2f}/{rec} = {expected_nef:.2f}, got {actual_nef:.2f}"
            )

    # recommended_parallel >= original_parallel (optimizer should not reduce)
    for p in procs:
        orig = p.get("original_parallel", 1)
        rec = p.get("recommended_parallel", 1)
        r.add_check(
            f"parallel_not_reduced:{p.get('process_id', '?')}",
            rec >= orig,
            f"Reduced from {orig} to {rec}"
        )

    # improvement_pct should be non-negative
    r.add_check(
        "improvement_nonneg",
        output["improvement_pct"] >= 0,
        f"Negative improvement {output['improvement_pct']:.2f}%"
    )

    return r


# ============================================================
# 9. energy_estimator
# ============================================================

def validate_energy_estimator(output: dict, bop: dict, tool_input: dict) -> ValidationResult:
    r = ValidationResult(passed=True)

    required = ["process_energy", "total_energy_kwh", "total_cost"]
    for f in required:
        r.add_check(f"field_exists:{f}", f in output, f"Missing field '{f}'")
    if not r.passed:
        return r

    procs = output.get("process_energy", [])
    cost_per_kwh = output.get("cost_per_kwh", tool_input.get("cost_per_kwh", 0.1))

    # total_energy = sum of process energies
    if procs:
        proc_energies = [p.get("energy_total_kwh", 0) for p in procs]
        expected_total = sum(proc_energies)
        r.add_check(
            "total_energy_sum",
            _approx(output["total_energy_kwh"], expected_total),
            f"Sum={expected_total:.4f}, total={output['total_energy_kwh']:.4f}"
        )

    # total_cost = total_energy * cost_per_kwh
    if cost_per_kwh > 0:
        expected_cost = output["total_energy_kwh"] * cost_per_kwh
        r.add_check(
            "total_cost",
            _approx(output["total_cost"], expected_cost),
            f"Expected cost={expected_cost:.4f}, got {output['total_cost']:.4f}"
        )

    # Per-process: energy_per_unit * volume / parallel = total (approximately)
    for p in procs:
        energy_per_unit = p.get("energy_per_unit_kwh", 0)
        total_e = p.get("energy_total_kwh", 0)
        parallel = p.get("parallel_count", 1)
        volume = output.get("production_volume", tool_input.get("production_volume", 1000))

        if energy_per_unit > 0 and volume > 0 and parallel > 0:
            expected_total_e = energy_per_unit * volume / parallel
            r.add_check(
                f"energy_formula:{p.get('process_id', '?')}",
                _approx(total_e, expected_total_e),
                f"per_unit*vol/parallel = {expected_total_e:.4f}, got {total_e:.4f}"
            )

    # cost_estimate = energy_total * cost_per_kwh
    for p in procs:
        total_e = p.get("energy_total_kwh", 0)
        cost_est = p.get("cost_estimate", 0)
        expected_c = total_e * cost_per_kwh
        r.add_check(
            f"cost_est:{p.get('process_id', '?')}",
            _approx(cost_est, expected_c),
            f"energy*rate = {expected_c:.4f}, got {cost_est:.4f}"
        )

    # All energies should be non-negative
    for p in procs:
        r.add_check(
            f"energy_nonneg:{p.get('process_id', '?')}",
            p.get("energy_total_kwh", 0) >= 0,
            f"Negative energy {p.get('energy_total_kwh')}"
        )

    # energy_by_type should sum to total
    energy_by_type = output.get("energy_by_type", {})
    if energy_by_type:
        type_sum = sum(energy_by_type.values())
        r.add_check(
            "energy_by_type_sum",
            _approx(type_sum, output["total_energy_kwh"]),
            f"Type sum={type_sum:.4f}, total={output['total_energy_kwh']:.4f}"
        )

    return r


# ============================================================
# 10. layout_compactor
# ============================================================

def validate_layout_compactor(output: dict, bop: dict, tool_input: dict) -> ValidationResult:
    r = ValidationResult(passed=True)

    required = ["compacted_nodes", "total_original_span", "total_compacted_span",
                "reduction_pct"]
    for f in required:
        r.add_check(f"field_exists:{f}", f in output, f"Missing field '{f}'")
    if not r.passed:
        return r

    nodes = output.get("compacted_nodes", [])
    if not nodes:
        r.add_check("has_nodes", False, "No compacted_nodes")
        return r

    orig_span = output["total_original_span"]
    comp_span = output["total_compacted_span"]
    reduction = output["reduction_pct"]

    # reduction_pct = (orig - comp) / orig * 100
    if orig_span > 0:
        expected_red = (orig_span - comp_span) / orig_span * 100
        r.add_check(
            "reduction_pct",
            _approx(reduction, expected_red),
            f"Expected {expected_red:.2f}%, got {reduction:.2f}%"
        )

    # compacted_span <= original_span (compaction should not expand)
    r.add_check(
        "span_not_expanded",
        comp_span <= orig_span + 0.01,
        f"Compacted span {comp_span:.2f} > original {orig_span:.2f}"
    )

    # reduction_pct should be in [0, 100]
    r.add_check(
        "reduction_range",
        -0.01 <= reduction <= 100.01,
        f"Reduction {reduction:.2f}% outside [0, 100]"
    )

    # No overlapping nodes (check primary axis)
    flow_dir = tool_input.get("flow_direction", "x")
    pos_key = "new_x" if flow_dir == "x" else "new_z"
    size_key = "width" if flow_dir == "x" else "depth"
    min_gap = tool_input.get("min_gap", 1.0)

    # Build node info from input for sizes
    input_nodes = tool_input.get("layout_nodes", [])
    node_sizes = {}
    for n in input_nodes:
        node_sizes[n.get("node_id", "")] = n.get(size_key, 1.0)

    # Sort by position on primary axis
    sorted_nodes = sorted(nodes, key=lambda n: n.get(pos_key, 0))

    for i in range(len(sorted_nodes) - 1):
        n1 = sorted_nodes[i]
        n2 = sorted_nodes[i + 1]
        n1_id = n1.get("node_id", "")
        n2_id = n2.get("node_id", "")
        n1_end = n1.get(pos_key, 0) + node_sizes.get(n1_id, 1.0)
        n2_start = n2.get(pos_key, 0)
        gap = n2_start - n1_end

        # Check secondary axis overlap (only apply min_gap if they overlap)
        sec_key = "new_z" if flow_dir == "x" else "new_x"
        sec_size_key = "depth" if flow_dir == "x" else "width"
        sec_sizes = {}
        for n in input_nodes:
            sec_sizes[n.get("node_id", "")] = n.get(sec_size_key, 1.0)

        s1_start = n1.get(sec_key, n1.get("original_z" if flow_dir == "x" else "original_x", 0))
        s1_end = s1_start + sec_sizes.get(n1_id, 1.0)
        s2_start = n2.get(sec_key, n2.get("original_z" if flow_dir == "x" else "original_x", 0))
        s2_end = s2_start + sec_sizes.get(n2_id, 1.0)

        sec_overlap = not (s1_end <= s2_start or s2_end <= s1_start)

        if sec_overlap:
            r.add_check(
                f"no_overlap:{n1_id}-{n2_id}",
                gap >= -0.01,
                f"Overlap on primary axis: gap={gap:.2f}m between {n1_id} and {n2_id}"
            )

    # All coordinates non-negative
    for n in nodes:
        nx = n.get("new_x", 0)
        nz = n.get("new_z", 0)
        r.add_check(
            f"coord_nonneg:{n.get('node_id', '?')}",
            nx >= -0.01 and nz >= -0.01,
            f"Negative coordinates: x={nx:.2f}, z={nz:.2f}"
        )

    return r


# ============================================================
# Registry
# ============================================================

VALIDATORS = {
    "bottleneck_analyzer": validate_bottleneck_analyzer,
    "line_balance_calculator": validate_line_balance_calculator,
    "equipment_utilization": validate_equipment_utilization,
    "process_distance_analyzer": validate_process_distance_analyzer,
    "worker_skill_matcher": validate_worker_skill_matcher,
    "material_flow_analyzer": validate_material_flow_analyzer,
    "safety_zone_checker": validate_safety_zone_checker,
    "takt_time_optimizer": validate_takt_time_optimizer,
    "energy_estimator": validate_energy_estimator,
    "layout_compactor": validate_layout_compactor,
}


def validate_tool_output(tool_name: str, output: dict, bop: dict, tool_input: dict) -> ValidationResult:
    """Run property-based validation for a tool's output."""
    validator = VALIDATORS.get(tool_name)
    if validator is None:
        r = ValidationResult(passed=True)
        r.add_check("validator_exists", False, f"No validator for tool '{tool_name}'")
        return r
    try:
        return validator(output, bop, tool_input)
    except Exception as e:
        r = ValidationResult(passed=False)
        r.add_check("validator_error", False, f"Validator crashed: {type(e).__name__}: {e}")
        return r
