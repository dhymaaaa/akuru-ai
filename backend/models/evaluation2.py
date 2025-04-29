import os
from dotenv import load_dotenv
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from datasets import Dataset
from tqdm import tqdm
import numpy as np
import json
from peft import PeftModel, PeftConfig
import gc

# Load environment variables
load_dotenv()
hf_token = os.getenv("HF_TOKEN")

class DhivehiModelEvaluator:
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
        return response[len(self.tokenizer.decode(inputs["input_ids"][0], skip_special_tokens=True)):].strip()
    
    def evaluate_dhivehi_translation(self, test_data_path, max_samples=None):
        """
        Evaluate the model on Dhivehi translation tasks using a custom test set.
        
        Args:
            test_data_path: Path to the test data file
            max_samples: Maximum number of samples to evaluate
            
        Returns:
            Dictionary with metrics
        """
        print(f"Evaluating Dhivehi translation on {test_data_path}...")
        
        # Load test data
        if not os.path.exists(test_data_path):
            print(f"Test data file not found: {test_data_path}")
            return {"error": "Test data file not found"}
        
        # Load test data
        test_examples = []
        with open(test_data_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    example = json.loads(line.strip())
                    test_examples.append(example)
                except json.JSONDecodeError as e:
                    print(f"Error parsing JSON line: {e}")
                    continue
                    
        print(f"Loaded {len(test_examples)} test examples")
        
        # Take a subset if requested
        if max_samples and max_samples < len(test_examples):
            # Random sampling
            import random
            random.seed(42)
            test_examples = random.sample(test_examples, max_samples)
            print(f"Using {max_samples} examples for evaluation")
        
        results = []
        metrics = {"bleu_scores": [], "character_error_rates": []}
        
        for i, example in enumerate(tqdm(test_examples, desc="Evaluating translations")):
            try:
                # Extract input and expected output
                if "input" in example and "output" in example:
                    input_text = example["input"]
                    expected_output = example["output"]
                elif "messages" in example:
                    # Handle chat format
                    messages = example["messages"]
                    input_text = ""
                    expected_output = ""
                    for msg in messages:
                        if msg["role"] == "user":
                            input_text += msg["content"] + "\n"
                        elif msg["role"] == "assistant":
                            expected_output += msg["content"] + "\n"
                else:
                    print(f"Unknown example format: {example.keys()}")
                    continue
                
                # Modified prompt format to match training format
                prompt = f"<start>\nuser: {input_text}\nassistant: (Please respond in Dhivehi)"
                
                # Generate response
                generated_output = self.generate_response(prompt, max_new_tokens=150)
                
                # Calculate BLEU score (simple version)
                bleu_score = self.calculate_bleu(expected_output, generated_output)
                metrics["bleu_scores"].append(bleu_score)
                
                # Calculate character error rate
                cer = self.calculate_character_error_rate(expected_output, generated_output)
                metrics["character_error_rates"].append(cer)
                
                # Save results
                results.append({
                    "input": input_text,
                    "expected": expected_output,
                    "generated": generated_output,
                    "bleu": bleu_score,
                    "cer": cer
                })
                
                # Print progress every 10 examples
                if (i + 1) % 10 == 0:
                    avg_bleu = sum(metrics["bleu_scores"]) / len(metrics["bleu_scores"])
                    avg_cer = sum(metrics["character_error_rates"]) / len(metrics["character_error_rates"])
                    print(f"Progress: {i+1}/{len(test_examples)}, Avg BLEU: {avg_bleu:.4f}, Avg CER: {avg_cer:.4f}")
                
            except Exception as e:
                print(f"Error processing example {i}: {str(e)}")
                continue
                
            # Clear memory
            torch.cuda.empty_cache()
            
        # Calculate final metrics
        avg_bleu = sum(metrics["bleu_scores"]) / len(metrics["bleu_scores"]) if metrics["bleu_scores"] else 0
        avg_cer = sum(metrics["character_error_rates"]) / len(metrics["character_error_rates"]) if metrics["character_error_rates"] else 0
        
        # Print final results
        print("\n=== Dhivehi Translation Results ===")
        print(f"Average BLEU score: {avg_bleu:.4f}")
        print(f"Average Character Error Rate: {avg_cer:.4f}")
        print(f"Total evaluated examples: {len(results)}")
        
        # Return metrics and some example results for analysis
        return {
            "avg_bleu": avg_bleu,
            "avg_cer": avg_cer,
            "total_samples": len(results),
            "examples": results[:10]  # Include first 10 examples
        }
    
    def calculate_bleu(self, reference, candidate):
        """Calculate a simplified BLEU score."""
        try:
            from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
            
            # Tokenize by character for Dhivehi
            ref_tokens = list(reference)
            cand_tokens = list(candidate)
            
            # Calculate BLEU score with smoothing
            smoothie = SmoothingFunction().method1
            return sentence_bleu([ref_tokens], cand_tokens, smoothing_function=smoothie)
        except ImportError:
            print("NLTK not installed. Using basic token overlap.")
            ref_tokens = list(reference)
            cand_tokens = list(candidate)
            
            # Calculate token overlap as an approximation
            matches = sum(1 for t in cand_tokens if t in ref_tokens)
            if len(cand_tokens) == 0:
                return 0
            return matches / len(cand_tokens)

    def calculate_character_error_rate(self, reference, hypothesis):
        """Calculate the character error rate between reference and hypothesis."""
        # Implement Levenshtein distance
        def levenshtein(s1, s2):
            if len(s1) < len(s2):
                return levenshtein(s2, s1)
            
            if len(s2) == 0:
                return len(s1)
            
            previous_row = range(len(s2) + 1)
            for i, c1 in enumerate(s1):
                current_row = [i + 1]
                for j, c2 in enumerate(s2):
                    insertions = previous_row[j + 1] + 1
                    deletions = current_row[j] + 1
                    substitutions = previous_row[j] + (c1 != c2)
                    current_row.append(min(insertions, deletions, substitutions))
                previous_row = current_row
                
            return previous_row[-1]
        
        # Calculate CER
        edit_distance = levenshtein(reference, hypothesis)
        
        if len(reference) == 0:
            return 1.0
            
        return edit_distance / len(reference)
    
    def evaluate_model_coherence(self, prompts, max_new_tokens=200):
        """
        Evaluate the model's coherence and fluency in Dhivehi.
        
        Args:
            prompts: List of prompts to test
            max_new_tokens: Maximum number of tokens to generate
            
        Returns:
            Dictionary with coherence metrics and example outputs
        """
        print("Evaluating model coherence in Dhivehi...")
        
        results = []
        
        for i, prompt in enumerate(tqdm(prompts, desc="Generating responses")):
            try:
                # Modified prompt format to match training format
                full_prompt = f"<start>\nuser: {prompt}\nassistant: (Please respond in Dhivehi)"
                
                # Generate response
                generated_output = self.generate_response(full_prompt, max_new_tokens=max_new_tokens)
                
                # Create result entry
                result = {
                    "prompt": prompt,
                    "response": generated_output,
                    # We can't automatically evaluate coherence, but we can check for some heuristics
                    "contains_dhivehi": any('\u0780' <= c <= '\u07B1' for c in generated_output),
                    "response_length": len(generated_output)
                }
                
                results.append(result)
                
                # Print every 5th response for manual checking
                if i % 5 == 0:
                    print(f"\nPrompt {i+1}: {prompt}")
                    print(f"Response: {generated_output[:100]}...")
                
            except Exception as e:
                print(f"Error processing prompt {i}: {str(e)}")
                continue
                
            # Clear memory
            torch.cuda.empty_cache()
        
        # Calculate basic metrics
        dhivehi_ratio = sum(1 for r in results if r["contains_dhivehi"]) / len(results) if results else 0
        avg_length = sum(r["response_length"] for r in results) / len(results) if results else 0
        
        print("\n=== Coherence Evaluation Results ===")
        print(f"Responses with Dhivehi: {dhivehi_ratio:.2%}")
        print(f"Average response length: {avg_length:.1f} characters")
        
        return {
            "dhivehi_ratio": dhivehi_ratio,
            "avg_response_length": avg_length,
            "examples": results
        }
    
    def run_dhivehi_evaluation(self, test_data_path):
        """Run comprehensive evaluation for Dhivehi model"""
        print("Starting evaluation for Dhivehi fine-tuned model...")
        
        # Results dictionary
        all_results = {}
        
        # 1. Translation quality evaluation using test data
        print("\n1. Evaluating translation quality...")
        translation_results = self.evaluate_dhivehi_translation(test_data_path, max_samples=100)
        all_results["translation"] = translation_results
        
        # Clear memory
        torch.cuda.empty_cache()
        
        # 2. Model coherence evaluation with standard prompts
        print("\n2. Evaluating model coherence in Dhivehi...")
        test_prompts = [
            "Tell me about the Maldives",
            "What is your favorite food?",
            "Write a short story about the ocean",
            "Explain how to cook rice",
            "What is the history of the Dhivehi language?",
            "Describe the weather in a tropical country",
            "What are some traditional Maldivian dishes?",
            "Tell me about marine conservation",
            "How to make traditional Maldivian sweets?",
            "Write a poem about the sea",
            # Added Islamic greeting examples
            "Assalamu Alaikum",
            "Hello, how are you?"
        ]
        coherence_results = self.evaluate_model_coherence(test_prompts)
        all_results["coherence"] = coherence_results
        
        # 3. Calculate perplexity if test data is available
        if os.path.exists(test_data_path):
            print("\n3. Calculating perplexity...")
            # Extract text from test data
            texts = []
            with open(test_data_path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        example = json.loads(line.strip())
                        if "output" in example:
                            texts.append(example["output"])
                    except json.JSONDecodeError:
                        continue
            
            if texts:
                # Use a smaller subset for perplexity calculation to save time
                sample_size = min(30, len(texts))
                sample_texts = texts[:sample_size]
                perplexity = self.calculate_perplexity(sample_texts, batch_size=1)
                print(f"Perplexity on Dhivehi text: {perplexity:.4f}")
                all_results["perplexity"] = perplexity
        
        # Save results to file
        output_path = "dhivehi_evaluation_results.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        
        print(f"\nResults saved to {output_path}")
        
        # Print summary
        print("\n=== Dhivehi Model Evaluation Summary ===")
        
        # Print translation results
        if "translation" in all_results and "avg_bleu" in all_results["translation"]:
            print(f"Translation BLEU: {all_results['translation']['avg_bleu']:.4f}")
            print(f"Translation Character Error Rate: {all_results['translation']['avg_cer']:.4f}")
        
        # Print coherence results
        if "coherence" in all_results:
            print(f"Dhivehi content ratio: {all_results['coherence']['dhivehi_ratio']:.2%}")
            print(f"Average response length: {all_results['coherence']['avg_response_length']:.1f} chars")
        
        # Print perplexity
        if "perplexity" in all_results:
            print(f"Perplexity on Dhivehi text: {all_results['perplexity']:.4f}")
        
        return all_results


# Main execution
if __name__ == "__main__":
    # Get the absolute path to your fine-tuned model directory
    model_path = os.path.abspath("backend/models/gemma3/fine-tuned-dhivehi-gemma-3-1b")
    print(f"Using fine-tuned model path: {model_path}")
    
    # Verify the path exists before proceeding
    if not os.path.exists(model_path):
        print(f"ERROR: Model path does not exist: {model_path}")
        print(f"Current working directory: {os.getcwd()}")
        print("Please check your model path and try again.")
        exit(1)
    
    # Path to test data - using the validation data from the original training
    test_data_path = "backend/data/dhivehi-english-dialogue.jsonl"
    test_data_path_abs = os.path.abspath(test_data_path)
    print(f"Using test data: {test_data_path_abs}")
    
    # Verify test data exists
    if not os.path.exists(test_data_path_abs):
        print(f"ERROR: Test data not found: {test_data_path_abs}")
        print("Please check your test data path and try again.")
        exit(1)
    
    try:
        # Initialize evaluator
        print("Initializing Dhivehi model evaluator...")
        evaluator = DhivehiModelEvaluator(model_path)
        
        # Run evaluation
        print("Running Dhivehi-specific evaluation...")
        results = evaluator.run_dhivehi_evaluation(test_data_path_abs)
        
    except Exception as e:
        print(f"Error during evaluation: {str(e)}")
        import traceback
        traceback.print_exc()