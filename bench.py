from __future__ import annotations

import copy
import math
import sys
from datetime import datetime, timezone
from timeit import timeit
from typing import Annotated, Literal, NotRequired, TypedDict, cast

from bson.objectid import ObjectId

from vtjson import (
    Apply,
    at_most_one_of,
    compile,
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
    one_of,
    quote,
    regex,
    url,
    validate,
)

skip_first = Apply(skip_first=True)

username = Annotated[str, regex(r"[!-~][ -~]{0,30}[!-~]", name="username"), skip_first]
net_name = Annotated[str, regex("nn-[a-f0-9]{12}.nnue", name="net_name"), skip_first]
tc = Annotated[
    str, regex(r"([1-9]\d*/)?\d+(\.\d+)?(\+\d+(\.\d+)?)?", name="tc"), skip_first
]
str_int = Annotated[str, regex(r"[1-9]\d*", name="str_int"), skip_first]
sha = Annotated[str, regex(r"[a-f0-9]{40}", name="sha"), skip_first]
country_code = Annotated[str, regex(r"[A-Z][A-Z]", name="country_code"), skip_first]
run_id = Annotated[str, ObjectId.is_valid]
uuid = Annotated[
    str,
    regex(r"[0-9a-zA-Z]{2,}(-[a-f0-9]{4}){3}-[a-f0-9]{12}", name="uuid"),
    skip_first,
]
epd_file = Annotated[str, glob("*.epd", name="epd_file"), skip_first]
pgn_file = Annotated[str, glob("*.pgn", name="pgn_file"), skip_first]
even = Annotated[int, div(2, name="even"), skip_first]
datetime_utc = Annotated[datetime, fields({"tzinfo": timezone.utc})]

uint = Annotated[int, ge(0)]
suint = Annotated[int, gt(0)]
ufloat = Annotated[float, ge(0)]
sufloat = Annotated[float, gt(0)]


class results_type(TypedDict):
    wins: uint
    losses: uint
    draws: uint
    crashes: uint
    time_losses: uint
    pentanomial: Annotated[list[int], [uint, uint, uint, uint, uint], skip_first]


def valid_results(R: results_type) -> bool:
    l, d, w = R["losses"], R["draws"], R["wins"]
    Rp = R["pentanomial"]
    return (
        l + d + w == 2 * sum(Rp)
        and w - l == 2 * Rp[4] + Rp[3] - Rp[1] - 2 * Rp[0]
        and Rp[3] + 2 * Rp[2] + Rp[1] >= d >= Rp[3] + Rp[1]
    )


results_schema = Annotated[
    results_type,
    valid_results,
]


class worker_info_schema(TypedDict):
    uname: str
    architecture: Annotated[list[str], [str, str], skip_first]
    concurrency: suint
    max_memory: uint
    min_threads: suint
    username: str
    version: uint
    python_version: Annotated[list[int], [uint, uint, uint], skip_first]
    gcc_version: Annotated[list[int], [uint, uint, uint], skip_first]
    compiler: Literal["clang++", "g++"]
    unique_key: uuid
    modified: bool
    ARCH: str
    nps: ufloat
    near_github_api_limit: bool
    remote_addr: Annotated[str, ip_address]
    country_code: country_code | Literal["?"]


class overshoot_type(TypedDict):
    last_update: uint
    skipped_updates: uint
    ref0: float
    m0: float
    sq0: ufloat
    ref1: float
    m1: float
    sq1: ufloat


class sprt_type(TypedDict):
    alpha: Annotated[float, 0.05, skip_first]
    beta: Annotated[float, 0.05, skip_first]
    elo0: float
    elo1: float
    elo_model: Literal["normalized"]
    state: Literal["", "accepted", "rejected"]
    llr: float
    batch_size: suint
    lower_bound: Annotated[float, -math.log(19), skip_first]
    upper_bound: Annotated[float, math.log(19), skip_first]
    lost_samples: NotRequired[uint]
    illegal_update: NotRequired[uint]
    overshoot: NotRequired[overshoot_type]


sprt_schema = Annotated[
    sprt_type,
    one_of("overshoot", "lost_samples"),
]


class param_schema(TypedDict):
    name: str
    start: float
    min: float
    max: float
    c_end: sufloat
    r_end: ufloat
    c: sufloat
    a_end: ufloat
    a: ufloat
    theta: float


class param_history_schema(TypedDict):
    theta: float
    R: ufloat
    c: ufloat


class spsa_schema(TypedDict):
    A: ufloat
    alpha: ufloat
    gamma: ufloat
    raw_params: str
    iter: uint
    num_iter: uint
    params: list[param_schema]
    param_history: NotRequired[list[list[param_history_schema]]]


