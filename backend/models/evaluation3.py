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
            
            # Load the PEFT adapter
            self.model = PeftModel.from_pretrained(self.model, model_path)
            self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        else:
            print("Loading standard model...")
            self.tokenizer = AutoTokenizer.from_pretrained(model_path)
            self.model = AutoModelForCausalLM.from_pretrained(
                model_path,
                torch_dtype=torch.bfloat16,
                device_map="auto",
                quantization_config=quantization_config,
                attn_implementation="sdpa"
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
    
    def evaluate_news_summaries(self, test_data, num_samples=10):
        """Evaluate the model's ability to generate news summaries."""
        results = []
        
        for i, example in enumerate(tqdm(test_data[:num_samples], desc="Generating summaries")):
            if "content" in example and "title" in example:
                # Create a prompt for summary generation
                prompt = f"މި ޚަބަރުގެ ސަމަރީއެއް ލިޔެދޭށެވެ:\n{example['content'][:500]}"
                
                # Generate summary
                generated_summary = self.generate_response(prompt, max_length=150)
                
                results.append({
                    "original_title": example.get("title", ""),
                    "original_content": example.get("content", "")[:300] + "...",
                    "generated_summary": generated_summary
                })
                
                # Clear memory periodically
                if i % 5 == 0:
                    torch.cuda.empty_cache()
        
        return results
    
    def evaluate_language_understanding(self, test_data):
        """Evaluate language understanding through Q&A."""
        qa_results = []
        
        # Define some common news-related questions in Dhivehi
        questions = [
            "މި ޚަބަރަކީ ކޮބައިތޯ؟",  # What is this news about?
            "މި ޚަބަރުގައި ބައިވެރިވާ ފަރާތްތަކަކީ ކޮބައިތޯ؟",  # Who are the parties involved?
        ]
        
        for i, example in enumerate(tqdm(test_data[:10], desc="Q&A evaluation")):
            if "content" in example:
                for question in questions:
                    prompt = f"ޚަބަރު: {example['content'][:300]}\n\nސުވާލު: {question}"
                    answer = self.generate_response(prompt, max_length=100)
                    
                    qa_results.append({
                        "content": example['content'][:150] + "...",
                        "question": question,
                        "answer": answer
                    })
                    
                    # Clear memory
                    torch.cuda.empty_cache()
        
        return qa_results
    
    def evaluate_dhivehi_generation_ratio(self, test_texts, num_samples=20):
        """Evaluate the ratio of Dhivehi vs English in generated text."""
        dhivehi_char_count = 0
        total_char_count = 0
        
        for text in tqdm(test_texts[:num_samples], desc="Checking language ratio"):
            try:
                response = self.generate_response(text[:150], max_length=100)
                
                for char in response:
                    if '\u0780' <= char <= '\u07BF':  # Thaana Unicode range
                        dhivehi_char_count += 1
                    total_char_count += 1
                
                # Clear memory
                torch.cuda.empty_cache()
                
            except Exception as e:
                print(f"Error generating response: {e}")
                continue
        
        dhivehi_ratio = dhivehi_char_count / total_char_count if total_char_count > 0 else 0
        return dhivehi_ratio
    
    def full_evaluation(self, validation_data_path):
        """Perform a comprehensive evaluation of the model."""
        # Load validation data
        validation_data = load_dataset(
            "json",
            data_files=validation_data_path
        )["train"]
        
        print(f"Loaded {len(validation_data)} validation examples")
        
        # Extract texts
        texts = [example["text"] for example in validation_data]
        
        results = {}
        
        # Calculate perplexity on a small subset to avoid memory issues
        print("\n1. Calculating perplexity...")
        perplexity = self.calculate_perplexity(texts[:10], batch_size=1)
        print(f"Perplexity: {perplexity:.2f}")
        results["perplexity"] = perplexity
        
        # Clear memory
        torch.cuda.empty_cache()
        
        # Evaluate news summaries
        print("\n2. Evaluating news summaries...")
        summary_results = self.evaluate_news_summaries(validation_data, num_samples=5)
        results["summary_samples"] = summary_results
        
        # Clear memory
        torch.cuda.empty_cache()
        
        # Evaluate language understanding
        print("\n3. Evaluating language understanding...")
        qa_results = self.evaluate_language_understanding(validation_data)
        results["qa_samples"] = qa_results
        
        # Clear memory
        torch.cuda.empty_cache()
        
        # Evaluate Dhivehi generation ratio
        print("\n4. Evaluating Dhivehi generation ratio...")
        dhivehi_ratio = self.evaluate_dhivehi_generation_ratio(texts, num_samples=10)
        print(f"Dhivehi generation ratio: {dhivehi_ratio:.2%}")
        results["dhivehi_ratio"] = dhivehi_ratio
        
        # Save results
        output_path = "evaluation_results.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"\nResults saved to {output_path}")
        
        # Print sample results
        print("\n=== Sample Results ===")
        print("\nSample Summary Generation:")
        for i, result in enumerate(summary_results[:2]):
            print(f"\nExample {i+1}:")
            print(f"Original Title: {result['original_title']}")
            print(f"Generated Summary: {result['generated_summary']}")
        
        print("\nSample Q&A Results:")
        for i, result in enumerate(qa_results[:4]):
            print(f"\nExample {i+1}:")
            print(f"Question: {result['question']}")
            print(f"Answer: {result['answer']}")
        
        return results

# Main execution
if __name__ == "__main__":
    # Path to your fine-tuned model
    model_path = "backend/models/dhivehi-gemma-3-1b"
    
    # Path to validation data
    validation_data_path = "backend/data/processed/gemma/validation.jsonl"
    
    # Initialize evaluator
    evaluator = ModelEvaluator(model_path)
    
    # Run full evaluation
    results = evaluator.full_evaluation(validation_data_path)
    
    # Optional: Test with custom prompts
    print("\n=== Custom Prompt Test ===")
    custom_prompts = [
        "ރާއްޖޭގެ އިޤްތިޞާދަށް",
        "ސިޔާސީ ބަދަލުތަކުގެ ސަބަބުން",
    ]
    
    for prompt in custom_prompts:
        try:
            response = evaluator.generate_response(prompt)
            print(f"\nPrompt: {prompt}")
            print(f"Response: {response}")
        except Exception as e:
            print(f"Error with prompt '{prompt}': {e}")