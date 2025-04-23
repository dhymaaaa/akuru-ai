import os
from dotenv import load_dotenv
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer
from transformers import DataCollatorForLanguageModeling, BitsAndBytesConfig
from datasets import load_dataset
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

# Load environment variables
load_dotenv()
hf_token = os.getenv("HF_TOKEN")

# Configure quantization
quantization_config = BitsAndBytesConfig(
    load_in_8bit=True,
    bnb_8bit_compute_dtype=torch.bfloat16,  # Changed to bfloat16 to match Gemma 3
    llm_int8_enable_fp32_cpu_offload=True
)

# Load tokenizer and model
tokenizer = AutoTokenizer.from_pretrained("google/gemma-3-1b-pt", token=hf_token)
tokenizer.pad_token = tokenizer.eos_token
tokenizer.padding_side = "right"

model = AutoModelForCausalLM.from_pretrained(
    "google/gemma-3-1b-pt",
    token=hf_token,
    device_map="auto",
    torch_dtype=torch.bfloat16,  # Added torch_dtype
    quantization_config=quantization_config,
    use_cache=False,
    attn_implementation="sdpa"  # Added SDPA attention implementation
)

# Prepare model for training with PEFT
model = prepare_model_for_kbit_training(model)

# Define LoRA configuration with improved parameters - increased capacity
lora_config = LoraConfig(
    r=64,              # Increased from 32 to 64 for even more capacity
    lora_alpha=128,    # Increased from 64 to 128 to match r*2
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    lora_dropout=0.05, # Keep at 0.05 as it's already optimized
    bias="none",
    task_type="CAUSAL_LM"
)

# Apply LoRA adaptation
model = get_peft_model(model, lora_config)

# Load the processed datasets from JSONL files
dataset = load_dataset(
    "json",
    data_files={
        "train": "backend/data/processed/gemma/train.jsonl",
        "validation": "backend/data/processed/gemma/validation.jsonl"
    }
)

print(f"Loaded {len(dataset['train'])} training examples and {len(dataset['validation'])} validation examples")

# Function to preprocess the data to add explicit instructions for Dhivehi output
def add_dhivehi_instruction(example):
    # Add explicit instruction to prioritize Dhivehi in the prompt if not already present
    # Check if the text already contains some form of instruction
    original_text = example["text"]
    
    # Only modify if it doesn't already have a clear instruction
    if "ދިވެހި ބަހުން ޖަވާބު ދޭށެވެ" not in original_text and "respond in Dhivehi" not in original_text.lower():
        # Add instruction at an appropriate point in the text
        # Assuming format is roughly conversation-like
        modified_text = original_text.replace("<start>", "<start>\nޖަވާބު ދިވެހިބަހުން ދޭށެވެ (Please respond in Dhivehi)\n", 1)
        if modified_text == original_text:  # If no replacement was made
            modified_text = "ޖަވާބު ދިވެހިބަހުން ދޭށެވެ (Please respond in Dhivehi)\n" + original_text
        
        example["text"] = modified_text
    
    return example

# Apply the Dhivehi instruction preprocessing
modified_dataset = dataset.map(
    add_dhivehi_instruction,
    desc="Adding explicit Dhivehi instructions"
)

print("Added explicit Dhivehi instructions to the dataset")

# Function to tokenize the formatted data
def tokenize_function(examples):
    # The text field contains the formatted conversations
    return tokenizer(
        examples["text"],
        truncation=True,
        max_length=512,
        padding="max_length",  # Use fixed padding
        return_tensors="pt"    # Return PyTorch tensors
    )

# Tokenize datasets
tokenized_datasets = modified_dataset.map(
    tokenize_function,
    batched=True,
    remove_columns=["text"]  # Remove the original text field
)

print(f"Tokenized dataset sizes: Train={len(tokenized_datasets['train'])}, Validation={len(tokenized_datasets['validation'])}")

# Print sample of tokenized data
if len(tokenized_datasets['train']) > 0:
    print("\nSample tokenized data shape:")
    sample = tokenized_datasets['train'][0]
    for key, value in sample.items():
        print(f"{key}: {type(value)}, shape: {value.shape if hasattr(value, 'shape') else len(value)}")

# Data collator for language modeling
data_collator = DataCollatorForLanguageModeling(
    tokenizer=tokenizer,
    mlm=False
)

# Training arguments with improved settings
training_args = TrainingArguments(
    output_dir="backend/models/gemma3/checkpoints",
    per_device_train_batch_size=1,
    per_device_eval_batch_size=1,
    gradient_accumulation_steps=8,
    num_train_epochs=30,         # Increased from 15 to 30 as requested
    logging_steps=10,
    save_strategy="steps",
    save_steps=20,               # Keep frequent checkpoints
    save_total_limit=5,          # Keep more checkpoints (increased from 3 to 5)
    report_to="none",
    fp16=False,                  # Disabled FP16
    bf16=True,                   # Enabled BF16 for Gemma 3
    learning_rate=8e-5,          # Slightly increased from 5e-5 to 8e-5
    weight_decay=0.01,           # Keep weight decay at 0.01
    warmup_steps=50,             # Keep warmup steps
    eval_strategy="steps",
    eval_steps=20,               # Frequent evaluation
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss",
    greater_is_better=False,
    remove_unused_columns=False  # Important for handling the data format
)

# Custom Trainer class to prevent model device movement
class NoMovingTrainer(Trainer):
    def move_model_to_device(self, model, device):
        # Override to do nothing as model is already distributed
        pass

# Initialize trainer
trainer = NoMovingTrainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_datasets["train"],
    eval_dataset=tokenized_datasets["validation"],
    data_collator=data_collator
)

# Print trainable parameters info
model.print_trainable_parameters()

# Train model
trainer.train()

# Save the fine-tuned model
model_save_path = "backend/models/dhivehi-gemma-3-1b"
model.save_pretrained(model_save_path)
tokenizer.save_pretrained(model_save_path)
print(f"Model and tokenizer saved to {model_save_path}")