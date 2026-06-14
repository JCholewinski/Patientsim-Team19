import json
import os
import re
import pandas as pd


# =========================
# CONFIG
# =========================

EVAL_PATH = "results/2026-06-11-12-04-05_base_30_patients_cefr_base/gemini-3.1-flash-lite-preview_enhanced_realism_Patient.json"

OUTPUT_EXCEL = os.path.join(
    os.path.dirname(EVAL_PATH),
    "evaluation_group_results.xlsx"
)

CEREBRAL_INFARCTION_IDS = [
    "22648247",
    "20118599",
    "21458984",
    "24350216",
    "24054450",
    "24170109",
    "26135366",
    "26658062",
    "27675088",
    "27700966",
    "20041385",
    "25826269",
    "21031714",
    "23604831",
    "28162080",
]

# Tu wpisujesz ID, które NIE są cerebral infarction.
# Możesz zostawić puste [], wtedy kod sam weźmie wszystkie pozostałe ID z pliku.
OTHER_IDS = []


# =========================
# HELPERS
# =========================

def load_eval_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_result_score(value):
    """
    Obsługuje formaty:
    - "[REASON]: ... [RESULT]: 4"
    - {"result": 4}
    - {"score": 4}
    - 4
    """
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, dict):
        if "result" in value:
            return float(value["result"])
        if "score" in value:
            return float(value["score"])
        return None

    if isinstance(value, str):
        match = re.search(r"\[RESULT\]\s*:\s*([0-9]+(?:\.[0-9]+)?)", value)
        if match:
            return float(match.group(1))
        return None

    return None


def get_all_patient_ids(eval_data):
    patient_ids = set()

    for metric_name, metric_results in eval_data.items():
        if isinstance(metric_results, dict):
            patient_ids.update(str(pid) for pid in metric_results.keys())

    return sorted(patient_ids)


def build_patient_table(eval_data, patient_ids, group_name):
    rows = []

    metrics = list(eval_data.keys())

    for patient_id in patient_ids:
        row = {
            "group": group_name,
            "hadm_id": str(patient_id),
        }

        for metric in metrics:
            raw_value = eval_data.get(metric, {}).get(str(patient_id))
            row[metric] = extract_result_score(raw_value)

        rows.append(row)

    return pd.DataFrame(rows)


def build_summary_table(group_tables):
    rows = []

    for group_name, df in group_tables.items():
        metric_columns = [
            col for col in df.columns
            if col not in ["group", "hadm_id"]
        ]

        row = {
            "group": group_name,
            "n_patients": len(df),
        }

        for metric in metric_columns:
            row[f"{metric}_mean"] = pd.to_numeric(df[metric], errors="coerce").mean()
            row[f"{metric}_n_available"] = pd.to_numeric(df[metric], errors="coerce").notna().sum()

        rows.append(row)

    return pd.DataFrame(rows)


def build_long_summary_table(group_tables):
    rows = []

    for group_name, df in group_tables.items():
        metric_columns = [
            col for col in df.columns
            if col not in ["group", "hadm_id"]
        ]

        for metric in metric_columns:
            scores = pd.to_numeric(df[metric], errors="coerce")

            rows.append({
                "group": group_name,
                "metric": metric,
                "mean_score": scores.mean(),
                "n_available": scores.notna().sum(),
                "n_patients": len(df),
            })

    return pd.DataFrame(rows)


# =========================
# MAIN
# =========================

def main():
    eval_data = load_eval_file(EVAL_PATH)

    all_ids = get_all_patient_ids(eval_data)

    cerebral_ids = [str(x) for x in CEREBRAL_INFARCTION_IDS]

    if OTHER_IDS:
        other_ids = [str(x) for x in OTHER_IDS]
    else:
        other_ids = [
            patient_id for patient_id in all_ids
            if patient_id not in cerebral_ids
        ]

    cerebral_df = build_patient_table(
        eval_data=eval_data,
        patient_ids=cerebral_ids,
        group_name="Cerebral infarction",
    )

    other_df = build_patient_table(
        eval_data=eval_data,
        patient_ids=other_ids,
        group_name="Others",
    )

    all_df = build_patient_table(
        eval_data=eval_data,
        patient_ids=all_ids,
        group_name="All",
    )

    group_tables = {
        "Cerebral infarction": cerebral_df,
        "Others": other_df,
        "All": all_df,
    }

    summary_wide_df = build_summary_table(group_tables)
    summary_long_df = build_long_summary_table(group_tables)

    group_definitions_df = pd.DataFrame({
        "Cerebral infarction IDs": pd.Series(cerebral_ids),
        "Other IDs": pd.Series(other_ids),
    })

    with pd.ExcelWriter(OUTPUT_EXCEL) as writer:
        summary_long_df.to_excel(writer, sheet_name="Summary long", index=False)
        summary_wide_df.to_excel(writer, sheet_name="Summary wide", index=False)
        cerebral_df.to_excel(writer, sheet_name="Cerebral infarction", index=False)
        other_df.to_excel(writer, sheet_name="Others", index=False)
        all_df.to_excel(writer, sheet_name="All", index=False)
        group_definitions_df.to_excel(writer, sheet_name="Group definitions", index=False)

    print(f"Saved results to: {OUTPUT_EXCEL}")

    print("\nSummary:")
    print(summary_long_df)

    missing_cerebral_ids = [pid for pid in cerebral_ids if pid not in all_ids]
    if missing_cerebral_ids:
        print("\nWarning: these Cerebral infarction IDs were not found in the evaluation file:")
        print(missing_cerebral_ids)


if __name__ == "__main__":
    main()