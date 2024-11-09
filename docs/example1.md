# The runs schema

```python

import copy
import math
from datetime import datetime, timezone

from bson.objectid import ObjectId

from vtjson import (
    at_most_one_of,
    div,
    fields,
    ge,
    glob,
    gt,
    ifthen,
    intersect,
    ip_address,
    keys,
    lax,
    number,
    one_of,
    quote,
    regex,
    set_name,
    union,
    url,
)

username = regex(r"[!-~][ -~]{0,30}[!-~]", name="username")
net_name = regex("nn-[a-f0-9]{12}.nnue", name="net_name")
tc = regex(r"([1-9]\d*/)?\d+(\.\d+)?(\+\d+(\.\d+)?)?", name="tc")
str_int = regex(r"[1-9]\d*", name="str_int")
sha = regex(r"[a-f0-9]{40}", name="sha")
country_code = regex(r"[A-Z][A-Z]", name="country_code")
run_id = set_name(ObjectId.is_valid, "run_id")
uuid = regex(r"[0-9a-zA-Z]{2,}(-[a-f0-9]{4}){3}-[a-f0-9]{12}", name="uuid")
epd_file = glob("*.epd", name="epd_file")
pgn_file = glob("*.pgn", name="pgn_file")
even = div(2, name="even")
datetime_utc = intersect(datetime, fields({"tzinfo": timezone.utc}))

uint = intersect(int, ge(0))
suint = intersect(int, gt(0))
unumber = intersect(number, ge(0))
sunumber = intersect(number, gt(0))


def valid_results(R):
    l, d, w = R["losses"], R["draws"], R["wins"]
    R = R["pentanomial"]
    return (
        l + d + w == 2 * sum(R)
        and w - l == 2 * R[4] + R[3] - R[1] - 2 * R[0]
        and R[3] + 2 * R[2] + R[1] >= d >= R[3] + R[1]
    )


zero_results = {
    "wins": 0,
    "draws": 0,
    "losses": 0,
    "crashes": 0,
    "time_losses": 0,
    "pentanomial": 5 * [0],
}

if_bad_then_zero_stats_and_not_active = ifthen(
    keys("bad"), lax({"active": False, "stats": quote(zero_results)})
)


def final_results_must_match(run):
    rr = copy.deepcopy(zero_results)
    for t in run["tasks"]:
        r = t["stats"]
        for k in r:
            if k != "pentanomial":
                rr[k] += r[k]
            else:
                for i, p in enumerate(r["pentanomial"]):
                    rr[k][i] += p
    if rr != run["results"]:
        raise Exception(
            f"The final results {run['results']} do not match the computed results {rr}"
        )
    else:
        return True


def cores_must_match(run):
    cores = 0
    for t in run["tasks"]:
        if t["active"]:
            cores += t["worker_info"]["concurrency"]
    if cores != run["cores"]:
        raise Exception(
            f"Cores mismatch. Cores from tasks: {cores}. Cores from "
            f"run: {run['cores']}"
        )

    return True


def workers_must_match(run):
    workers = 0
    for t in run["tasks"]:
        if t["active"]:
            workers += 1
    if workers != run["workers"]:
        raise Exception(
            f"Workers mismatch. Workers from tasks: {workers}. Workers from "
            f"run: {run['workers']}"
        )

    return True


valid_aggregated_data = intersect(
    final_results_must_match,
    cores_must_match,
    workers_must_match,
)

worker_info_schema = {
    "uname": str,
    "architecture": [str, str],
    "concurrency": suint,
    "max_memory": uint,
    "min_threads": suint,
    "username": str,
    "version": uint,
    "python_version": [uint, uint, uint],
    "gcc_version": [uint, uint, uint],
    "compiler": union("clang++", "g++"),
    "unique_key": uuid,
    "modified": bool,
    "ARCH": str,
    "nps": unumber,
    "near_github_api_limit": bool,
    "remote_addr": ip_address,
    "country_code": union(country_code, "?"),
}

results_schema = intersect(
    {
        "wins": uint,
        "losses": uint,
        "draws": uint,
        "crashes": uint,
        "time_losses": uint,
        "pentanomial": [uint, uint, uint, uint, uint],
    },
    valid_results,
)

runs_schema = intersect(
    {
        "_id?": ObjectId,
        "version": uint,
        "start_time": datetime_utc,
        "last_updated": datetime_utc,
        "tc_base": unumber,
        "base_same_as_master": bool,
        "rescheduled_from?": run_id,
        "approved": bool,
        "approver": union(username, ""),
        "finished": bool,
        "deleted": bool,
        "failed": bool,
        "is_green": bool,
        "is_yellow": bool,
        "workers": uint,
        "cores": uint,
        "results": results_schema,
        "results_info?": {
            "style": str,
            "info": [str, ...],
        },
        "args": intersect(
            {
                "base_tag": str,
                "new_tag": str,
                "base_nets": [net_name, ...],
                "new_nets": [net_name, ...],
                "num_games": intersect(uint, even),
                "tc": tc,
                "new_tc": tc,
                "book": union(epd_file, pgn_file),
                "book_depth": str_int,
                "threads": suint,
                "resolved_base": sha,
                "resolved_new": sha,
                "master_sha": sha,
                "official_master_sha": sha,
                "msg_base": str,
                "msg_new": str,
                "base_options": str,
                "new_options": str,
                "info": str,
                "base_signature": str_int,
                "new_signature": str_int,
                "username": username,
                "tests_repo": url,
                "auto_purge": bool,
                "throughput": unumber,
                "itp": unumber,
                "priority": number,
                "adjudication": bool,
                "sprt?": intersect(
                    {
                        "alpha": 0.05,
                        "beta": 0.05,
                        "elo0": number,
                        "elo1": number,
                        "elo_model": "normalized",
                        "state": union("", "accepted", "rejected"),
                        "llr": number,
                        "batch_size": suint,
                        "lower_bound": -math.log(19),
                        "upper_bound": math.log(19),
                        "lost_samples?": uint,
                        "illegal_update?": uint,
                        "overshoot?": {
                            "last_update": uint,
                            "skipped_updates": uint,
                            "ref0": number,
                            "m0": number,
                            "sq0": unumber,
                            "ref1": number,
                            "m1": number,
                            "sq1": unumber,
                        },
                    },
                    one_of("overshoot", "lost_samples"),
                ),
                "spsa?": {
                    "A": unumber,
                    "alpha": unumber,
                    "gamma": unumber,
                    "raw_params": str,
                    "iter": uint,
                    "num_iter": uint,
                    "params": [
                        {
                            "name": str,
                            "start": number,
                            "min": number,
                            "max": number,
                            "c_end": sunumber,
                            "r_end": unumber,
                            "c": sunumber,
                            "a_end": unumber,
                            "a": unumber,
                            "theta": number,
                        },
                        ...,
                    ],
                    "param_history?": [
                        [
                            {"theta": number, "R": unumber, "c": unumber},
                            ...,
                        ],
                        ...,
                    ],
                },
            },
            at_most_one_of("sprt", "spsa"),
        ),
        "tasks": [
            intersect(
                {
                    "num_games": intersect(uint, even),
                    "active": bool,
                    "last_updated": datetime_utc,
                    "start": uint,
                    "residual?": number,
                    "residual_color?": str,
                    "bad?": True,
                    "stats": results_schema,
                    "worker_info": worker_info_schema,
                },
                if_bad_then_zero_stats_and_not_active,
            ),
            ...,
        ],
        "bad_tasks?": [
            {
                "num_games": intersect(uint, even),
                "active": False,
                "last_updated": datetime_utc,
                "start": uint,
                "residual": number,
                "residual_color": str,
                "bad": True,
                "task_id": uint,
                "stats": results_schema,
                "worker_info": worker_info_schema,
            },
            ...,
        ],
    },
    lax(ifthen({"approved": True}, {"approver": username}, {"approver": ""})),
    lax(ifthen({"is_green": True}, {"is_yellow": False})),
    lax(ifthen({"is_yellow": True}, {"is_green": False})),
    lax(ifthen({"failed": True}, {"finished": True})),
    lax(ifthen({"deleted": True}, {"finished": True})),
    lax(ifthen({"finished": True}, {"workers": 0, "cores": 0})),
    lax(ifthen({"finished": True}, {"tasks": [{"active": False}, ...]})),
    valid_aggregated_data,
)


```
