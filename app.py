import random
import uuid
from copy import deepcopy
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = "replace-with-a-random-secret"  # change for production

# In-memory store (OK for local demo)
RUNS = {}

# ---------------- Utilities ----------------
def snapshot(states, arr, highlights=None, note=""):
    """
    Capture a frame to render: current array + highlight info.
    highlights keys: 'compare', 'swap', 'sorted' -> list[int]
    """
    if highlights is None:
        highlights = {}
    safe_hl = {}
    for k, v in highlights.items():
        if isinstance(v, (set, tuple)):
            safe_hl[k] = list(v)
        else:
            safe_hl[k] = v
    states.append({"arr": deepcopy(arr), "hl": safe_hl, "note": note})

# ---------------- Sorting algorithms (produce frames) ----------------
def bubble_sort_frames(arr):
    states = []
    a = deepcopy(arr)
    n = len(a)
    sorted_tail = set()
    snapshot(states, a, {"sorted": sorted_tail}, "Start Bubble Sort")
    for i in range(n - 1):
        for j in range(n - i - 1):
            snapshot(states, a, {"compare": [j, j+1], "sorted": sorted_tail}, f"Compare {j} & {j+1}")
            if a[j] > a[j+1]:
                a[j], a[j+1] = a[j+1], a[j]
                snapshot(states, a, {"swap": [j, j+1], "sorted": sorted_tail}, f"Swap {j} & {j+1}")
        sorted_tail.add(n - i - 1)
        snapshot(states, a, {"sorted": sorted_tail}, f"Fix position {n - i - 1}")
    snapshot(states, a, {"sorted": list(range(n))}, "Done")
    return states

def selection_sort_frames(arr):
    states = []
    a = deepcopy(arr)
    n = len(a)
    fixed = set()
    snapshot(states, a, {"sorted": fixed}, "Start Selection Sort")
    for i in range(n - 1):
        min_idx = i
        for j in range(i + 1, n):
            snapshot(states, a, {"compare": [min_idx, j], "sorted": fixed}, f"Compare min {min_idx} vs {j}")
            if a[j] < a[min_idx]:
                min_idx = j
                snapshot(states, a, {"compare": [i, min_idx], "sorted": fixed}, f"New min at {min_idx}")
        if min_idx != i:
            a[i], a[min_idx] = a[min_idx], a[i]
            snapshot(states, a, {"swap": [i, min_idx], "sorted": fixed}, f"Swap {i} & {min_idx}")
        fixed.add(i)
        snapshot(states, a, {"sorted": fixed}, f"Fix position {i}")
    fixed.add(n - 1)
    snapshot(states, a, {"sorted": list(fixed)}, "Done")
    return states

def insertion_sort_frames(arr):
    states = []
    a = deepcopy(arr)
    n = len(a)
    snapshot(states, a, {}, "Start Insertion Sort")
    for i in range(1, n):
        key = a[i]
        j = i - 1
        snapshot(states, a, {"compare": [i]}, f"Key index {i}")
        while j >= 0 and a[j] > key:
            a[j + 1] = a[j]
            snapshot(states, a, {"swap": [j, j+1]}, f"Shift {j} -> {j+1}")
            j -= 1
        a[j + 1] = key
        snapshot(states, a, {"swap": [j+1]}, f"Place key at {j+1}")
    snapshot(states, a, {"sorted": list(range(n))}, "Done")
    return states

def merge_sort_frames(arr):
    states = []
    a = deepcopy(arr)
    n = len(a)
    snapshot(states, a, {}, "Start Merge Sort")

    def merge(l, m, r):
        left = a[l:m+1]
        right = a[m+1:r+1]
        i = j = 0
        k = l
        while i < len(left) and j < len(right):
            snapshot(states, a, {"compare": [k]}, f"Merge compare at {k}")
            if left[i] <= right[j]:
                a[k] = left[i]; i += 1
            else:
                a[k] = right[j]; j += 1
            snapshot(states, a, {"swap": [k]}, f"Write at {k}")
            k += 1
        while i < len(left):
            a[k] = left[i]; i += 1
            snapshot(states, a, {"swap": [k]}, f"Write left at {k}")
            k += 1
        while j < len(right):
            a[k] = right[j]; j += 1
            snapshot(states, a, {"swap": [k]}, f"Write right at {k}")
            k += 1
        snapshot(states, a, {"sorted": list(range(l, r+1))}, f"Merged [{l}, {r}]")

    def sort(l, r):
        if l >= r: return
        m = (l + r) // 2
        sort(l, m)
        sort(m + 1, r)
        merge(l, m, r)

    sort(0, n - 1)
    snapshot(states, a, {"sorted": list(range(n))}, "Done")
    return states

