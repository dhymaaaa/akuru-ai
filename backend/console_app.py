import os
import sys
import signal
from dotenv import load_dotenv
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, GenerationConfig
import re
import warnings

# Suppress specific warnings
warnings.filterwarnings("ignore", message="`generation_config`.*")

# Setup signal handler for graceful exit with Ctrl+C
def signal_handler(sig, frame):
    print("\nExiting chat bot...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

class DhivehiChatBot:
    def __init__(self, model_path="backend/models/gemma3/fine-tuned-dhivehi-gemma-3-1b"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Load tokenizer with Dhivehi-specific settings
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_path,
            token=hf_token,
            padding_side="left"
        )
        self.tokenizer.pad_token = self.tokenizer.eos_token
        
        # Load model with optimizations
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path,
            token=hf_token,
            device_map="auto",
            torch_dtype=torch.bfloat16
        ).eval()
        
        # Get model's default generation config and update with our settings
        default_config = self.model.generation_config
        self.generation_config = GenerationConfig(
            max_new_tokens=80,
            temperature=0.7,
            top_p=0.9,
            top_k=40,
            repetition_penalty=1.2,
            do_sample=True,
            pad_token_id=self.tokenizer.eos_token_id,
            eos_token_id=self.tokenizer.eos_token_id,
            bos_token_id=getattr(self.tokenizer, 'bos_token_id', default_config.bos_token_id),
            cache_implementation=default_config.cache_implementation,
        )
        
        # System prompt to guide the model
        self.system_prompt = (
            "މިއީ ދިވެހިބަހުގެ ޗެޓްބޮޓެކެވެ. ތިބާޔާ ދިވެހިބަހުގެ ގޮތުގައި ވާހަކަ ދައްކަވާ ބޮޓެކެވެ. "
            "ޖަވާބު ދިވެހި ބަހުން ދޭށެވެ.\n\n"
        )

    def _clean_response(self, text):
        """Remove unwanted patterns and validate Dhivehi content."""
        # Remove URLs and special patterns
        text = re.sub(r'http\S+|www\.\S+', '', text)
        text = re.sub(r'\(.*?\)|\[.*?\]|\{.*?\}', '', text)
        text = re.sub(r'[^\u0780-\u07B1\s\.,!?ހ-ް]', '', text)  # Keep only Thaana chars
        
        # Validate Dhivehi content
        thaana_count = sum(1 for c in text if '\u0780' <= c <= '\u07B1')
        if thaana_count < 3:  # Require at least 3 Thaana characters
            return None
        
        return text.strip()

    def generate_response(self, user_input):
        """Generate and validate a Dhivehi response."""
        try:
            # Prepare the prompt with system message and user input
            prompt = f"{self.system_prompt}User: {user_input}\nBot:"
            
            inputs = self.tokenizer(
                prompt,
                return_tensors="pt",
                max_length=512,
                truncation=True,
                padding=True
            ).to(self.device)
            
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    generation_config=self.generation_config
                )
            
            # Decode and clean the response
            full_response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            response = full_response[len(prompt):].strip()
            cleaned_response = self._clean_response(response)
            
            return cleaned_response if cleaned_response else None
            
        except Exception as e:
            print(f"Generation error: {e}")
            return None

    def get_response(self, user_input):
        """Get a validated Dhivehi response with fallback."""
        # First try model generation
        response = self.generate_response(user_input)
        
        # Fallback responses if generation fails
        if response is None:
            if any(g in user_input.lower() for g in ["hello", "hi", "ހެލޯ", "އައްސަލާމް"]):
                return "ވައަލައިކުމް އައްސަލާމް! ކިހިނެއްތޯ އުޅުއްވަނީ؟"
            elif "ކިހިނެއް" in user_input or "how are you" in user_input.lower():
                return "އަޅުގަނޑު ރަނގަޅު، ޝުކުރިއްޔާ! ތިބާ ކިހިނެއް؟"
            return "މާފު ކުރައްވާ، އަޅުގަނޑަކަށް ނުވިސްނުނު."
        
        return response

def chat_bot():
    print("އައްސަލާމް އަލައިކުމް! އަކުރު އޭއައި އަށް މަރުުހަބާ!")
    print("Type 'exit' or 'quit' to end the conversation.")
    bot = DhivehiChatBot()
    
    # Add a while loop to keep the conversation going
    while True:
        user_input = input("\nYou: ")
        
        # Check if user wants to exit
        if user_input.lower() in ["exit", "quit"]:
            print("Bot: ބާއްޖަވެރި ދުވަހަކަށް އެދެން!")
            break
        
        response = bot.get_response(user_input)
        print("Bot:", response)
        

if __name__ == "__main__":
    load_dotenv()
    hf_token = os.getenv("HF_TOKEN")
    if not hf_token:
        raise ValueError("HF_TOKEN environment variable not set.")
    chat_bot()