class args_type(TypedDict):
    base_tag: str
    new_tag: str
    base_nets: list[net_name]
    new_nets: list[net_name]
    num_games: Annotated[uint, even]
    tc: tc
    new_tc: tc
    book: epd_file | pgn_file
    book_depth: str_int
    threads: suint
    resolved_base: sha
    resolved_new: sha
    master_sha: sha
    official_master_sha: sha
    msg_base: str
    msg_new: str
    base_options: str
    new_options: str
    info: str
    base_signature: str_int
    new_signature: str_int
    username: username
    tests_repo: Annotated[str, url, skip_first]
    auto_purge: bool
    throughput: ufloat
    itp: ufloat
    priority: float
    adjudication: bool
    sprt: NotRequired[sprt_schema]
    spsa: NotRequired[spsa_schema]


args_schema = Annotated[
    args_type,
    at_most_one_of("sprt", "spsa"),
]


class task_type(TypedDict):
    num_games: Annotated[uint, even]
    active: bool
    last_updated: datetime_utc
    start: uint
    residual: float
    residual_color: NotRequired[str]
    bad: NotRequired[Literal[True]]
    stats: results_schema
    worker_info: worker_info_schema


zero_results: results_type = {
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

task_schema = Annotated[
    task_type,
    if_bad_then_zero_stats_and_not_active,
]


class bad_task_schema(TypedDict):
    num_games: Annotated[uint, even]
    active: Literal[False]
    last_updated: datetime_utc
    start: uint
    residual: float
    residual_color: str
    bad: Literal[True]
    task_id: uint
    stats: results_schema
    worker_info: worker_info_schema


class results_info_schema(TypedDict):
    style: str
    info: list[str]


class runs_type(TypedDict):
    _id: NotRequired[ObjectId]
    version: uint
    start_time: datetime_utc
    last_updated: datetime_utc
    tc_base: ufloat
    base_same_as_master: bool
    rescheduled_from: NotRequired[run_id]
    approved: bool
    approver: username | Literal[""]
    finished: bool
    deleted: bool
    failed: bool
    is_green: bool
    is_yellow: bool
    workers: uint
    cores: uint
    results: results_schema
    results_info: NotRequired[results_info_schema]
    args: args_schema
    tasks: list[task_schema]
    bad_tasks: NotRequired[list[bad_task_schema]]


def final_results_must_match(run: runs_type) -> bool:
    rr = copy.deepcopy(zero_results)
    for t in run["tasks"]:
        r = t["stats"]
        # mypy does not support variable keys for
        # TypedDict
        rr["wins"] += r["wins"]
        rr["losses"] += r["losses"]
        rr["draws"] += r["draws"]
        rr["crashes"] += r["crashes"]
        rr["time_losses"] += r["time_losses"]
        for i, p in enumerate(r["pentanomial"]):
            rr["pentanomial"][i] += p
    if rr != run["results"]:
        raise Exception(
            f"The final results {run['results']} do not match the computed results {rr}"
        )
    else:
        return True


def cores_must_match(run: runs_type) -> bool:
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


def workers_must_match(run: runs_type) -> bool:
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

runs_schema = Annotated[
    runs_type,
    lax(ifthen({"approved": True}, {"approver": username}, {"approver": ""})),
    lax(ifthen({"is_green": True}, {"is_yellow": False})),
    lax(ifthen({"is_yellow": True}, {"is_green": False})),
    lax(ifthen({"failed": True}, {"finished": True})),
    lax(ifthen({"deleted": True}, {"finished": True})),
    lax(ifthen({"finished": True}, {"workers": 0, "cores": 0})),
    lax(ifthen({"finished": True}, {"tasks": [{"active": False}, ...]})),
    valid_aggregated_data,
]

task_object: task_schema = {
    "num_games": 1632,
    "active": False,
    "worker_info": {
        "uname": "Linux 6.5.8-200.fc38.x86_64",
        "architecture": ["64bit", "ELF"],
        "concurrency": 28,
        "max_memory": 7992,
        "min_threads": 1,
        "username": "okrout",
        "version": 222,
        "python_version": [3, 11, 6],
        "gcc_version": [13, 2, 1],
        "compiler": "g++",
        "unique_key": "22f29ecf-5a28-4b7d-b27b-d78d97ecf11a",
        "modified": False,
        "ARCH": "64bit AVX2 SSE41 SSSE3 SSE2 POPCNT",
        "nps": 448999.0,
        "near_github_api_limit": False,
        "remote_addr": "111.111.111.111",
        "country_code": "US",
    },
    "last_updated": datetime.now(timezone.utc),
    "start": 0,
    "stats": {
        "wins": 396,
        "losses": 410,
        "draws": 826,
        "crashes": 0,
        "time_losses": 0,
        "pentanomial": [2, 197, 434, 179, 4],
    },
    "residual": 1.7549591853035416,
    "residual_color": "#44EB44",
}

run_sprt_object: runs_schema = {
    "_id": ObjectId("6549951b136acbc573529528"),
    "version": 0,
    "args": {
        "base_tag": "master",
        "new_tag": "phRed8",
        "base_nets": ["nn-0000000000a0.nnue"],
        "new_nets": ["nn-0000000000a0.nnue"],
        "num_games": 800000,
        "tc": "10+0.1",
        "new_tc": "10+0.1",
        "book": "UHO_Lichess_4852_v1.epd",
        "book_depth": "8",
        "threads": 1,
        "resolved_base": "442c294a07836e9e32ad8b3bad49a853cc6f47de",
        "resolved_new": "ddfe32d14f289646e6470bde3a8ec12f1fb84578",
        "master_sha": "442c294a07836e9e32ad8b3bad49a853cc6f47de",
        "official_master_sha": "442c294a07836e9e32ad8b3bad49a853cc6f47de",
        "msg_base": "Use stat_malus when decreasing stats",
        "msg_new": "bench 1246774",
        "base_options": "Hash=16",
        "new_options": "Hash=16",
        "info": "Take 8",
        "base_signature": "1114417",
        "new_signature": "1246774",
        "username": "Vizvezdenec",
        "tests_repo": "https://github.com/Vizvezdenec/Stockfish",
        "auto_purge": False,
        "throughput": 100,
        "itp": 36.0,
        "priority": 0,
        "adjudication": True,
        "sprt": {
            "alpha": 0.05,
            "beta": 0.05,
            "elo0": 0.0,
            "elo1": 2.0,
            "elo_model": "normalized",
            "state": "rejected",
            "llr": -2.936953911013966,
            "batch_size": 16,
            "lower_bound": -2.9444389791664403,
            "upper_bound": 2.9444389791664403,
            "overshoot": {
                "last_update": 3184,
                "skipped_updates": 0,
                "ref0": -2.936953911013966,
                "m0": -2.936953911013966,
                "sq0": 0.1069762911936328,
                "ref1": 0.2331113146809201,
                "m1": 0.2331113146809201,
                "sq1": 0.01295330278694318,
            },
        },
    },
    "start_time": datetime.now(timezone.utc),
    "last_updated": datetime.now(timezone.utc),
    "tc_base": 10.0,
    "base_same_as_master": True,
    "tasks": [],
    "bad_tasks": [],
    "results": {
        "wins": 26829,
        "losses": 26934,
        "draws": 52605,
        "crashes": 0,
        "time_losses": 12,
        "pentanomial": [369, 12695, 27124, 12664, 332],
    },
    "approved": True,
    "approver": "bigpen0r",
    "finished": True,
    "deleted": False,
    "failed": False,
    "is_green": False,
    "is_yellow": False,
    "results_info": {
        "style": "#FF6A6A",
        "info": [
            "LLR: -2.94 (-2.94,2.94) <0.00,2.00>",
            "Total: 106368 W: 26829 L: 26934 D: 52605",
            "Ptnml(0-2): 369, 12695, 27124, 12664, 332",
        ],
    },
    "workers": 0,
    "cores": 0,
}

total_tasks = 500
for i in range(total_tasks):
    run_sprt_object["tasks"].append(copy.deepcopy(task_object))
total_bad_tasks = 50
for i in range(total_bad_tasks):
    run_sprt_object["bad_tasks"].append(
        cast(bad_task_schema, copy.deepcopy(task_object))
    )
    run_sprt_object["bad_tasks"][-1]["bad"] = True
    run_sprt_object["bad_tasks"][-1]["active"] = False
    run_sprt_object["bad_tasks"][-1]["task_id"] = i
    run_sprt_object["tasks"][i]["bad"] = True
    run_sprt_object["tasks"][i]["stats"] = zero_results
    run_sprt_object["tasks"][i]["active"] = False


# fix results

tmp = copy.deepcopy(zero_results)
for t in run_sprt_object["tasks"]:
    r = t["stats"]
    tmp["wins"] += r["wins"]
    tmp["losses"] += r["losses"]
    tmp["draws"] += r["draws"]
    tmp["time_losses"] += r["time_losses"]
    tmp["crashes"] += r["crashes"]
    for i, p in enumerate(r["pentanomial"]):
        tmp["pentanomial"][i] += p
run_sprt_object["results"] = tmp

# To avoid bugs
validate(runs_schema, run_sprt_object, "run")

print(f"Python {sys.version}")

N = 100
t1 = timeit("compile(runs_schema)", number=N, globals=globals())
print("")
print(f"Compiling the runs_schema takes {1000*t1/N:.2f} ms")

N = 100
t2 = timeit("validate(runs_schema, run_sprt_object)", number=N, globals=globals())
print("")
print(
    f"Validating an SPRT run with {total_tasks} tasks "
    f"and {total_bad_tasks} bad task takes {1000*t2/N:.2f} ms"
)
runs_schema_compiled = compile(runs_schema)
N = 100
t3 = timeit(
    "validate(runs_schema_compiled, run_sprt_object)", number=N, globals=globals()
)
print("")
print(
    f"Validating a compiled SPRT run with {total_tasks} tasks "
    f"and {total_bad_tasks} bad task takes {1000*t3/N:.2f} ms"
)

thetas: list[param_history_schema] = [
    {"R": 0.02380368399108814, "c": 2.9826065718051287, "theta": 61.28398809721997},
    {"R": 0.02380368399108814, "c": 2.9826065718051287, "theta": 66.71601190278002},
    {"R": 0.02380368399108814, "c": 2.9826065718051287, "theta": 16.283988097219968},
    {"R": 0.02380368399108814, "c": 2.9826065718051287, "theta": 61.71601190278003},
    {"R": 0.02380368399108814, "c": 2.9826065718051287, "theta": 30.716011902780032},
]

param_history = 101 * [thetas]

spsa: spsa_schema = {
    "A": 5000,
    "alpha": 0.602,
    "gamma": 0.101,
    "iter": 50000,
    "num_iter": 50000,
    "param_history": param_history,
    "params": [
        {
            "a": 35.700010464300185,
            "a_end": 0.05,
            "c": 2.9826065718051287,
            "c_end": 1.0,
            "max": 125.0,
            "min": -3.0,
            "name": "A[1]",
            "r_end": 0.05,
            "start": 61.0,
            "theta": 61.45857717957549,
        },
        {
            "a": 35.700010464300185,
            "a_end": 0.05,
            "c": 2.9826065718051287,
            "c_end": 1.0,
            "max": 131.0,
            "min": 3.0,
            "name": "A[2]",
            "r_end": 0.05,
            "start": 67.0,
            "theta": 63.541704176544684,
        },
        {
            "a": 35.700010464300185,
            "a_end": 0.05,
            "c": 2.9826065718051287,
            "c_end": 1.0,
            "max": 80.0,
            "min": -48.0,
            "name": "A[3]",
            "r_end": 0.05,
            "start": 16.0,
            "theta": 4.751241882584454,
        },
        {
            "a": 35.700010464300185,
            "a_end": 0.05,
            "c": 2.9826065718051287,
            "c_end": 1.0,
            "max": 126.0,
            "min": -2.0,
            "name": "A[4]",
            "r_end": 0.05,
            "start": 62.0,
            "theta": 44.58456299118108,
        },
        {
            "a": 35.700010464300185,
            "a_end": 0.05,
            "c": 2.9826065718051287,
            "c_end": 1.0,
            "max": 95.0,
            "min": -33.0,
            "name": "A[6]",
            "r_end": 0.05,
            "start": 31.0,
            "theta": 36.56109862629754,
        },
    ],
    "raw_params": "A[1],61,-3,125,1,0.05\r\nA[2],67,3,131,1,0.05\r\n"
    "A[3],16,-48,80,1,0.05\r\nA[4],62,-2,126,1,0.05\r\nA[6],31,-33,95,1,0.05",
}

run_spsa_object = copy.deepcopy(run_sprt_object)
del run_spsa_object["args"]["sprt"]
run_spsa_object["args"]["spsa"] = spsa
validate(runs_schema, run_spsa_object, "run")
t4 = timeit("validate(runs_schema, run_spsa_object)", number=N, globals=globals())
print("")
print(
    f"Validating an SPSA run with {len(spsa['param_history'])}"
    f" param_history entries and {total_tasks} tasks and "
    f"{total_bad_tasks} bad task takes {1000*t4/N:.2f} ms"
)
t5 = timeit(
    "validate(runs_schema_compiled, run_spsa_object)", number=N, globals=globals()
)
print("")
print(
    f"Validating a compiled SPSA run with {len(spsa['param_history'])}"
    f" param_history entries and {total_tasks} tasks and "
    f"{total_bad_tasks} bad task takes {1000*t5/N:.2f} ms"
)
