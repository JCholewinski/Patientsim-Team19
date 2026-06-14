## Usage

All commands below should be run from the `src` directory:

```bash
cd src
```

---

## 1. Prepare a patient ID file

Create a text file with selected patient admission IDs. Each ID should be placed in a separate line:

```bash
cat > hadm_ids_smoke_test.txt <<EOF
HADM_ID_1
HADM_ID_2
HADM_ID_3
EOF
```

Replace `HADM_ID_1`, `HADM_ID_2`, and `HADM_ID_3` with valid `hadm_id` values from:

```text
data/final_data/patient_profile.json
```

---

## 2. Run a small end-to-end simulation

This command runs a short simulation for selected patients using the descriptive patient prompt.

```bash
python run_batch_simulations.py \
  --exp_name descriptive_smoke_test \
  --hadm_ids_file hadm_ids_smoke_test.txt \
  --cefr_type C \
  --personality_type plain \
  --recall_level_type high \
  --dazed_level_type normal \
  --patient_prompt_file initial_system_patient_w_persona_descriptive \
  --patient_api_type genai \
  --patient_backend gemini-2.5-flash \
  --doctor_api_type genai \
  --doctor_backend gemini-2.5-flash \
  --total_inferences 5 \
  --verbose
```

After the command finishes, the generated dialogue file should appear at:

```text
results/descriptive_smoke_test/outputs/dialogue.jsonl
```

Check it with:

```bash
ls results/descriptive_smoke_test/outputs/dialogue.jsonl
```

---

## 3. Run the LLM evaluator

After generating `dialogue.jsonl`, run the enhanced realism evaluator:

```bash
python ./eval/llm_eval.py \
  --trg_exp_name "descriptive_smoke_test" \
  --evaluator gemini-2.5-flash \
  --evaluator_api_type genai \
  --eval_enhanced_realism
```

The evaluation output should be saved as:

```text
results/descriptive_smoke_test/gemini-2.5-flash_enhanced_realism_Patient.json
```

Check it with:

```bash
ls results/descriptive_smoke_test/gemini-2.5-flash_enhanced_realism_Patient.json
```

If the file already exists and the evaluator refuses to overwrite it, remove the old file and run the evaluator again:

```bash
rm results/descriptive_smoke_test/gemini-2.5-flash_enhanced_realism_Patient.json
```

---

## 4. Analyze evaluation scores

After evaluation, run:

```bash
python analyze_eval_scores.py
```

The script reads the evaluator output and creates an Excel file with grouped results and metric averages.

Expected output:

```text
results/descriptive_smoke_test/evaluation_group_results.xlsx
```

The Excel file contains:

```text
Summary long
Summary wide
Cerebral infarction
Severe symptoms
Normal patients
All
Group definitions
```

---

## Full experiment

For a larger experiment, create a separate file with the patient IDs that should be included:

```bash
cat > hadm_ids_full_test.txt <<EOF
HADM_ID_1
HADM_ID_2
HADM_ID_3
HADM_ID_4
HADM_ID_5
EOF
```

Then run:

```bash
python run_batch_simulations.py \
  --exp_name descriptive_full_test \
  --hadm_ids_file hadm_ids_full_test.txt \
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

Then evaluate it:

```bash
python ./eval/llm_eval.py \
  --trg_exp_name "descriptive_full_test" \
  --evaluator gemini-2.5-flash \
  --evaluator_api_type genai \
  --eval_enhanced_realism
```

Then update `EVAL_PATH` in `analyze_eval_scores.py` if needed and run:

```bash
python analyze_eval_scores.py
```

---

## Patient groups used in analysis

The analysis script supports grouping patients into categories, for example:

```python
CEREBRAL_INFARCTION_IDS = [
    # Add hadm_id values for cerebral infarction cases here.
]

SEVERE_SYMPTOMS_IDS = [
    # Add hadm_id values for severe symptom / speaking difficulty cases here.
]

NORMAL_PATIENT_IDS = [
    # Add hadm_id values for normal comparison cases here.
]
```

These lists should be edited inside `analyze_eval_scores.py` before running the analysis script.

---

## Expected outputs

After running the smoke test pipeline, the following files should exist:

```text
src/results/descriptive_smoke_test/outputs/dialogue.jsonl
src/results/descriptive_smoke_test/gemini-2.5-flash_enhanced_realism_Patient.json
src/results/descriptive_smoke_test/evaluation_group_results.xlsx
```

For the full experiment:

```text
src/results/descriptive_full_test/outputs/dialogue.jsonl
src/results/descriptive_full_test/gemini-2.5-flash_enhanced_realism_Patient.json
src/results/descriptive_full_test/evaluation_group_results.xlsx
```
