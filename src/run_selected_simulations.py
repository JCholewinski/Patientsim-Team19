import argparse
import json
import os
import sys
import time
from typing import Any, Dict, List

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agent.doctor_agent import DoctorAgent
from agent.patient_agent import PatientAgent
from utils import save_to_dialogue, set_seed, detect_termination


def make_client_compatible(client):
    """
    PatientAgent and DoctorAgent call:
        self.client(messages, model=self.model, **client_params)

    Some backends already know the model / temperature internally and do not
    accept keyword arguments such as 'model', 'temperature', or 'seed'.
    This wrapper keeps the original agent code unchanged.
    """

    def wrapped_client(messages, **kwargs):
        try:
            return client(messages, **kwargs)

        except TypeError as e:
            error_msg = str(e)

            if "unexpected keyword argument" not in error_msg:
                raise

            # Remove all optional kwargs and call the backend only with messages.
            # This is needed for backends whose lambda signature is simply:
            # lambda messages: ...
            return client(messages)

    return wrapped_client

def load_json(path: str) -> Any:
    with open(path, "r") as f:
        return json.load(f)


def normalize_hadm_id(value: Any) -> str:
    return str(value).strip()


def load_hadm_ids(args: argparse.Namespace) -> List[str]:
    ids: List[str] = []

    if args.hadm_ids:
        ids.extend([x.strip() for x in args.hadm_ids.split(",") if x.strip()])

    if args.hadm_ids_file:
        with open(args.hadm_ids_file, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    ids.append(line)

    if not ids:
        raise ValueError("You must provide --hadm_ids or --hadm_ids_file.")

    return [normalize_hadm_id(x) for x in ids]


def load_scenarios_by_hadm_id(data_path: str) -> Dict[str, Dict[str, Any]]:
    raw_data = load_json(data_path)
    scenarios_by_id: Dict[str, Dict[str, Any]] = {}

    if isinstance(raw_data, list):
        for scenario in raw_data:
            hadm_id = normalize_hadm_id(scenario["hadm_id"])
            scenarios_by_id[hadm_id] = scenario

    elif isinstance(raw_data, dict):
        for key, scenario in raw_data.items():
            if not isinstance(scenario, dict):
                raise ValueError("Unsupported patient_profile.json structure.")

            hadm_id = normalize_hadm_id(scenario.get("hadm_id", key))
            scenarios_by_id[hadm_id] = scenario

    else:
        raise ValueError("patient_profile.json must be a list or a dict.")

    return scenarios_by_id


def run_single_dialogue(
    scenario: Dict[str, Any],
    args: argparse.Namespace,
    save_dir: str,
) -> None:
    patient_agent = PatientAgent(
        patient_profile=scenario,
        backend_str=args.patient_backend,
        backend_api_type=args.patient_api_type,
        prompt_dir=args.prompt_dir,
        prompt_file=args.patient_prompt_file,
        num_word_sample=args.num_word_sample,
        cefr_type=args.cefr_type,
        personality_type=args.personality_type,
        recall_level_type=args.recall_level_type,
        dazed_level_type=args.dazed_level_type,
        client_params={
            "temperature": args.patient_temperature,
            "seed": args.random_seed,
        },
        verbose=args.verbose,
    )

    patient_agent.client = make_client_compatible(patient_agent.client)

    doctor_agent = DoctorAgent(
        max_infs=args.doctor_max_infs,
        top_k_diagnosis=args.top_k_diagnosis,
        backend_str=args.doctor_backend,
        backend_api_type=args.doctor_api_type,
        prompt_dir=args.prompt_dir,
        prompt_file=args.doctor_prompt_file,
        patient_info=scenario,
        client_params={
            "temperature": args.doctor_temperature,
            "seed": args.random_seed,
        },
        verbose=args.verbose,
    )

    doctor_agent.client = make_client_compatible(doctor_agent.client)

    start_time = time.time()

    dialog_history = [{"role": "Doctor", "content": doctor_agent.doctor_greet}]
    doctor_agent.messages.append(
        {"role": "assistant", "content": doctor_agent.doctor_greet}
    )

    if args.verbose:
        print(f"\n=== hadm_id: {scenario['hadm_id']} ===")
        print(f"Doctor: {doctor_agent.doctor_greet}")

    for inf_idx in range(args.total_inferences):
        patient_response = patient_agent.inference(dialog_history[-1]["content"])
        dialog_history.append({"role": "Patient", "content": patient_response})

        if args.verbose:
            print(
                f"Patient [{inf_idx + 1}/{args.total_inferences}]: "
                f"{patient_response}"
            )

        if inf_idx == args.total_inferences - 1:
            doctor_input = (
                dialog_history[-1]["content"]
                + "\nThis is the final turn. Now, you must provide your top5 differential diagnosis."
            )
        else:
            doctor_input = dialog_history[-1]["content"]

        doctor_response = doctor_agent.inference(doctor_input)
        dialog_history.append({"role": "Doctor", "content": doctor_response})

        if args.verbose:
            print(
                f"Doctor [{inf_idx + 1}/{args.total_inferences}]: "
                f"{doctor_response}"
            )

        if detect_termination(doctor_response):
            break

        if args.sleep_seconds > 0:
            time.sleep(args.sleep_seconds)

    end_time = time.time()

    dialog_info = {
        "hadm_id": scenario["hadm_id"],
        "doctor_engine_name": doctor_agent.backend,
        "patient_engine_name": patient_agent.backend,
        "doctor_api_type": doctor_agent.backend_api_type,
        "patient_api_type": patient_agent.backend_api_type,
        "cefr_type": patient_agent.patient_profile["cefr_option"],
        "personality_type": patient_agent.patient_profile["personality_option"],
        "recall_level_type": patient_agent.patient_profile["recall_level_option"],
        "dazed_level_type": patient_agent.patient_profile["dazed_level_option"],
        "diagnosis": patient_agent.diagnosis,
        "dialog_history": dialog_history,
        "patient_token_log": patient_agent.token_log,
        "doctor_token_log": doctor_agent.token_log,
        "elapsed_time": end_time - start_time,
    }

    save_to_dialogue(dialog_info, os.path.join(save_dir, "dialogue.jsonl"))


def main(args: argparse.Namespace) -> None:
    set_seed(args.random_seed)

    data_path = os.path.join(args.data_dir, f"{args.data_file_name}.json")
    scenarios_by_id = load_scenarios_by_hadm_id(data_path)
    hadm_ids = load_hadm_ids(args)

    save_dir = os.path.join(args.result_dir, args.exp_name, "outputs")
    os.makedirs(save_dir, exist_ok=True)

    output_file = os.path.join(save_dir, "dialogue.jsonl")

    if args.overwrite and os.path.exists(output_file):
        os.remove(output_file)

    missing_ids = [hadm_id for hadm_id in hadm_ids if hadm_id not in scenarios_by_id]
    if missing_ids:
        raise ValueError(f"These hadm_id values were not found in data: {missing_ids}")

    for hadm_id in hadm_ids:
        scenario = scenarios_by_id[hadm_id]
        run_single_dialogue(scenario, args, save_dir)

    print(f"\nSaved dialogues to: {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run PatientSim conversations for selected hadm_id values."
    )

    parser.add_argument("--exp_name", type=str, required=True)

    parser.add_argument(
        "--hadm_ids",
        type=str,
        default=None,
        help="Comma-separated list of hadm_id values, e.g. 20098012,20118599",
    )
    parser.add_argument(
        "--hadm_ids_file",
        type=str,
        default=None,
        help="Path to a txt file with one hadm_id per line.",
    )

    parser.add_argument("--data_dir", type=str, default="./data/final_data")
    parser.add_argument("--data_file_name", type=str, default="patient_profile")

    parser.add_argument("--prompt_dir", type=str, default="./prompts/simulation")
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

    parser.add_argument("--result_dir", type=str, default="./results")
    parser.add_argument("--overwrite", action="store_true")

    parser.add_argument("--total_inferences", type=int, default=30)
    parser.add_argument("--doctor_max_infs", type=int, default=30)
    parser.add_argument("--top_k_diagnosis", type=int, default=5)
    parser.add_argument("--num_word_sample", type=int, default=10)

    parser.add_argument("--doctor_api_type", type=str, default="genai")
    parser.add_argument("--doctor_backend", type=str, default="gemini-2.5-flash")
    parser.add_argument("--doctor_temperature", type=float, default=1.0)

    parser.add_argument("--patient_api_type", type=str, default="genai")
    parser.add_argument("--patient_backend", type=str, default="gemini-2.5-flash")
    parser.add_argument("--patient_temperature", type=float, default=0.7)

    parser.add_argument("--cefr_type", type=str, default="B")
    parser.add_argument("--personality_type", type=str, default="plain")
    parser.add_argument("--recall_level_type", type=str, default="high")
    parser.add_argument("--dazed_level_type", type=str, default="normal")

    parser.add_argument("--random_seed", type=int, default=42)
    parser.add_argument("--sleep_seconds", type=float, default=1.0)
    parser.add_argument("--verbose", action="store_true")

    args = parser.parse_args()
    main(args)