def quick_sort_frames(arr):
    states = []
    a = deepcopy(arr)
    n = len(a)
    snapshot(states, a, {}, "Start Quick Sort")

    def partition(low, high):
        pivot = a[high]
        i = low - 1
        for j in range(low, high):
            snapshot(states, a, {"compare": [j, high]}, f"Compare {j} with pivot {high}")
            if a[j] < pivot:
                i += 1
                if i != j:
                    a[i], a[j] = a[j], a[i]
                    snapshot(states, a, {"swap": [i, j]}, f"Swap {i} & {j}")
        if i + 1 != high:
            a[i + 1], a[high] = a[high], a[i + 1]
            snapshot(states, a, {"swap": [i + 1, high]}, f"Place pivot at {i+1}")
        return i + 1

    def quick(low, high):
        if low < high:
            p = partition(low, high)
            quick(low, p - 1)
            quick(p + 1, high)

    quick(0, n - 1)
    snapshot(states, a, {"sorted": list(range(n))}, "Done")
    return states

ALGORITHMS = {
    "bubble":    ("Bubble Sort", bubble_sort_frames),
    "selection": ("Selection Sort", selection_sort_frames),
    "insertion": ("Insertion Sort", insertion_sort_frames),
    "merge":     ("Merge Sort", merge_sort_frames),
    "quick":     ("Quick Sort", quick_sort_frames),
}

# ---------------- Routes ----------------
@app.route("/", methods=["GET"])
def index():
    # IMPORTANT: pass algos to template to avoid 'algos is undefined'
    return render_template("index.html", algos=ALGORITHMS)

@app.route("/start", methods=["POST"])
def start():
    algo = request.form.get("algorithm", "bubble")
    try:
        size = int(request.form.get("size", "30"))
    except ValueError:
        size = 30
    size = max(5, min(size, 120))

    # speed from form is in SECONDS; allow 0.01 .. 1.00 seconds
    speed_str = request.form.get("speed", "0.25")  # default 250 ms
    try:
        speed = float(speed_str)
    except ValueError:
        speed = 0.25
    speed = max(0.01, min(speed, 1.00))  # 10 ms to 1 sec

    autoplay = request.form.get("autoplay") == "on"

    # generate random data and compute frames
    arr = [random.randint(5, 500) for _ in range(size)]
    _, fn = ALGORITHMS.get(algo, ALGORITHMS["bubble"])
    frames = fn(arr)

    run_id = str(uuid.uuid4())
    RUNS[run_id] = {
        "algo": algo,
        "frames": frames,
        "index": 0,
        "autoplay": autoplay,
        "speed": speed,   # seconds per step
        "size": size,
    }
    session["run_id"] = run_id
    return redirect(url_for("view"))

@app.route("/view", methods=["GET"])
def view():
    run_id = session.get("run_id")
    if not run_id or run_id not in RUNS:
        return redirect(url_for("index"))

    run = RUNS[run_id]
    idx = max(0, min(run["index"], len(run["frames"]) - 1))
    run["index"] = idx
    frame = run["frames"][idx]
    title, _ = ALGORITHMS[run["algo"]]

    # view.html should use `autoplay` and `speed` to add meta-refresh
    return render_template(
        "view.html",
        title=title,
        idx=idx,
        total=len(run["frames"]),
        frame=frame,
        autoplay=run["autoplay"],
        speed=run["speed"],
        algos=ALGORITHMS,      # optional if your view page has controls
        algo_key=run["algo"],
        size=run["size"],
    )

@app.route("/advance", methods=["POST", "GET"])
def advance():
    # GET is used by meta refresh; POST by buttons (Prev/Next)
    run_id = session.get("run_id")
    if not run_id or run_id not in RUNS:
        return redirect(url_for("index"))
    run = RUNS[run_id]
    direction = request.values.get("dir", "next")  # next, prev, first, last, toggle_auto
    if direction == "next":
        run["index"] = min(run["index"] + 1, len(run["frames"]) - 1)
    elif direction == "prev":
        run["index"] = max(run["index"] - 1, 0)
    elif direction == "first":
        run["index"] = 0
    elif direction == "last":
        run["index"] = len(run["frames"]) - 1
    elif direction == "toggle_auto":
        run["autoplay"] = not run["autoplay"]
    return redirect(url_for("view"))

@app.route("/reset", methods=["POST"])
def reset():
    run_id = session.get("run_id")
    if run_id in RUNS:
        del RUNS[run_id]
    session.pop("run_id", None)
    return redirect(url_for("index"))

if __name__ == "__main__":
    # Host locally; debug=True for development
    app.run(debug=True)
