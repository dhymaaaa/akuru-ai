import os
import json
from dotenv import load_dotenv
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer
from transformers import DataCollatorForLanguageModeling, BitsAndBytesConfig
from datasets import Dataset
from peft import LoraConfig, get_peft_model, PeftModel, prepare_model_for_kbit_training

# Load environment variables
load_dotenv()
hf_token = os.getenv("HF_TOKEN")

# Configure quantization
quantization_config = BitsAndBytesConfig(
    load_in_8bit=True,
    bnb_8bit_compute_dtype=torch.float16
)

# Load tokenizer from second training stage
tokenizer = AutoTokenizer.from_pretrained("backend/models/dhivehi-gemma-2b")
tokenizer.pad_token = tokenizer.eos_token
tokenizer.padding_side = "right"

# Load base model with second stage LoRA weights
base_model = AutoModelForCausalLM.from_pretrained(
    "google/gemma-2b",
    token=hf_token,
    device_map="auto",
    quantization_config=quantization_config,
    use_cache=False
)

# Prepare model for kbit training
base_model = prepare_model_for_kbit_training(base_model)

# Create a new LoRA configuration instead of loading existing weights
lora_config = LoraConfig(
    r=16,
    lora_alpha=32,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM"
)

# Apply new LoRA adapter to prepared model
model = get_peft_model(base_model, lora_config)

# Set the model to training mode
model.train()

# Load and prepare the instruction dataset
with open("backend/data/processed/dhivehi-english-dialogue.jsonl", "r", encoding="utf-8") as f:
    data = [json.loads(line) for line in f]

# Create instruction-tuning samples
formatted_texts = []
for item in data:
    formatted_text = f"Input: {item['input']}\nOutput: {item['output']}"
    formatted_texts.append(formatted_text)

# Create dataset
dataset = Dataset.from_dict({"text": formatted_texts})

# Define tokenization function for instruction tuning
def tokenize_function(examples):
    return tokenizer(
        examples["text"],
        padding="max_length",
        truncation=True,
        max_length=256,
        return_tensors="pt"
    )

# Tokenize dataset
tokenized_datasets = dataset.map(tokenize_function, batched=True, remove_columns=["text"])

# Split dataset
split_datasets = tokenized_datasets.train_test_split(test_size=0.1)

# Data collator
data_collator = DataCollatorForLanguageModeling(
    tokenizer=tokenizer,
    mlm=False
)

# Training arguments
training_args = TrainingArguments(
    output_dir="backend/models/finetune-checkpoints",
    eval_strategy="epoch",
    save_strategy="epoch",
    per_device_train_batch_size=1,
    per_device_eval_batch_size=1,
    gradient_accumulation_steps=8,
    num_train_epochs=5,
    logging_steps=10,
    save_total_limit=2,
    report_to="none",
    fp16=True,
    learning_rate=5e-5,
    warmup_steps=50,
    remove_unused_columns=False,  # Added this to prevent column removal issues
)

# Initialize trainer - simplified trainer without custom training_step
class NoMovingTrainer(Trainer):
    def move_model_to_device(self, model, device):
        pass

# Initialize trainer
trainer = NoMovingTrainer(
    model=model,
    args=training_args,
    train_dataset=split_datasets["train"],
    eval_dataset=split_datasets["test"],
    data_collator=data_collator
)

# Train model
trainer.train()

# Save the final fine-tuned model
model.save_pretrained("backend/models/fine-tuned-dhivehi-gemma-2b")
tokenizer.save_pretrained("backend/models/fine-tuned-dhivehi-gemma-2b")