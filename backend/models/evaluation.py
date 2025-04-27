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
import nltk
from rouge_score import rouge_scorer

# Download NLTK resources if not already present
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

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
                    max_length=256  # Reduced from 512
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
    
    def generate_response(self, prompt, max_length=100):
        """Generate a response from the model."""
        # Add instruction if not present
        if "ދިވެހި ބަހުން ޖަވާބު ދޭށެވެ" not in prompt:
            prompt = f"ޖަވާބު ދިވެހިބަހުން ދޭށެވެ (Please respond in Dhivehi)\n{prompt}"
        
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_length=max_length,
                num_return_sequences=1,
                temperature=0.7,
                top_p=0.9,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id
            )
        
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        # Return only the generated part (removing the prompt)
        return response[len(prompt):].strip()
    
    def calculate_rouge_score(self, validation_data, num_samples=20):
        """Calculate ROUGE scores using reference and hypothesis texts."""
        # Initialize rouge scorer with all metrics
        scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)
        
        references = []
        hypotheses = []
        rouge_scores = {
            'rouge1': {'precision': [], 'recall': [], 'fmeasure': []},
            'rouge2': {'precision': [], 'recall': [], 'fmeasure': []},
            'rougeL': {'precision': [], 'recall': [], 'fmeasure': []}
        }
        
        print(f"Calculating ROUGE scores on {min(num_samples, len(validation_data))} samples")
        
        for i, example in enumerate(tqdm(validation_data[:num_samples], desc="Generating for ROUGE")):
            try:
                # Safety check for data type
                if not isinstance(example, dict):
                    print(f"Skipping example {i}: not a dictionary, type: {type(example)}")
                    continue
                
                # Extract text from the example
                text = self.extract_text_for_evaluation(example)
                if not text:
                    continue
                
                # Extract assistant responses as references
                reference_text = ""
                if "messages" in example:
                    messages = example["messages"]
                    if isinstance(messages, str):
                        try:
                            messages = json.loads(messages)
                        except:
                            continue
                    
                    for message in messages:
                        if isinstance(message, dict) and "role" in message and message["role"] == "assistant":
                            reference_text = message["content"]
                            break
                elif "summary" in example:
                    reference_text = example["summary"]
                
                if reference_text:
                    # Get the prompt from user message
                    prompt = text[:200]  # Using part of the user message as prompt
                    
                    # Generate model response
                    hypothesis_text = self.generate_response(prompt, max_length=150)
                    
                    # Add to lists for later reference
                    references.append(reference_text)
                    hypotheses.append(hypothesis_text)
                    
                    # Calculate ROUGE scores for this example
                    scores = scorer.score(reference_text, hypothesis_text)
                    
                    # Store scores
                    for metric, score in scores.items():
                        rouge_scores[metric]['precision'].append(score.precision)
                        rouge_scores[metric]['recall'].append(score.recall)
                        rouge_scores[metric]['fmeasure'].append(score.fmeasure)
                    
                    # Clear memory periodically
                    if i % 5 == 0:
                        torch.cuda.empty_cache()
            
            except Exception as e:
                print(f"Error processing example {i} for ROUGE: {str(e)}")
                continue
        
        # Calculate average ROUGE scores
        avg_rouge_scores = {}
        for metric in rouge_scores:
            avg_rouge_scores[metric] = {
                'precision': sum(rouge_scores[metric]['precision']) / len(rouge_scores[metric]['precision']) if rouge_scores[metric]['precision'] else 0,
                'recall': sum(rouge_scores[metric]['recall']) / len(rouge_scores[metric]['recall']) if rouge_scores[metric]['recall'] else 0,
                'fmeasure': sum(rouge_scores[metric]['fmeasure']) / len(rouge_scores[metric]['fmeasure']) if rouge_scores[metric]['fmeasure'] else 0
            }
        
        # Print results
        print("\nROUGE Score Results:")
        for metric, scores in avg_rouge_scores.items():
            print(f"{metric} - Precision: {scores['precision']:.4f}, Recall: {scores['recall']:.4f}, F1: {scores['fmeasure']:.4f}")
        
        # Return detailed results
        return {
            'avg_scores': avg_rouge_scores,
            'num_samples': len(references),
            'all_scores': rouge_scores,
            # Include sample texts for reference
            'sample_pairs': [{'reference': ref, 'hypothesis': hyp} for ref, hyp in zip(references[:5], hypotheses[:5])]
        }
    
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
    
    def run_perplexity_and_rouge_evaluation(self, validation_data_path):
        """Run only perplexity and ROUGE evaluation"""
        print("Loading validation data...")
        
        # Check if validation data file exists
        if not os.path.exists(validation_data_path):
            raise FileNotFoundError(f"Validation data file not found: {validation_data_path}")
        
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
        
        # Results dictionary
        results = {}
        
        # Calculate perplexity
        print("\n1. Calculating perplexity...")
        perplexity = self.calculate_perplexity(texts[:10], batch_size=1)
        print(f"Perplexity: {perplexity:.4f}")
        results["perplexity"] = perplexity
        
        # Clear memory
        torch.cuda.empty_cache()
        
        # Calculate ROUGE score
        print("\n2. Calculating ROUGE scores...")
        rouge_results = self.calculate_rouge_score(validation_examples, num_samples=10)
        results["rouge"] = rouge_results
        
        # Save results to file
        output_path = "perplexity_rouge_results.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"\nResults saved to {output_path}")
        
        # Print summary
        print("\n=== Evaluation Summary ===")
        print(f"Perplexity: {perplexity:.4f}")
        print("ROUGE scores:")
        for metric, scores in rouge_results['avg_scores'].items():
            print(f"  {metric} - F1: {scores['fmeasure']:.4f}")
        print(f"Number of samples evaluated for ROUGE: {rouge_results['num_samples']}")
        
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
        
        # Run perplexity and ROUGE evaluation
        print("Running perplexity and ROUGE evaluation...")
        results = evaluator.run_perplexity_and_rouge_evaluation(validation_data_path_abs)
        
    except Exception as e:
        print(f"Error during evaluation: {str(e)}")
        import traceback
        traceback.print_exc()