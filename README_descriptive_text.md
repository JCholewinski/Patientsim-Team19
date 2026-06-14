# PatientSim-Team19

This repository extends PatientSim with symptom-related descriptive text in simulated patient responses and an enhanced LLM-based evaluator for dialogue realism.

The goal of the project is to make simulated patients more realistic by allowing short descriptive text in asterisks when it reflects observable symptoms from the current Emergency Department visit, such as slurred speech, facial droop, visible weakness, pain-related movement, labored breathing, confusion, or distress.

The repository includes:

* descriptive patient prompts,
* patient-doctor dialogue simulation,
* batch simulation for selected patient admission IDs,
* enhanced realism evaluation,
* score collection and grouped result summaries.

---

## Repository structure

```text
src/
├── run_simulation.py
├── run_batch_simulations.py
├── collect_scores.py
├── models.py
├── eval/
│   └── llm_eval.py
├── prompts/
│   ├── simulation/
│   │   ├── initial_system_doctor.txt
│   │   ├── initial_system_patient_w_persona.txt
│   │   ├── initial_system_patient_w_persona_uti.txt
│   │   └── initial_system_patient_w_persona_descriptive.txt
│   └── eval/
│       ├── eval_dialogue_user_enhanced_realism.txt
│       └── llm_eval_metrics_enhanced_realism.json
├── data/
│   └── final_data/
│       └── patient_profile.json
└── results/
```

---

## Installation

Run the following commands from the root directory of the repository.

```bash
conda create -n patientsim python=3.11 -y
conda activate patientsim
pip install -r requirements.txt
pip install hydra-core google-genai python-dotenv openai jsonlines numpy pyyaml pandas openpyxl torch
```

For `micromamba`, use:

```bash
micromamba create -n patientsim python=3.11 -y
micromamba activate patientsim
pip install -r requirements.txt
pip install hydra-core google-genai python-dotenv openai jsonlines numpy pyyaml pandas openpyxl torch
```

---

## API setup

The commands below use Gemini through the `genai` backend.

For Vertex AI, authenticate first:

```bash
gcloud auth application-default login
gcloud config set project YOUR_GOOGLE_CLOUD_PROJECT_ID
```

Then set the environment variables:

```bash
export GOOGLE_GENAI_USE_VERTEXAI=true
export GOOGLE_CLOUD_PROJECT="YOUR_GOOGLE_CLOUD_PROJECT_ID"
export GOOGLE_CLOUD_LOCATION="global"
```

Check the variables:

```bash
echo $GOOGLE_GENAI_USE_VERTEXAI
echo $GOOGLE_CLOUD_PROJECT
echo $GOOGLE_CLOUD_LOCATION
```

Expected output:

```text
true
YOUR_GOOGLE_CLOUD_PROJECT_ID
global
```

---

## Data setup

The simulator expects the PatientSim patient profile file at:

```text
src/data/final_data/patient_profile.json
```

Check that the file exists:

```bash
ls src/data/final_data/patient_profile.json
```

---

## Usage

All commands below should be run from the `src` directory.

```bash
cd src
```

---

## 1. Run a small end-to-end simulation

This command runs one short simulated doctor-patient conversation using the descriptive patient prompt.

```bash
python run_simulation.py \
  experiment.exp_name=descriptive_smoke_test \
  hydra.run.dir=results/descriptive_smoke_test \
  data.num_scenarios=1 \
  experiment.total_inferences=5 \
  experiment.verbose=true \
  data.patient_prompt_file=initial_system_patient_w_persona_descriptive \
  data.doctor_prompt_file=initial_system_doctor \
  patient_agent.api_type=genai \
  patient_agent.backend=gemini-2.5-flash \
  patient_agent.params.temperature=0.7 \
  patient_agent.persona.cefr_type=C \
  patient_agent.persona.personality_type=plain \
  patient_agent.persona.recall_level_option=high \
  patient_agent.persona.dazed_level_option=normal \
  doctor_agent.api_type=genai \
  doctor_agent.backend=gemini-2.5-flash \
  doctor_agent.params.temperature=1.0 \
  doctor_agent.max_infs=5 \
  doctor_agent.top_k_diagnosis=5
```

After the command finishes, the generated dialogue file should exist at:

```text
results/descriptive_smoke_test/outputs/dialogue.jsonl
```

Check it with:

```bash
ls results/descriptive_smoke_test/outputs/dialogue.jsonl
```

