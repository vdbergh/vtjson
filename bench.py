import copy
import math
import sys
from datetime import datetime, timezone
from timeit import timeit

from bson.objectid import ObjectId

from vtjson import (
    at_most_one_of,
    compile,
    div,
    fields,
    glob,
    ifthen,
    intersect,
    interval,
    ip_address,
    keys,
    lax,
    number,
    one_of,
    quote,
    regex,
    union,
    url,
    validate,
)

username = regex(r"[!-~][ -~]{0,30}[!-~]", name="username")
net_name = regex("nn-[a-f0-9]{12}.nnue", name="net_name")
tc = regex(r"([1-9]\d*/)?\d+(\.\d+)?(\+\d+(\.\d+)?)?", name="tc")
str_int = regex(r"[1-9]\d*", name="str_int")
sha = regex(r"[a-f0-9]{40}", name="sha")
country_code = regex(r"[A-Z][A-Z]", name="country_code")
run_id = regex(r"[a-f0-9]{24}", name="run_id")
uuid = regex(r"[0-9a-zA-Z]{2,}(-[a-f0-9]{4}){3}-[a-f0-9]{12}", name="uuid")
epd_file = glob("*.epd", name="epd_file")
pgn_file = glob("*.pgn", name="pgn_file")
even = div(2, name="even")
datetime_utc = intersect(datetime, fields({"tzinfo": timezone.utc}))

uint = intersect(int, interval(0, ...))
suint = intersect(int, interval(1, ...))
unumber = intersect(number, interval(0, ...))


def valid_results(R):
    l, d, w = R["losses"], R["draws"], R["wins"]
    R = R["pentanomial"]
    return (
        l + d + w == 2 * sum(R)
        and w - l == 2 * R[4] + R[3] - R[1] - 2 * R[0]
        and R[2] >= R[3] + 2 * R[2] + R[1] - d >= 0
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
                            "c_end": unumber,
                            "r_end": unumber,
                            "c": unumber,
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
    final_results_must_match,
)

task_object = {
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

run_sprt_object = {
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
    run_sprt_object["bad_tasks"].append(copy.deepcopy(task_object))
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
    for k in r:
        if k != "pentanomial":
            tmp[k] += r[k]
        else:
            for i, p in enumerate(r["pentanomial"]):
                tmp[k][i] += p
run_sprt_object["results"] = tmp

# To avoid bugs
validate(runs_schema, run_sprt_object, "run")

print(f"Python {sys.version}")

N = 100
t = timeit("compile(runs_schema)", number=N, globals=globals())
print("")
print(f"Compiling the runs_schema takes {1000*t/N:.2f} ms")

N = 100
t = timeit("validate(runs_schema, run_sprt_object)", number=N, globals=globals())
print("")
print(
    f"Validating an SPRT run with {total_tasks} tasks "
    f"and {total_bad_tasks} bad task takes {1000*t/N:.2f} ms"
)
runs_schema_compiled = compile(runs_schema)
N = 100
t = timeit(
    "validate(runs_schema_compiled, run_sprt_object)", number=N, globals=globals()
)
print("")
print(
    f"Validating a compiled SPRT run with {total_tasks} tasks "
    f"and {total_bad_tasks} bad task takes {1000*t/N:.2f} ms"
)

thetas = [
    {"R": 0.02380368399108814, "c": 2.9826065718051287, "theta": 61.28398809721997},
    {"R": 0.02380368399108814, "c": 2.9826065718051287, "theta": 66.71601190278002},
    {"R": 0.02380368399108814, "c": 2.9826065718051287, "theta": 16.283988097219968},
    {"R": 0.02380368399108814, "c": 2.9826065718051287, "theta": 61.71601190278003},
    {"R": 0.02380368399108814, "c": 2.9826065718051287, "theta": 30.716011902780032},
]

param_history = 101 * [thetas]

spsa = {
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

run_spsa_object = run_sprt_object
del run_spsa_object["args"]["sprt"]
run_spsa_object["args"]["spsa"] = spsa
validate(runs_schema, run_spsa_object, "run")
t = timeit("validate(runs_schema, run_spsa_object)", number=N, globals=globals())
print("")
print(
    f"Validating an SPSA run with {len(spsa['param_history'])}"
    f" param_history entries and {total_tasks} tasks and "
    f"{total_bad_tasks} bad task takes {1000*t/N:.2f} ms"
)
t = timeit(
    "validate(runs_schema_compiled, run_spsa_object)", number=N, globals=globals()
)
print("")
print(
    f"Validating a compiled SPSA run with {len(spsa['param_history'])}"
    f" param_history entries and {total_tasks} tasks and "
    f"{total_bad_tasks} bad task takes {1000*t/N:.2f} ms"
)
