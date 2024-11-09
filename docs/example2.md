# The runs schema

```python

import copy
import math
from datetime import datetime, timezone
from typing import Annotated, Literal, NotRequired, TypedDict

from bson.objectid import ObjectId

from vtjson import (
    Apply,
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
    one_of,
    quote,
    regex,
    url,
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

```
