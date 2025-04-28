import os
from dotenv import load_dotenv
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from datasets import load_dataset
from tqdm import tqdm
import numpy as np
import json
from peft import PeftModel, PeftConfig
import gc

# Load environment variables
load_dotenv()
hf_token = os.getenv("HF_TOKEN")

class ModelEvaluator:
    def __init__(self, model_path, base_model_name="google/gemma-3-1b-pt", device="cuda" if torch.cuda.is_available() else "cpu"):
        self.device = device
        
        # Configure quantization to save memory
        quantization_config = BitsAndBytesConfig(
            load_in_8bit=True,
            bnb_8bit_compute_dtype=torch.bfloat16,
            llm_int8_enable_fp32_cpu_offload=True
        )
        
        # Check if path exists locally
        if not os.path.exists(model_path):
            raise ValueError(f"Model path '{model_path}' does not exist locally")
            
        # Check if this is a PEFT model
        is_peft_model = os.path.exists(os.path.join(model_path, "adapter_config.json"))
        
        if is_peft_model:
            print("Loading PEFT model...")
            # Load the base model
            self.model = AutoModelForCausalLM.from_pretrained(
                base_model_name,
                token=hf_token,
                torch_dtype=torch.bfloat16,
                device_map="auto",
                quantization_config=quantization_config,
                attn_implementation="sdpa"
            )
            
            # Load the PEFT adapter - explicitly specify it's a local path
            self.model = PeftModel.from_pretrained(
                self.model, 
                model_path, 
                local_files_only=True
            )
            
            # Note: For PEFT models, we should load the tokenizer from the base model
            self.tokenizer = AutoTokenizer.from_pretrained(
                base_model_name,
                token=hf_token
            )
        else:
            print("Loading standard model...")
            # Explicitly specify using local files
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_path,
                local_files_only=True
            )
            
            self.model = AutoModelForCausalLM.from_pretrained(
                model_path,
                torch_dtype=torch.bfloat16,
                device_map="auto",
                quantization_config=quantization_config,
                attn_implementation="sdpa",
                local_files_only=True
            )
        
        # Ensure pad token is set
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        
        self.model.eval()
        
    def calculate_perplexity(self, texts, batch_size=1):
        """Calculate perplexity of the model on given texts."""
        total_loss = 0
        total_tokens = 0
        
        with torch.no_grad():
            for i in tqdm(range(0, len(texts), batch_size), desc="Calculating perplexity"):
                batch_texts = texts[i:i + batch_size]
                
                # Tokenize with reduced max length to save memory
                inputs = self.tokenizer(
                    batch_texts,
                    return_tensors="pt",
                    padding=True,
                    truncation=True,
                    max_length=256 
                ).to(self.device)
                
                try:
                    # Get model outputs
                    outputs = self.model(**inputs, labels=inputs["input_ids"])
                    
                    # Calculate loss
                    total_loss += outputs.loss.item() * inputs["input_ids"].size(0)
                    total_tokens += inputs["input_ids"].numel()
                    
                    # Clear memory
                    del outputs, inputs
                    torch.cuda.empty_cache()
                    
                except torch.cuda.OutOfMemoryError:
                    print(f"Out of memory error at batch {i}, skipping...")
                    torch.cuda.empty_cache()
                    continue
        
        # Calculate perplexity
        if total_tokens > 0:
            perplexity = torch.exp(torch.tensor(total_loss / total_tokens))
            return perplexity.item()
        else:
            return float('inf')
    
    def generate_response(self, prompt, max_new_tokens=100, language_instruction=None):
        """Generate a response from the model with optional language instruction."""
        # Add language instruction if provided
        if language_instruction:
            prompt = f"{language_instruction}\n{prompt}"
        
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                num_return_sequences=1,
                temperature=0.7,
                top_p=0.9,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id
            )
        
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        # Return only the generated part (removing the prompt)
        return response[len(prompt):].strip()
    
    def extract_text_for_evaluation(self, example):
        """Extract text for evaluation from different data formats."""
        # Safety check for data type
        if not isinstance(example, dict):
            print(f"Cannot extract text: example is not a dictionary, type: {type(example)}")
            return ""
            
        try:
            if "messages" in example:
                # Extract user messages for evaluation
                user_texts = []
                
                # Handle case where messages might be a string instead of a list
                if isinstance(example["messages"], str):
                    try:
                        # Try to parse it as JSON
                        parsed_messages = json.loads(example["messages"])
                        messages = parsed_messages if isinstance(parsed_messages, list) else []
                    except json.JSONDecodeError:
                        print("Could not parse messages as JSON")
                        messages = []
                else:
                    messages = example["messages"]
                
                # Process messages
                for message in messages:
                    if isinstance(message, dict) and "role" in message and message["role"] == "user":
                        user_texts.append(message["content"])
                
                # Return all user messages joined together or the first one
                if user_texts:
                    return " ".join(user_texts)
                else:
                    return ""
            elif "text" in example:
                # Legacy format
                return example["text"]
            elif "content" in example:
                # Another possible format
                return example["content"]
            else:
                # No recognized format
                return ""
        except Exception as e:
            print(f"Error extracting text: {str(e)}")
            return ""
    
    def evaluate_cola(self, batch_size=8, max_samples=100):
        """
        Evaluate the model on the CoLA (Corpus of Linguistic Acceptability) task.
        
        Args:
            batch_size: Batch size for evaluation
            max_samples: Maximum number of samples to evaluate
            
        Returns:
            Dictionary with task metrics
        """
        print(f"Evaluating on CoLA...")
        
        # Load dataset
        try:
            dataset = load_dataset("glue", "cola", split="validation")
            print(f"Loaded {len(dataset)} examples from CoLA")
        except Exception as e:
            print(f"Error loading CoLA dataset: {e}")
            return {"error": str(e)}
        
        # Take a subset if requested
        if max_samples and max_samples < len(dataset):
            dataset = dataset.select(range(max_samples))
            print(f"Using {max_samples} examples for evaluation")
        
        # Prepare prompt template and metrics
        prompt_template = "Is the following sentence grammatically correct? Answer 'acceptable' or 'unacceptable'.\nSentence: {}\n"
        label_map = {0: "unacceptable", 1: "acceptable"}
        
        # Prepare inputs
        inputs = []
        gold_labels = []
        
        for example in dataset:
            prompt = prompt_template.format(example["sentence"])
            inputs.append(prompt)
            gold_labels.append(example["label"])
        
        # Generate predictions
        predictions = []
        for i in tqdm(range(0, len(inputs), batch_size), desc="Evaluating CoLA"):
            batch_inputs = inputs[i:i + batch_size]
            batch_predictions = []
            
            for prompt in batch_inputs:
                response = self.generate_response(prompt, max_new_tokens=50)
                batch_predictions.append(response.strip().lower())
            
            predictions.extend(batch_predictions)
            
            # Clear memory
            torch.cuda.empty_cache()
        
        # Map text predictions to label ids
        label_map_reverse = {v.lower(): k for k, v in label_map.items()}
        pred_labels = []
        
        for pred in predictions:
            # Check for any match with label words
            label_found = False
            for label_text, label_id in label_map_reverse.items():
                if label_text in pred.lower():
                    pred_labels.append(label_id)
                    label_found = True
                    break
            
            # If no label word found, use default
            if not label_found:
                # Default to first label as fallback
                pred_labels.append(list(label_map_reverse.values())[0])
        
        # Calculate metrics
        # Accuracy
        correct = sum(p == g for p, g in zip(pred_labels, gold_labels))
        accuracy = correct / len(gold_labels) if gold_labels else 0
        
        # Matthews correlation coefficient
        tp = sum(1 for p, g in zip(pred_labels, gold_labels) if p == 1 and g == 1)
        tn = sum(1 for p, g in zip(pred_labels, gold_labels) if p == 0 and g == 0)
        fp = sum(1 for p, g in zip(pred_labels, gold_labels) if p == 1 and g == 0)
        fn = sum(1 for p, g in zip(pred_labels, gold_labels) if p == 0 and g == 1)
        
        numerator = (tp * tn) - (fp * fn)
        denominator = ((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn)) ** 0.5
        
        mcc = numerator / denominator if denominator > 0 else 0
        
        # Save some example predictions for debugging
        examples = []
        for i in range(min(5, len(inputs))):
            examples.append({
                "input": inputs[i],
                "prediction": predictions[i],
                "pred_label": pred_labels[i],
                "gold_label": gold_labels[i],
                "correct": pred_labels[i] == gold_labels[i]
            })
        
        results = {
            "accuracy": accuracy,
            "matthews_correlation": mcc,
            "examples": examples,
            "total_samples": len(inputs)
        }
        
        # Print results summary
        print("\n=== CoLA Results ===")
        print(f"Accuracy: {accuracy:.4f}")
        print(f"Matthews Correlation: {mcc:.4f}")
        
        return results
    
    def evaluate_hellaswag(self, max_samples=100, batch_size=4):
        """
        Evaluate the model on the HellaSwag benchmark.
        
        HellaSwag tests if a model can complete a sentence with the correct ending.
        
        Args:
            max_samples: Maximum number of samples to evaluate
            batch_size: Batch size for evaluation
            
        Returns:
            Dictionary with metrics
        """
        print("Evaluating on HellaSwag...")
        
        try:
            # Load HellaSwag dataset with trust_remote_code=True
            dataset = load_dataset("hellaswag", trust_remote_code=True)
            validation_dataset = dataset['validation']
            print(f"Loaded {len(validation_dataset)} examples from HellaSwag")
            
            # Debug the first example to see its structure
            if len(validation_dataset) > 0:
                first_example = validation_dataset[0]
                print(f"Example structure sample: {first_example.keys()}")
        except Exception as e:
            print(f"Error loading HellaSwag dataset: {e}")
            return {"error": str(e)}
        
        # Take a subset if requested
        if max_samples and max_samples < len(validation_dataset):
            indices = list(range(max_samples))
            validation_subset = validation_dataset.select(indices)
            print(f"Using {max_samples} examples for evaluation")
        else:
            validation_subset = validation_dataset
        
        correct_predictions = 0
        examples = []
        
        for i in tqdm(range(0, len(validation_subset), batch_size), desc="Evaluating HellaSwag"):
            batch_indices = list(range(i, min(i + batch_size, len(validation_subset))))
            batch = [validation_subset[j] for j in batch_indices]
            
            for example in batch:
                try:
                    # Format the prompt with context and activity label
                    context = example["ctx_a"] if "ctx_a" in example else example.get("ctx", "")
                    activity_label = example.get("activity_label", "")
                    
                    prompt = f"Activity: {activity_label}\nContext: {context}\nComplete the sentence with the most appropriate ending:\n"
                    
                    # Get the endings
                    endings = example["endings"]
                    correct_ending_idx = int(example["label"]) if "label" in example else 0
                    
                    # For scoring purposes, we'll ask the model to rank the endings
                    ending_scores = []
                    
                    for j, ending in enumerate(endings):
                        full_prompt = f"{prompt}{ending}"
                        
                        try:
                            # Calculate perplexity for this ending
                            inputs = self.tokenizer(full_prompt, return_tensors="pt").to(self.device)
                            
                            with torch.no_grad():
                                outputs = self.model(**inputs, labels=inputs["input_ids"])
                                loss = outputs.loss.item()
                                
                            # Lower perplexity (loss) is better
                            ending_scores.append((j, loss))
                        except Exception as e:
                            print(f"Error processing ending {j}: {str(e)}")
                            # Assign a high loss (bad score) to problematic endings
                            ending_scores.append((j, float('inf')))
                    
                    # Sort by perplexity (lower is better)
                    ending_scores.sort(key=lambda x: x[1])
                    predicted_ending_idx = ending_scores[0][0]  # Get the index with lowest perplexity
                    
                    # Check if prediction is correct
                    is_correct = predicted_ending_idx == correct_ending_idx
                    if is_correct:
                        correct_predictions += 1
                    
                    # Save this example for debugging if needed
                    if len(examples) < 5:
                        examples.append({
                            "context": context,
                            "activity": activity_label,
                            "endings": endings,
                            "predicted_idx": predicted_ending_idx,
                            "correct_idx": correct_ending_idx,
                            "is_correct": is_correct
                        })
                except Exception as e:
                    print(f"Error processing example: {str(e)}")
                    continue
                
                # Clear memory
                torch.cuda.empty_cache()
        
        # Calculate accuracy
        accuracy = correct_predictions / len(validation_subset) if validation_subset else 0
        
        results = {
            "accuracy": accuracy,
            "total_samples": len(validation_subset),
            "correct_predictions": correct_predictions,
            "examples": examples
        }
        
        # Print results summary
        print("\n=== HellaSwag Results ===")
        print(f"Accuracy: {accuracy:.4f}")
        print(f"Correct: {correct_predictions}/{len(validation_subset)}")
        
        return results
    
    def run_evaluation(self, validation_data_path=None):
        """Run evaluation including perplexity, CoLA and HellaSwag"""
        print("Starting evaluation...")
        
        # Results dictionary
        results = {}
        
        # 1. Calculate perplexity if validation data is provided
        if validation_data_path:
            print("\n1. Calculating perplexity...")
            
            # Check if validation data file exists
            if not os.path.exists(validation_data_path):
                print(f"Warning: Validation data file not found: {validation_data_path}")
                print("Skipping perplexity evaluation.")
            else:
                # Load validation data
                validation_examples = []
                with open(validation_data_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            example = json.loads(line.strip())
                            validation_examples.append(example)
                        except json.JSONDecodeError as e:
                            print(f"Error parsing JSON line: {e}")
                            continue
                
                print(f"Loaded {len(validation_examples)} validation examples")
                
                # Extract texts for perplexity calculation
                texts = []
                for example in validation_examples:
                    text = self.extract_text_for_evaluation(example)
                    if text:
                        texts.append(text)
                
                print(f"Extracted {len(texts)} valid text samples for evaluation")
                
                # Calculate perplexity on a subset to save time
                num_perplexity_samples = min(10, len(texts))
                perplexity = self.calculate_perplexity(texts[:num_perplexity_samples], batch_size=1)
                print(f"Perplexity: {perplexity:.4f}")
                results["perplexity"] = perplexity
                
                # Clear memory
                torch.cuda.empty_cache()
        
        # 2. Evaluate on CoLA
        print("\n2. Running CoLA evaluation...")
        cola_results = self.evaluate_cola(max_samples=50)
        results["cola"] = cola_results
        
        # Clear memory
        torch.cuda.empty_cache()
        
        # 3. Evaluate on HellaSwag
        print("\n3. Running HellaSwag evaluation...")
        hellaswag_results = self.evaluate_hellaswag(max_samples=50)
        results["hellaswag"] = hellaswag_results
        
        # Save results to file
        output_path = "evaluation_results.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"\nResults saved to {output_path}")
        
        # Print summary
        print("\n=== Evaluation Summary ===")
        if "perplexity" in results:
            print(f"Perplexity: {results['perplexity']:.4f}")
        
        # Print CoLA results
        if "cola" in results and "accuracy" in results["cola"]:
            print(f"CoLA accuracy: {results['cola']['accuracy']:.4f}")
            print(f"CoLA Matthews correlation: {results['cola']['matthews_correlation']:.4f}")
        
        # Print HellaSwag results
        if "hellaswag" in results and "accuracy" in results["hellaswag"]:
            print(f"HellaSwag accuracy: {results['hellaswag']['accuracy']:.4f}")
        
        return results

# Main execution
if __name__ == "__main__":
    # Get the absolute path to your model directory
    model_path = os.path.abspath("backend/models/gemma3/dhivehi-gemma-3-1b")
    print(f"Using model path: {model_path}")
    
    # Verify the path exists before proceeding
    if not os.path.exists(model_path):
        print(f"ERROR: Model path does not exist: {model_path}")
        print(f"Current working directory: {os.getcwd()}")
        print("Please check your model path and try again.")
        exit(1)
    
    # Path to validation data
    validation_data_path = "backend/data/processed/gemma3/validation.jsonl"
    validation_data_path_abs = os.path.abspath(validation_data_path)
    print(f"Using validation data: {validation_data_path_abs}")
    
    # Verify validation data exists
    if not os.path.exists(validation_data_path_abs):
        print(f"ERROR: Validation data not found: {validation_data_path_abs}")
        print("Please check your validation data path and try again.")
        exit(1)
    
    try:
        # Initialize evaluator
        print("Initializing evaluator...")
        evaluator = ModelEvaluator(model_path)
        
        # Run evaluation
        print("Running evaluation...")
        results = evaluator.run_evaluation(validation_data_path_abs)
        
    except Exception as e:
        print(f"Error during evaluation: {str(e)}")
        import traceback
        traceback.print_exc()