Inspect the generated dialogue:

```bash
head -n 1 results/descriptive_smoke_test/outputs/dialogue.jsonl
```

---

## 2. Run the enhanced realism evaluator

After generating `dialogue.jsonl`, run:

```bash
python ./eval/llm_eval.py \
  --trg_exp_name descriptive_smoke_test \
  --evaluator gemini-2.5-flash \
  --evaluator_api_type genai \
  --eval_enhanced_realism
```

The evaluator output should be saved as:

```text
results/descriptive_smoke_test/gemini-2.5-flash_enhanced_realism_Patient.json
```

Check it with:

```bash
ls results/descriptive_smoke_test/gemini-2.5-flash_enhanced_realism_Patient.json
```

---

## 3. Collect evaluation scores

After evaluation, make sure that `EVAL_PATH` in `collect_scores.py` points to the evaluator output file:

```python
EVAL_PATH = "results/descriptive_smoke_test/gemini-2.5-flash_enhanced_realism_Patient.json"
```

Then run:

```bash
python collect_scores.py
```

The script creates grouped score tables and metric averages.

Expected output:

```text
results/descriptive_smoke_test/evaluation_group_results.xlsx
```

---

## Batch simulation for selected patients

To run selected patient cases, prepare a text file with `hadm_id` values. Each ID should be placed in a separate line.

Example file name:

```text
hadm_ids.txt
```

Example structure:

```text
HADM_ID_1
HADM_ID_2
HADM_ID_3
```

The IDs must correspond to valid patients from:

```text
data/final_data/patient_profile.json
```

Then run:

```bash
python run_batch_simulations.py \
  --exp_name descriptive_batch_test \
  --hadm_ids_file hadm_ids.txt \
  --cefr_type C \
  --personality_type plain \
  --recall_level_type high \
  --dazed_level_type normal \
  --patient_prompt_file initial_system_patient_w_persona_descriptive \
  --patient_api_type genai \
  --patient_backend gemini-2.5-flash \
  --doctor_api_type genai \
  --doctor_backend gemini-2.5-flash \
  --total_inferences 30
```

The generated results will be saved under:

```text
results/
```

using the experiment name defined with:

```text
--exp_name
```

---

## Enhanced realism metrics

The enhanced realism evaluator scores each generated dialogue using four metrics:

```text
Factual_Accuracy
Personality_Consistency
Contextual_Coherence
Clinical_Realism
```

The evaluator output has the following structure:

```json
{
  "Factual_Accuracy": {
    "HADM_ID": "[REASON]: ... [RESULT]: 4"
  },
  "Personality_Consistency": {
    "HADM_ID": "[REASON]: ... [RESULT]: 4"
  },
  "Contextual_Coherence": {
    "HADM_ID": "[REASON]: ... [RESULT]: 4"
  },
  "Clinical_Realism": {
    "HADM_ID": "[REASON]: ... [RESULT]: 4"
  }
}
```

Scores are integers from 1 to 4, where 4 is the best score.

---

## Results availability

The `results/` directory is not included in this repository.

Generated simulation outputs and evaluation results may contain patient-specific information derived from the source dataset. For this reason, generated dialogues, evaluation files, and score tables are not committed to avoid possible data leakage.

All results should be regenerated locally by following the Usage section.

After running the pipeline, generated files will appear locally under:

```text
src/results/
```

---

## Expected outputs

After a successful smoke test, the following files should exist locally:

```text
src/results/descriptive_smoke_test/outputs/dialogue.jsonl
src/results/descriptive_smoke_test/gemini-2.5-flash_enhanced_realism_Patient.json
src/results/descriptive_smoke_test/evaluation_group_results.xlsx
```

These files are generated locally and are not committed to the repository.

---

## End-to-end runnability checklist

A successful run should complete the following steps:

```text
1. Install dependencies.
2. Set Gemini or Vertex AI environment variables.
3. Confirm that patient_profile.json exists in src/data/final_data/.
4. Run run_simulation.py from src/.
5. Confirm that results/descriptive_smoke_test/outputs/dialogue.jsonl exists.
6. Run eval/llm_eval.py with --eval_enhanced_realism.
7. Confirm that the enhanced realism evaluation JSON exists.
8. Run collect_scores.py.
9. Confirm that evaluation_group_results.xlsx exists locally.
```

These steps are intended to verify that the repository contains working end-to-end code rather than only stub files.
