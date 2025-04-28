import os
from dotenv import load_dotenv
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer
from transformers import DataCollatorForLanguageModeling, BitsAndBytesConfig
from datasets import Dataset
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
import json

# Load environment variables
load_dotenv()
hf_token = os.getenv("HF_TOKEN")

# Configure quantization with bfloat16 for Gemma-3
quantization_config = BitsAndBytesConfig(
    load_in_8bit=True,
    bnb_8bit_compute_dtype=torch.bfloat16,  # Using bfloat16 for Gemma-3 as in original script
    llm_int8_enable_fp32_cpu_offload=True
)

# Load tokenizer from previous training stage (your existing Gemma-3 model)
tokenizer = AutoTokenizer.from_pretrained("backend/models/gemma3/dhivehi-gemma-3-1b")
tokenizer.pad_token = tokenizer.eos_token
tokenizer.padding_side = "right"

# Load the previously trained Dhivehi model as the base model
base_model = AutoModelForCausalLM.from_pretrained(
    "backend/models/gemma3/dhivehi-gemma-3-1b",  # Using your previously trained model
    device_map="auto",
    torch_dtype=torch.bfloat16,  # Using bfloat16 for Gemma-3
    quantization_config=quantization_config,
    use_cache=False,
    attn_implementation="sdpa"  # Using same attention implementation as in original
)

# Prepare model for kbit training
base_model = prepare_model_for_kbit_training(base_model)

# Create a new LoRA configuration that combines the strengths of both scripts
lora_config = LoraConfig(
    r=64,  # Increased rank from second script (was 16)
    lora_alpha=128,  # Increased alpha from second script (was 32)
    # Use the more comprehensive target modules list from second script but maintain first script's focus
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM"
)

# Apply new LoRA adapter to prepared model
model = get_peft_model(base_model, lora_config)

# Set the model to training mode
model.train()

# Load and prepare the instruction dataset (using the approach from second script)
print("Loading instruction dataset...")
with open("backend/data/dhivehi-english-dialogue.jsonl", "r", encoding="utf-8") as f:
    data = [json.loads(line) for line in f]

# Create instruction-tuning samples with explicit Dhivehi instructions
formatted_texts = []
for item in data:
    # Add explicit instruction to respond in Dhivehi
    formatted_text = f"<start>\nuser: ޖަވާބު ދިވެހިބަހުން ދޭށެވެ (Please respond in Dhivehi)\n{item['input']}\nassistant: {item['output']}\n<end>"
    formatted_texts.append(formatted_text)

print(f"Created {len(formatted_texts)} formatted examples")

# Create dataset
dataset = Dataset.from_dict({"text": formatted_texts})

# Define tokenization function for instruction tuning
def tokenize_function(examples):
    return tokenizer(
        examples["text"],
        padding="max_length",
        truncation=True,
        max_length=512,  # Increased from 256 to match first script
        return_tensors="pt"
    )

# Tokenize dataset
tokenized_datasets = dataset.map(tokenize_function, batched=True, remove_columns=["text"])

# Split dataset
split_datasets = tokenized_datasets.train_test_split(test_size=0.1)
print(f"Split dataset into {len(split_datasets['train'])} training and {len(split_datasets['test'])} test examples")

# Data collator
data_collator = DataCollatorForLanguageModeling(
    tokenizer=tokenizer,
    mlm=False
)

# Training arguments combining the best of both scripts
training_args = TrainingArguments(
    output_dir="backend/models/gemma3/finetune-checkpoints",
    per_device_train_batch_size=1,
    per_device_eval_batch_size=1,
    gradient_accumulation_steps=8,
    num_train_epochs=5,
    logging_steps=10,
    save_strategy="steps",
    save_steps=20,  # Keep frequent checkpoints as in first script
    save_total_limit=5,  # Keep more checkpoints
    report_to="none",
    fp16=False,  # Disabled as in first script
    bf16=True,  # Using bfloat16 for Gemma-3
    learning_rate=8e-5,  # Using increased learning rate from first script
    weight_decay=0.01,
    warmup_steps=50,
    eval_strategy="steps",
    eval_steps=20,
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss",
    greater_is_better=False,
    remove_unused_columns=False  # Important for handling the data format
)

# Custom Trainer class to prevent model device movement (from first script)
class NoMovingTrainer(Trainer):
    def move_model_to_device(self, model, device):
        # Override to do nothing as model is already distributed
        pass

# Initialize trainer
trainer = NoMovingTrainer(
    model=model,
    args=training_args,
    train_dataset=split_datasets["train"],
    eval_dataset=split_datasets["test"],
    data_collator=data_collator
)

# Print trainable parameters info
model.print_trainable_parameters()

# Train model
print("Starting training...")
trainer.train()

# Save the final fine-tuned model
model_save_path = "backend/models/gemma3/fine-tuned-dhivehi-gemma-3-1b"
model.save_pretrained(model_save_path)
tokenizer.save_pretrained(model_save_path)
print(f"Model and tokenizer saved to {model_save_path}")