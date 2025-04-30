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
    r=64, 
    lora_alpha=128, 
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

# Load and prepare the instruction dataset
print("Loading instruction dataset...")
data_path = "backend/data/dhivehi-english-dialogue.jsonl"

# Check if the file exists
if not os.path.exists(data_path):
    raise FileNotFoundError(f"Dataset file not found: {data_path}")

# Load the data and print the first item to inspect format
with open(data_path, "r", encoding="utf-8") as f:
    try:
        # Read the first line to check format
        first_line = f.readline().strip()
        print("First data item for format inspection:")
        print(first_line)
        
        # Reset file pointer to start
        f.seek(0)
        
        # Load all data
        data = []
        for line in f:
            try:
                item = json.loads(line.strip())
                data.append(item)
            except json.JSONDecodeError as e:
                print(f"Error parsing line: {e}")
                continue
    except Exception as e:
        print(f"Error reading dataset: {e}")
        raise

print(f"Loaded {len(data)} data items")

# Check the structure of the first item to determine keys
if data:
    print("Keys in the first data item:", list(data[0].keys()))
    
    # Create instruction-tuning samples with the appropriate format based on data structure
    formatted_texts = []
    
    # Check if the data has the expected structure or adapt to what's available
    for item in data:
        try:
            # Option 1: If data has 'input' and 'output' keys (as expected)
            if 'input' in item and 'output' in item:
                formatted_text = f"<start>\nuser: {item['input']}\nassistant: (Please respond in Dhivehi) {item['output']}\n<end>"
            # Option 2: If data has 'messages' structure (common in chat datasets)
            elif 'messages' in item:
                user_message = ""
                assistant_message = ""
                for msg in item['messages']:
                    if msg['role'] == 'user':
                        user_message += msg['content'] + "\n"
                    elif msg['role'] == 'assistant':
                        assistant_message += msg['content'] + "\n"
                
                if user_message and assistant_message:
                    formatted_text = f"<start>\nuser: {user_message.strip()}\nassistant: (Please respond in Dhivehi) {assistant_message.strip()}\n<end>"
                else:
                    continue  # Skip if we can't extract both parts
            # Option 3: For single-turn datasets: first key is the prompt, second is the response
            elif len(item) == 2:
                keys = list(item.keys())
                formatted_text = f"<start>\nuser: {item[keys[0]]}\nassistant: (Please respond in Dhivehi) {item[keys[1]]}\n<end>"
            else:
                # If none of the above cases match, print the item and skip
                print(f"Skipping item with unexpected format: {item}")
                continue
                
            formatted_texts.append(formatted_text)
        except Exception as e:
            print(f"Error processing item {item}: {e}")
            continue

    print(f"Created {len(formatted_texts)} formatted examples")
    
    # Print a sample of the formatted text to verify
    if formatted_texts:
        print("\nSample formatted example:")
        print(formatted_texts[0])
else:
    raise ValueError("No valid data items found in the dataset")

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
    learning_rate=8e-5,  
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