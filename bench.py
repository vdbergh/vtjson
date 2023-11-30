import copy
import math
from datetime import datetime, timezone
from timeit import timeit

from bson.objectid import ObjectId

from vtjson import _compile, _validate  # noqa: F401
from vtjson import ip_address, number, regex, url, validate

# This schema only matches new runs.

net_name = regex("nn-[a-z0-9]{12}.nnue", name="net_name")
tc = regex(r"([1-9]\d*/)?\d+(\.\d+)?(\+\d+(\.\d+)?)?", name="tc")
str_int = regex(r"[1-9]\d*", name="str_int")
sha = regex(r"[a-f0-9]{40}", name="sha")
country_code = regex(r"[A-Z][A-Z]", name="country_code")
run_id = regex(r"[a-f0-9]{24}", name="run_id")
uuid = regex(r"[0-9a-zA-z]{2,}(-[0-9a-f]{4}){3}-[0-9a-f]{12}")

worker_info_schema = {
    "uname": str,
    "architecture": [str, str],
    "concurrency": int,
    "max_memory": int,
    "min_threads": int,
    "username": str,
    "version": int,
    "python_version": [int, int, int],
    "gcc_version": [int, int, int],
    "compiler": {"clang++", "g++"},
    "unique_key": uuid,
    "modified": bool,
    "ARCH": str,
    "nps": number,
    "near_github_api_limit": bool,
    "remote_addr": ip_address,
    "country_code": {country_code, "?"},
}

results_schema = {
    "wins": int,
    "losses": int,
    "draws": int,
    "crashes": int,
    "time_losses": int,
    "pentanomial": [int, int, int, int, int],
}

runs_schema = {
    "_id?": ObjectId,
    "start_time": datetime,
    "last_updated": datetime,
    "tc_base": number,
    "base_same_as_master": bool,
    "results_stale?": bool,  # Will go away soon
    "rescheduled_from?": run_id,
    "approved": bool,
    "approver": str,
    "finished": bool,
    "deleted": bool,
    "failed": bool,
    "is_green": bool,
    "is_yellow": bool,
    "workers?": int,  # Will become non-optional
    "cores?": int,  # Will become non-optional
    "results": results_schema,
    "results_info?": {
        "style": str,
        "info": [str, ...],
    },
    "args": {
        "base_tag": str,
        "new_tag": str,
        "base_net": net_name,
        "new_net": net_name,
        "num_games": int,
        "tc": tc,
        "new_tc": tc,
        "book": str,
        "book_depth": str_int,
        "threads": int,
        "resolved_base": sha,
        "resolved_new": sha,
        "msg_base": str,
        "msg_new": str,
        "base_options": str,
        "new_options": str,
        "info": str,
        "base_signature": str_int,
        "new_signature": str_int,
        "username": str,
        "tests_repo": url,
        "auto_purge": bool,
        "throughput": number,
        "itp": number,
        "priority": number,
        "adjudication": bool,
        "sprt?": {
            "alpha": 0.05,
            "beta": 0.05,
            "elo0": number,
            "elo1": number,
            "elo_model": "normalized",
            "state": {"", "accepted", "rejected"},
            "llr": number,
            "batch_size": int,
            "lower_bound": -math.log(19),
            "upper_bound": math.log(19),
            "lost_samples?": int,
            "illegal_update?": int,
            "overshoot?": {
                "last_update": int,
                "skipped_updates": int,
                "ref0": number,
                "m0": number,
                "sq0": number,
                "ref1": number,
                "m1": number,
                "sq1": number,
            },
        },
        "spsa?": {
            "A": number,
            "alpha": number,
            "gamma": number,
            "raw_params": str,
            "iter": int,
            "num_iter": int,
            "params": [
                {
                    "name": str,
                    "start": number,
                    "min": number,
                    "max": number,
                    "c_end": number,
                    "r_end": number,
                    "c": number,
                    "a_end": number,
                    "a": number,
                    "theta": number,
                },
                ...,
            ],
            "param_history?": [
                [{"theta": number, "R": number, "c": number}, ...],
                ...,
            ],
        },
    },
    "tasks": [
        {
            "num_games": int,
            "active": bool,
            "last_updated": datetime,
            "start": int,
            "residual?": number,
            "residual_color?": str,
            "bad?": True,
            "stats": results_schema,
            "worker_info": worker_info_schema,
        },
        ...,
    ],
    "bad_tasks?": [
        {
            "num_games": int,
            "active": False,
            "last_updated": datetime,
            "start": int,
            "residual": number,
            "residual_color": str,
            "bad": True,
            "task_id": int,
            "stats": results_schema,
            "worker_info": worker_info_schema,
        },
        ...,
    ],
}

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
    "args": {
        "base_tag": "master",
        "new_tag": "phRed8",
        "base_net": "nn-0000000000a0.nnue",
        "new_net": "nn-0000000000a0.nnue",
        "num_games": 800000,
        "tc": "10+0.1",
        "new_tc": "10+0.1",
        "book": "UHO_Lichess_4852_v1.epd",
        "book_depth": "8",
        "threads": 1,
        "resolved_base": "442c294a07836e9e32ad8b3bad49a853cc6f47de",
        "resolved_new": "ddfe32d14f289646e6470bde3a8ec12f1fb84578",
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
                "last_update": 53184,
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
    "results": {
        "wins": 26829,
        "losses": 26934,
        "draws": 52605,
        "crashes": 0,
        "time_losses": 12,
        "pentanomial": [369, 12695, 27124, 12664, 332],
    },
    "results_stale": False,
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
    "workers": 7,
    "cores": 66,
}

total_tasks = 500
for i in range(total_tasks):
    run_sprt_object["tasks"].append(copy.deepcopy(task_object))


validate(runs_schema, run_sprt_object, "run")

N = 20
t = timeit(
    "_validate(runs_schema, run_sprt_object, 'run')", number=N, globals=globals()
)
print(f"Validating an SPRT run with {total_tasks} tasks takes {1000*t/N:.0f} ms")

t = timeit("_compile(runs_schema)", number=N, globals=globals())
print(
    f"Compiling runs schema takes {1000000*t/N:.0f} ns"
)
