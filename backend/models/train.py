import os
from dotenv import load_dotenv
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer
from transformers import DataCollatorForLanguageModeling, BitsAndBytesConfig
from datasets import load_dataset
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
import json

# Load environment variables
load_dotenv()
hf_token = os.getenv("HF_TOKEN")

# Configure quantization
quantization_config = BitsAndBytesConfig(
    load_in_8bit=True,
    bnb_8bit_compute_dtype=torch.bfloat16, 
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
    torch_dtype=torch.bfloat16, 
    quantization_config=quantization_config,
    use_cache=False,
    attn_implementation="sdpa" 
)

# Prepare model for training with PEFT
model = prepare_model_for_kbit_training(model)

# Define LoRA configuration with improved parameters - increased capacity
lora_config = LoraConfig(
    r=64,              
    lora_alpha=128,   
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM"
)

# Apply LoRA adaptation
model = get_peft_model(model, lora_config)

# Load the processed datasets from JSONL files
dataset = load_dataset(
    "json",
    data_files={
        "train": "backend/data/processed/gemma3/train.jsonl",  # Updated path from gemma to gemma3
        "validation": "backend/data/processed/gemma3/validation.jsonl"  # Updated path
    }
)

print(f"Loaded {len(dataset['train'])} training examples and {len(dataset['validation'])} validation examples")

# Print a sample to understand the structure
print("\nExamining dataset structure:")
if len(dataset['train']) > 0:
    sample = dataset['train'][0]
    print(f"Sample keys: {list(sample.keys())}")
    for key in sample.keys():
        print(f"  {key} type: {type(sample[key])}")
        if isinstance(sample[key], dict) and 'messages' in sample[key]:
            print(f"  Found messages in {key}!")

# Function to preprocess the data to add explicit instructions for Dhivehi output
def format_chat_data(example):
    """
    Format the message structure into a ChatML format that Gemma can understand
    """
    try:
        # The format seems to have messages directly in the example
        if 'messages' in example:
            messages = example['messages']
        # Or it might be nested in a field
        elif any(isinstance(example.get(k), dict) and 'messages' in example.get(k) for k in example):
            for k in example:
                if isinstance(example[k], dict) and 'messages' in example[k]:
                    messages = example[k]['messages']
                    break
        else:
            # If we can't find messages, try to parse from any JSON strings
            for k, v in example.items():
                if isinstance(v, str) and v.startswith('{"messages":'):
                    try:
                        data = json.loads(v)
                        messages = data.get('messages', [])
                        break
                    except:
                        pass
            else:
                # If still not found, use empty messages
                messages = []
        
        # Check if we need to add Dhivehi instruction
        if len(messages) > 0 and messages[0]['role'] == 'user':
            # Check if we need to add Dhivehi instruction to the first user message
            if "ދިވެހި ބަހުން" not in messages[0]['content'] and "respond in Dhivehi" not in messages[0]['content'].lower():
                # Add instruction to respond in Dhivehi
                messages[0]['content'] = "ޖަވާބު ދިވެހިބަހުން ދޭށެވެ (Please respond in Dhivehi)\n" + messages[0]['content']
        
        # Format as ChatML
        formatted_text = ""
        for message in messages:
            role = message['role']
            content = message['content']
            
            if role == 'user':
                formatted_text += f"<start>\nuser: {content}\n"
            elif role == 'assistant':
                formatted_text += f"assistant: {content}\n"
        
        # End the sequence
        formatted_text += "<end>"
        
        return {"text": formatted_text}
    except Exception as e:
        print(f"Error formatting example: {str(e)}")
        # Return a fallback empty text to avoid breaking the training
        return {"text": ""}

# Apply the chat formatting
formatted_dataset = dataset.map(
    format_chat_data,
    desc="Formatting chat data with Dhivehi instructions"
)

print("Formatted dataset to ChatML format with Dhivehi instructions")

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
# Determine which columns to remove based on what's in the dataset
columns_to_remove = []
if "text" in formatted_dataset["train"].column_names:
    columns_to_remove.append("text")
if "messages" in formatted_dataset["train"].column_names:
    columns_to_remove.append("messages")
# Add any other columns that might exist
for col in formatted_dataset["train"].column_names:
    if col not in ["input_ids", "attention_mask", "labels"] and col not in columns_to_remove:
        columns_to_remove.append(col)

print(f"Columns to remove: {columns_to_remove}")

tokenized_datasets = formatted_dataset.map(
    tokenize_function,
    batched=True,
    remove_columns=columns_to_remove
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
    num_train_epochs=5,         
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

# Save the fine-tuned model to a more consistent path
model_save_path = "backend/models/gemma3/dhivehi-gemma-3-1b"  # Updated path to match directory structure
model.save_pretrained(model_save_path)
tokenizer.save_pretrained(model_save_path)
print(f"Model and tokenizer saved to {model_save_path}")