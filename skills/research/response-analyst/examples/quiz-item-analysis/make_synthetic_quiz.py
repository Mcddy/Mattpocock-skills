"""Generates the SYNTHETIC quiz responses and instrument for this example. Standard library only.

Usage:  python make_synthetic_quiz.py OUTPUT_FOLDER SEED      (the example was made with: . 1)

31 respondents, 12 items, fixed seed. Planted on purpose: k7 is keyed C in the instrument although B
is the right answer (a miskey), and option D of k10 is implausible so nobody picks it (a dead
distractor). Writes responses.csv and instrument.json into OUTPUT_FOLDER, replacing any there.
Exit codes: 0 written. 2 bad arguments.
"""
import csv, json, math, random, statistics, sys
if len(sys.argv) != 3 or not sys.argv[2].lstrip("-").isdigit():
    print("usage: python make_synthetic_quiz.py OUTPUT_FOLDER SEED", file=sys.stderr)
    sys.exit(2)
out, seed = sys.argv[1], int(sys.argv[2])
rng = random.Random(seed)
N = 31
ITEMS = [  # id, text, options, TRUE answer, key recorded in the instrument, difficulty b, wrong-answer weights
 ("k1", "Which symbol starts a formula in a spreadsheet cell?", {"A": "=", "B": "#", "C": "@", "D": "&"}, "A", "A", -3.2, None),
 ("k2", "What does SUM(A1:A5) add up?", {"A": "A1 and A5 only", "B": "Cells A1 to A5", "C": "All of column A", "D": "Rows 1 to 5 of every column"}, "B", "B", -1.6, None),
 ("k3", "Which chart suits shares of a whole at one point in time?", {"A": "Line chart", "B": "Scatter plot", "C": "Pie or stacked bar", "D": "Histogram"}, "C", "C", -0.9, None),
 ("k4", "What does a filter do to rows that do not match?", {"A": "Deletes them", "B": "Hides them", "C": "Sorts them to the bottom", "D": "Locks them"}, "B", "B", -1.1, None),
 ("k5", "What is the mean of 2, 4 and 9?", {"A": "4", "B": "5", "C": "7.5", "D": "15"}, "B", "B", -0.6, None),
 ("k6", "Which of these is a relative cell reference?", {"A": "$A$1", "B": "A1", "C": "$A1$", "D": "'A1'"}, "B", "B", 0.0, None),
 ("k7", "Which function gives the middle value of a sorted list?", {"A": "MEAN", "B": "MEDIAN", "C": "MODE", "D": "MAX"}, "B", "C", -0.4, {"A": 0.3, "C": 0.5, "D": 0.2}),
 ("k8", "What happens if one column of a table is sorted on its own?", {"A": "Rows stay intact", "B": "Values no longer line up with their rows", "C": "Duplicates are removed", "D": "The header is frozen"}, "B", "B", -0.2, None),
 ("k9", "What does a pivot table do?", {"A": "Summarises rows by group", "B": "Rotates the sheet", "C": "Checks spelling", "D": "Protects the file"}, "A", "A", 0.3, None),
 ("k10", "What does $B$2 do when a formula is copied down a column?", {"A": "Stays on B2", "B": "Moves down a row each time", "C": "Moves across a column each time", "D": "Deletes cell B2"}, "A", "A", -0.5, {"B": 0.6, "C": 0.4, "D": 0.0}),
 ("k11", "COUNT counts the cells in a range that contain", {"A": "Anything", "B": "Text", "C": "Numbers", "D": "Formulas only"}, "C", "C", 0.9, None),
 ("k12", "Where does VLOOKUP look for its lookup value?", {"A": "Any column of the range", "B": "The first column of the range", "C": "The last column of the range", "D": "The header row"}, "B", "B", 1.3, None),
]
nd = statistics.NormalDist()
theta = [nd.inv_cdf((i + 0.5) / N) for i in range(N)]
rng.shuffle(theta)
rows = []
for i in range(N):
    row = ["quiz-%03d" % (201 + 3 * i)]
    for qid, text, opts, true, key, b, w in ITEMS:
        if rng.random() < 0.02:
            row.append("")
            continue
        p = 1 / (1 + math.exp(-1.5 * (theta[i] - b)))
        if rng.random() < p:
            row.append(true)
        else:
            wrong = [o for o in opts if o != true]
            weights = [w[o] for o in wrong] if w else [1] * len(wrong)
            row.append(rng.choices(wrong, weights)[0])
    rows.append(row)
with open(out + "/responses.csv", "w", newline="", encoding="utf-8") as f:
    wr = csv.writer(f, lineterminator="\n")
    wr.writerow(["respondent"] + [it[0] for it in ITEMS])
    wr.writerows(rows)
inst = {"title": "Spreadsheet basics quiz (SYNTHETIC data)",
        "collection": {"reached": "Paper quiz sat by everyone present at the end of the session; 31 of 31 handed it in.", "invited": 31,
                       "missing": "Nobody present is missing. People enrolled but absent that day did not sit it."},
        "questions": [{"id": qid, "text": text + "  " + "  ".join("%s) %s" % kv for kv in opts.items()), "type": "single", "options": list(opts), "correct": key}
                      for qid, text, opts, true, key, b, w in ITEMS]}
json.dump(inst, open(out + "/instrument.json", "w", encoding="utf-8"), indent=1)
