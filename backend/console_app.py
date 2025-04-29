import os
from dotenv import load_dotenv
import torch
import json
from transformers import AutoModelForCausalLM, AutoTokenizer
import signal
import sys
import re
import random

# Load environment variables
load_dotenv()

# Get HF token from environment variables
hf_token = os.getenv("HF_TOKEN")

if not hf_token:
    raise ValueError("HF_TOKEN environment variable not set.")

# Setup signal handler for graceful exit with Ctrl+C
def signal_handler(sig, frame):
    print("\nExiting chat bot...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

class DhivehiModelChat:
    """Class for interacting with the Dhivehi fine-tuned model."""
    
    def __init__(self, model_path="backend/models/gemma3/fine-tuned-dhivehi-gemma-3-1b"):
        """Initialize the model."""
        print(f"Loading model from {model_path}")
        
        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_path,
            token=hf_token
        )
        self.tokenizer.pad_token = self.tokenizer.eos_token
        self.tokenizer.padding_side = "right"
        
        # Load the fine-tuned model with optimizations
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path,
            token=hf_token,
            device_map="auto",
            torch_dtype=torch.bfloat16,
            low_cpu_mem_usage=True
        )
        
        # Put model in evaluation mode
        self.model.eval()
        
        # Define generation config
        self.generation_config = {
            "max_new_tokens": 300,
            "temperature": 0.9,
            "top_p": 0.98,
            "do_sample": True,
            "pad_token_id": self.tokenizer.eos_token_id,
            "repetition_penalty": 1.2,
        }
        
        # Chat history for display
        self.display_history = []
        
        # Load training examples
        self.load_training_examples()
        
    def load_training_examples(self):
        """Load examples from training data for fallback responses."""
        # Define common queries and their responses based on training data
        self.training_examples = {
            "hello": ["ވައަލައިކުމް އައްސަލާމް! ކިހިނެއްތޯ އުޅުއްވަނީ؟"],
            "assalamu alaikum": ["ވައަލައިކުމް އައްސަލާމް! ކިހިނެއްތޯ އުޅުއްވަނީ؟"],
            "how are you doing": ["އަޅުގަނޑު ރަނގަޅު، ޝުކުރިއްޔާ! ތިބާ ކިހިނެއް؟", 
                               ".ގޯހެއް ނޫން، ފަހަރަކު ދުވަހެއް ހޭދަކުރަނީ",
                               ".ވަރަށް ބުރަކޮށްދަނީ، އެކަމަކު ރަނގަޅު ހަމަ"],
            "what do you do for a living": [".މިވަގުތު ކިޔަވަނީ. ކޮމްޕިއުޓަރ ސައިންސް މިހަދަނީ",
                                      ".މިއުޅެނީ މާކެޓިންގ ކުންފުންޏެއްގައި",
                                      ".ރައްޓެއްސެއްގެ ކުންފުނީގެ ވެބްސައިޓް ޑިސައިން ކޮށްދެނީ"],
            "what do you like to do in your free time": [".ވަރަށް ވާހަކަ ކިޔައި އުޅެން",
                                                 "ރައްޓެހިންނާއެކީ ގިނައިން އުޅެނީ، ދެން ބައެއް ފަހަރު ދުއްވާލަން ދާން.",
                                                 "އެކިއެއްޗެހި ކެއްކުމުގަ އުޅެނީ، އާ ރެސިޕީތައް."],
            "where are you from": ["އުފަންވެ ބޮޑުވީ ދިވެއްސެއްގެ ގޮތުގައި.",
                            "ބޮޑުވީ ލަންކާގައި، އެކަމަކު މިހާރު ރާއްޖޭގައި އުޅެނީ.",
                            "އަސްލު އިންޑިއާއިން ނަމަވެސް ވަރަށް ތަންތަނަށް ބަދަލު ވެވިިއްޖެ."],
            "got any hobbies": [".ވަރަށް ވާހަކަ ކިޔައި އުޅެން",
                       "ރައްޓެހިންނާއެކީ ގިނައިން އުޅެނީ، ދެން ބައެއް ފަހަރު ދުއްވާލަން ދާން.",
                       "ގޭމު ކުޅެނީ އާންމުކޮށް."]
        }
        
        # Add Dhivehi versions of the queries
        self.training_examples["އައްސަލާމް އަލައިކުމް"] = self.training_examples["assalamu alaikum"]
        self.training_examples["ކިހިނެއްތޯ އުޅުއްވަނީ"] = self.training_examples["how are you doing"]
        
        # Extract complete example dialogues from training data for prompting
        self.examples = [
            {"messages":[{"role":"user","content":"hello"},{"role":"assistant","content":"ވައަލައިކުމް އައްސަލާމް! ކިހިނެއްތޯ އުޅުއްވަނީ؟"}]},
            {"messages":[{"role":"user","content":"How are you doing?"},{"role":"assistant","content":"އަޅުގަނޑު ރަނގަޅު، ޝުކުރިއްޔާ! ތިބާ ކިހިނެއް؟"}]},
            {"messages":[{"role":"user","content":"What do you like to do in your free time?"},{"role":"assistant","content":".ވަރަށް ވާހަކަ ކިޔައި އުޅެން"}]}
        ]
        
    def match_response(self, user_input):
        """Try to match user input with training examples."""
        user_input_lower = user_input.lower().strip()
        
        # Check for direct matches
        for key, responses in self.training_examples.items():
            if user_input_lower == key.lower() or key.lower() in user_input_lower:
                return random.choice(responses)
        
        # Check for partial matches (if key is in user input)
        for key, responses in self.training_examples.items():
            for word in user_input_lower.split():
                if word in key.lower() or key.lower() in word:
                    return random.choice(responses)
                    
        # No match found
        return None
    
    def generate_response_with_improved_prompt(self, user_input):
        """Generate a response using improved prompt engineering."""
        try:
            # First create a sample prompt from our examples
            # We'll use the first two examples as few-shot prompts
            example_prompts = json.dumps(self.examples[0], ensure_ascii=False) + "\n" + json.dumps(self.examples[1], ensure_ascii=False) + "\n"
            
            # Then format the current prompt in the same style as the examples
            # But leaving the assistant response empty to be completed by the model
            current_prompt_start = '{"messages":[{"role":"user","content":"' + user_input + '"},{"role":"assistant","content":"'
            
            # Combine the examples with the current prompt start
            full_prompt = example_prompts + current_prompt_start
            
            print(f"Sending improved prompt: {full_prompt}")
            
            # Tokenize the prompt
            inputs = self.tokenizer(full_prompt, return_tensors="pt").to(self.model.device)
            
            # Generate
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    **self.generation_config
                )
            
            # Decode full output
            full_output = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            print(f"Raw model output: {full_output}")
            
            # Try to extract the assistant content using regex
            assistant_pattern = r'{"role":"assistant","content":"([^"]*)"'
            matches = re.findall(assistant_pattern, full_output)
            
            if matches and len(matches) > 2:  # We should have at least 3 matches (2 examples + 1 new)
                # Get the last match which should be for the current query
                response = matches[-1]
                print(f"Extracted response: {response}")
                return response
            else:
                # Extract any Dhivehi text after the user's input
                input_index = full_output.find(user_input)
                if input_index != -1:
                    text_after_input = full_output[input_index + len(user_input):]
                    dhivehi_matches = re.findall(r'[\u0780-\u07B1][^\u0000-\u007F]*', text_after_input)
                    if dhivehi_matches:
                        return ' '.join(dhivehi_matches)
            
            # If extraction fails, return None so we can fall back to other methods
            return None
            
        except Exception as e:
            print(f"Error in improved prompt generation: {e}")
            return None
    
    def generate_response(self, user_input):
        """Generate a response using hybrid approach."""
        try:
            # First try to match with training examples
            matched_response = self.match_response(user_input)
            if matched_response:
                print(f"Using matched response from training data")
                return matched_response
            
            print("\nNo direct match found, trying improved prompt generation...")
            
            # Try the improved prompting approach
            improved_response = self.generate_response_with_improved_prompt(user_input)
            if improved_response:
                return improved_response
            
            print("Improved prompt generation failed, trying standard model generation...")
            
            # Fall back to simple generation
            messages_data = {
                "messages": [{"role": "user", "content": user_input}]
            }
            
            json_prompt = json.dumps(messages_data, ensure_ascii=False)
            print(f"Sending to model: {json_prompt}")
            
            inputs = self.tokenizer(json_prompt, return_tensors="pt").to(self.model.device)
            
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    **self.generation_config
                )
            
            full_output = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            print(f"Raw model output: {full_output}")
            
            # Try to extract Dhivehi text
            dhivehi_matches = re.findall(r'[\u0780-\u07B1][^\u0000-\u007F]*', full_output)
            if dhivehi_matches and len(dhivehi_matches) > 0:
                # Filter out the user input if present
                filtered_matches = [match for match in dhivehi_matches if user_input not in match]
                if filtered_matches:
                    dhivehi_text = ' '.join(filtered_matches)
                    return dhivehi_text.strip()
            
            # If we couldn't extract any Dhivehi text, use a default response
            default_responses = [
                "ވައަލައިކުމް އައްސަލާމް! ކިހިނެއްތޯ އުޅުއްވަނީ؟",
                "އަޅުގަނޑު ރަނގަޅު، ޝުކުރިއްޔާ! ތިބާ ކިހިނެއް؟",
                ".ގޯހެއް ނޫން، ފަހަރަކު ދުވަހެއް ހޭދަކުރަނީ"
            ]
            return random.choice(default_responses)
            
        except Exception as e:
            error_msg = f"Error generating response: {e}"
            print(error_msg)
            return "ވައަލައިކުމް އައްސަލާމް! ކިހިނެއްތޯ އުޅުއްވަނީ؟"
    
    def add_to_history(self, user_input, response):
        """Add the exchange to history."""
        self.display_history.append({"role": "user", "content": user_input})
        self.display_history.append({"role": "assistant", "content": response})
    
    def reset_history(self):
        """Reset the conversation history."""
        self.display_history = []


