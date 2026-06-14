import argparse
import json
import os
import subprocess
import sys
from typing import Any, Dict, List


def load_json(path: str) -> Any:
    with open(path, "r") as f:
        return json.load(f)


def save_json(data: Any, path: str) -> None:
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def normalize_id(value: Any) -> str:
    return str(value).strip()


def load_hadm_ids(args: argparse.Namespace) -> List[str]:
    ids: List[str] = []

    if args.hadm_ids:
        ids.extend([x.strip() for x in args.hadm_ids.split(",") if x.strip()])

    if args.hadm_ids_file:
        with open(args.hadm_ids_file, "r") as f:
            ids.extend([line.strip() for line in f if line.strip()])

    if not ids:
        raise ValueError("Provide --hadm_ids or --hadm_ids_file.")

    return [normalize_id(x) for x in ids]


def index_patient_profiles(raw_profiles: Any) -> Dict[str, Dict[str, Any]]:
    profiles_by_id: Dict[str, Dict[str, Any]] = {}

    if isinstance(raw_profiles, list):
        for profile in raw_profiles:
            hadm_id = normalize_id(profile["hadm_id"])
            profiles_by_id[hadm_id] = profile

    elif isinstance(raw_profiles, dict):
        for key, profile in raw_profiles.items():
            if not isinstance(profile, dict):
                raise ValueError("Unsupported patient_profile.json format.")

            hadm_id = normalize_id(profile.get("hadm_id", key))
            profiles_by_id[hadm_id] = profile

    else:
        raise ValueError("patient_profile.json must be either a list or a dict.")

    return profiles_by_id


def build_hydra_command(args: argparse.Namespace, subset_file_name: str, num_scenarios: int) -> List[str]:
    cmd = [
        sys.executable,
        "run_simulation.py",

        f"experiment.exp_name={args.exp_name}",
        f"experiment.random_seed={args.random_seed}",
        f"experiment.total_inferences={args.total_inferences}",
        f"experiment.verbose={str(args.verbose).lower()}",

        f"data.data_file_name={subset_file_name}",
        f"data.num_scenarios={num_scenarios}",
        f"data.patient_prompt_file={args.patient_prompt_file}",
        f"data.doctor_prompt_file={args.doctor_prompt_file}",

        f"patient_agent.api_type={args.patient_api_type}",
        f"patient_agent.backend={args.patient_backend}",
        f"patient_agent.persona.cefr_type={args.cefr_type}",
        f"patient_agent.persona.personality_type={args.personality_type}",
        f"patient_agent.persona.recall_level_option={args.recall_level_type}",
        f"patient_agent.persona.dazed_level_option={args.dazed_level_type}",

        f"doctor_agent.api_type={args.doctor_api_type}",
        f"doctor_agent.backend={args.doctor_backend}",
        f"doctor_agent.max_infs={args.total_inferences}",
        f"doctor_agent.top_k_diagnosis={args.top_k_diagnosis}",
    ]

    if args.patient_temperature is not None:
        cmd.append(f"patient_agent.params.temperature={args.patient_temperature}")

    if args.doctor_temperature is not None:
        cmd.append(f"doctor_agent.params.temperature={args.doctor_temperature}")

    return cmd


def main(args: argparse.Namespace) -> None:
    src_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(src_dir)

    hadm_ids = load_hadm_ids(args)

    full_profile_path = os.path.join(args.data_dir, f"{args.data_file_name}.json")
    raw_profiles = load_json(full_profile_path)
    profiles_by_id = index_patient_profiles(raw_profiles)

    missing_ids = [hadm_id for hadm_id in hadm_ids if hadm_id not in profiles_by_id]
    if missing_ids:
        raise ValueError(f"These hadm_id values were not found in patient profiles: {missing_ids}")

    selected_profiles = [profiles_by_id[hadm_id] for hadm_id in hadm_ids]

    subset_file_name = f"_selected_{args.exp_name}"
    subset_path = os.path.join(args.data_dir, f"{subset_file_name}.json")

    save_json(selected_profiles, subset_path)

    print(f"Prepared selected patient file: {subset_path}")
    print(f"Number of selected patients: {len(selected_profiles)}")
    print("Selected hadm_id values:")
    for hadm_id in hadm_ids:
        print(f"  - {hadm_id}")

    cmd = build_hydra_command(
        args=args,
        subset_file_name=subset_file_name,
        num_scenarios=len(selected_profiles),
    )

    print("\nRunning command:")
    print(" ".join(cmd))
    print()

    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run existing PatientSim run_simulation.py for selected hadm_id values."
    )

    parser.add_argument("--exp_name", type=str, required=True)

    parser.add_argument("--hadm_ids", type=str, default=None)
    parser.add_argument("--hadm_ids_file", type=str, default=None)

    parser.add_argument("--data_dir", type=str, default="./data/final_data")
    parser.add_argument("--data_file_name", type=str, default="patient_profile")

    parser.add_argument(
        "--patient_prompt_file",
        type=str,
        default="initial_system_patient_w_persona_descriptive",
    )
    parser.add_argument(
        "--doctor_prompt_file",
        type=str,
        default="initial_system_doctor",
    )

    parser.add_argument("--patient_api_type", type=str, default="vertexai")
    parser.add_argument("--patient_backend", type=str, default="gemini-2.5-flash")

    parser.add_argument("--doctor_api_type", type=str, default="vertexai")
    parser.add_argument("--doctor_backend", type=str, default="gemini-2.5-flash")

    parser.add_argument("--cefr_type", type=str, default="C")
    parser.add_argument("--personality_type", type=str, default="plain")
    parser.add_argument("--recall_level_type", type=str, default="high")
    parser.add_argument("--dazed_level_type", type=str, default="normal")

    parser.add_argument("--total_inferences", type=int, default=30)
    parser.add_argument("--top_k_diagnosis", type=int, default=5)

    parser.add_argument("--patient_temperature", type=float, default=None)
    parser.add_argument("--doctor_temperature", type=float, default=None)

    parser.add_argument("--random_seed", type=int, default=42)
    parser.add_argument("--verbose", action="store_true")

    args = parser.parse_args()
    main(args)