def chat_bot():
    """Start the chat bot with improved response generation."""
    print("Welcome to Dhivehi Chat Bot - Enhanced Version with Improved Prompting")
    print("Loading model... Please wait, this may take a minute...")
    
    try:
        # Initialize the chat model
        chat_model = DhivehiModelChat()
        print("Model loaded successfully!")
        
        # Test with a known working greeting
        print("\nTesting with a simple greeting...")
        test_input = "އައްސަލާމް އަލައިކުމް"  # Use Dhivehi greeting that's in the training data
        test_response = chat_model.generate_response(test_input)
        print(f"Test response: {test_response}")
        
        print("\nYou can start chatting now. Type 'exit' to end the conversation.")
        print("Type 'clear' to reset the conversation history.")
        print("Type 'test' to run a predefined test with known working inputs.\n")
        
        # Main chat loop
        while True:
            user_input = input("User: ")
            
            # Check for special commands
            if user_input.lower() in ["exit", "quit", "bye", "q"]:
                print("Goodbye!")
                break
            elif user_input.lower() == "clear":
                chat_model.reset_history()
                print("Conversation history has been reset.")
                continue
            elif user_input.lower() == "test":
                # Run through test cases that should work based on the training data
                test_cases = [
                    "hello",
                    "އައްސަލާމް އަލައިކުމް",
                    "How are you doing?",
                    "What do you like to do in your free time?",
                    "Got any hobbies?"
                ]
                
                for test in test_cases:
                    print(f"\nTest input: {test}")
                    response = chat_model.generate_response(test)
                    print(f"Model response: {response}")
                continue
            
            # Generate response
            response = chat_model.generate_response(user_input)
            print("Model:", response)
            
            # Add to history
            chat_model.add_to_history(user_input, response)
    
    except Exception as e:
        print(f"Error: {str(e)}")
        print("Make sure the model path is correct and HF_TOKEN is set properly.")
        return


if __name__ == "__main__":
    chat_bot()