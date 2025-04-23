import os
import json
import re
import random
from datetime import datetime
import logging
from tqdm import tqdm
import pandas as pd
from sklearn.model_selection import train_test_split

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("backend/data/processed/processing.log"),
        logging.StreamHandler()
    ]
)

# Create necessary directories
os.makedirs('backend/data/processed', exist_ok=True)
os.makedirs('backend/data/processed/gemma', exist_ok=True)
os.makedirs('backend/data/processed/articles', exist_ok=True)

def keep_dhivehi_only(text):
    """Keep only Dhivehi characters, numerals, and essential punctuation"""
    if not text:
        return ""
    
    # Define what to keep:
    # 1. Thaana script Unicode range (main Dhivehi script): U+0780 to U+07BF
    # 2. Common numerals (0-9)
    # 3. Essential punctuation
    # 4. Whitespace
    
    allowed_chars = []
    for char in text:
        # Keep Thaana script characters
        if '\u0780' <= char <= '\u07BF':
            allowed_chars.append(char)
        # Keep digits
        elif char.isdigit():
            allowed_chars.append(char)
        # Keep essential punctuation
        elif char in " .,;:!?-()[]{}\"'،":
            allowed_chars.append(char)
        # Keep whitespace
        elif char.isspace():
            allowed_chars.append(char)
    
    return ''.join(allowed_chars)

def clean_text(text):
    """Clean and normalize article text, keeping only Dhivehi characters"""
    if not text:
        return ""
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Remove HTML artifacts
    text = re.sub(r'<[^>]+>', '', text)
    
    # Fix common issues
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    
    # Remove common footer elements
    text = re.sub(r'Copyright © \d+ Mihaaru.*', '', text)
    text = re.sub(r"SMS 'sub mihaaru' to \d+", '', text)
    text = re.sub(r'Deliver popular news headlines to your inbox!.*', '', text)
    
    # Remove job listings often found at end of articles
    text = re.sub(r'(Associate|Manager|Officer|Assistant|Treasury|FI-Manager|Compliance)( \([^)]+\))?,', '', text)
    
    # Remove URLs
    text = re.sub(r'https?://\S+', '', text)
    
    # Remove English phrases often found in footer
    text = re.sub(r'Terms and Conditions|Privacy Policy|Copyright', '', text)
    
    # Clean up whitespace again after removals
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Filter to keep only Dhivehi characters, numerals, and essential punctuation
    text = keep_dhivehi_only(text)
    
    # Final whitespace cleanup
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def is_dhivehi_text(text):
    """Check if text is primarily in Dhivehi language
    
    This function uses character set analysis to determine if
    text is primarily in Dhivehi (Thaana script).
    """
    if not text:
        return False
    
    # Thaana script Unicode range (main Dhivehi script): U+0780 to U+07BF
    dhivehi_chars = 0
    non_dhivehi_chars = 0
    
    for char in text:
        # Ignore spaces, numbers, and punctuation
        if char.isspace() or char.isdigit() or char in ".,;:!?-()[]{}\"'،":
            continue
            
        # Count Thaana script characters
        if '\u0780' <= char <= '\u07BF':
            dhivehi_chars += 1
        else:
            non_dhivehi_chars += 1
    
    # Calculate percentage of Dhivehi characters (if there are any characters to count)
    total_chars = dhivehi_chars + non_dhivehi_chars
    if total_chars == 0:
        return False
        
    dhivehi_percentage = (dhivehi_chars / total_chars) * 100
    
    # Text is considered Dhivehi if at least 95% of characters are in Thaana script
    # Increased from 70% to 95% to be more strict about Dhivehi content
    return dhivehi_percentage >= 95

def is_valid_content(text):
    """Check if content appears to be a valid article rather than random words or names"""
    if not text:
        return False
        
    # Minimum length requirement
    if len(text) < 200:
        return False
    
    # Check for sentence structure (at least some punctuation)
    if not re.search(r'[.،:؛!?]', text):
        return False
        
    # Count words
    words = text.split()
    if len(words) < 30:  # Article should have at least 30 words
        return False
        
    # Check for repetition of short words (like lists of names)
    word_lengths = [len(word) for word in words]
    avg_word_length = sum(word_lengths) / len(word_lengths) if word_lengths else 0
    
    # If average word length is very short and there's little punctuation, 
    # it might be just a list of names
    if avg_word_length < 4 and text.count('.') < 3:
        return False
    
    return True

def load_articles(raw_data_dir='backend/data/raw'):
    """Load all article JSON files from raw data directory"""
    articles = []
    
    # Get all JSON files that contain article data
    json_files = [f for f in os.listdir(raw_data_dir) if f.endswith('.json') and 'mihaaru_article' in f]
    
    logging.info(f"Found {len(json_files)} article files to process")
    
    for filename in tqdm(json_files, desc="Loading articles"):
        try:
            with open(os.path.join(raw_data_dir, filename), 'r', encoding='utf-8') as f:
                article_data = json.load(f)
                
                # Only include articles with actual content
                if article_data and 'content' in article_data and len(article_data['content']) > 100:
                    articles.append(article_data)
        except Exception as e:
            logging.error(f"Error loading {filename}: {str(e)}")
    
    logging.info(f"Successfully loaded {len(articles)} articles")
    return articles

def sample_and_check_article(article):
    """Debug function to check if an article meets quality criteria"""
    cleaned_content = clean_text(article['content'])
    cleaned_title = clean_text(article['title'])
    
    # Count non-Dhivehi characters in original vs cleaned content
    original_non_dhivehi = sum(1 for char in article['content'] 
                             if not (char.isspace() or char.isdigit() or 
                                    char in ".,;:!?-()[]{}\"'،" or 
                                    '\u0780' <= char <= '\u07BF'))
    
    cleaned_non_dhivehi = sum(1 for char in cleaned_content 
                            if not (char.isspace() or char.isdigit() or 
                                   char in ".,;:!?-()[]{}\"'،" or 
                                   '\u0780' <= char <= '\u07BF'))
    
    checks = {
        "title_length_ok": len(cleaned_title) >= 15,
        "content_length_ok": len(cleaned_content) >= 300,
        "has_punctuation": bool(re.search(r'[.،:؛!?]', cleaned_content)),
        "word_count_ok": len(cleaned_content.split()) >= 30,
        "passes_validity_check": is_valid_content(cleaned_content),
        "is_dhivehi_title": is_dhivehi_text(cleaned_title),
        "is_dhivehi_content": is_dhivehi_text(cleaned_content),
        "orig_non_dhivehi_chars": original_non_dhivehi,
        "cleaned_non_dhivehi_chars": cleaned_non_dhivehi
    }
    
    return {
        "title": cleaned_title,
        "content_preview": cleaned_content[:100] + "...",
        "content_length": len(cleaned_content),
        "word_count": len(cleaned_content.split()),
        "quality_checks": checks,
        "would_be_included": all([v for k, v in checks.items() if k != "orig_non_dhivehi_chars" and k != "cleaned_non_dhivehi_chars"])
    }

def preprocess_articles(articles):
    """Clean and preprocess article data with improved quality filtering and Dhivehi detection"""
    processed_articles = []
    filtered_count = 0
    non_dhivehi_count = 0
    
    for article in tqdm(articles, desc="Preprocessing articles"):
        try:
            # Skip if either title or content is missing
            if not article.get('title') or not article.get('content'):
                filtered_count += 1
                continue
                
            # Clean article content with Dhivehi-only filter
            cleaned_content = clean_text(article['content'])
            
            # Clean title with Dhivehi-only filter
            cleaned_title = clean_text(article['title'])
            
            # Check if the content is primarily Dhivehi
            if not is_dhivehi_text(cleaned_content):
                non_dhivehi_count += 1
                continue
                
            # Also check if the title is in Dhivehi
            if not is_dhivehi_text(cleaned_title):
                non_dhivehi_count += 1
                continue
            
            # Apply stricter quality checks
            if len(cleaned_title) < 15:  # Title should be substantial
                filtered_count += 1
                continue
                
            if len(cleaned_content) < 300:  # Content should be substantial
                filtered_count += 1
                continue
                
            if not is_valid_content(cleaned_content):
                filtered_count += 1
                continue
            
            # Create simplified article object with only title and content
            processed_article = {
                'title': cleaned_title,
                'content': cleaned_content
            }
            
            processed_articles.append(processed_article)
            
        except Exception as e:
            logging.error(f"Error preprocessing article: {str(e)}")
            filtered_count += 1
    
    logging.info(f"Preprocessed {len(processed_articles)} quality Dhivehi articles")
    logging.info(f"Filtered out: {filtered_count} low-quality articles, {non_dhivehi_count} non-Dhivehi articles")
    return processed_articles

def save_processed_articles(processed_articles):
    """Save processed articles as individual files and as a combined file"""
    processed_dir = 'backend/data/processed/articles'
    
    # Save each article as a separate file
    for i, article in tqdm(enumerate(processed_articles), desc="Saving processed articles"):
        article_file = os.path.join(processed_dir, f"article_{i+1:04d}.json")
        with open(article_file, 'w', encoding='utf-8') as f:
            json.dump(article, f, ensure_ascii=False, indent=4)
    
    # Also save as a single file for convenience
    processed_path = 'backend/data/processed/processed_articles.json'
    with open(processed_path, 'w', encoding='utf-8') as f:
        json.dump(processed_articles, f, ensure_ascii=False, indent=4)
    
    logging.info(f"Saved {len(processed_articles)} high-quality article files to {processed_dir}")
    logging.info(f"Saved all processed articles to {processed_path}")

def format_for_gemma(articles):
    """Format articles for Gemma 2B training with improved prompts for Dhivehi"""
    formatted_data = []
    
    for article in tqdm(articles, desc="Formatting for Gemma"):
        # Skip any problematic articles (extra safety check)
        if not article.get('title') or not article.get('content') or len(article['content']) < 300:
            continue
            
        # Extra check to ensure it's Dhivehi
        if not is_dhivehi_text(article['title']) or not is_dhivehi_text(article['content']):
            continue
            
        # Format 1: Article generation from title
        title_format = {
            "text": f"<start_of_turn>user\nGenerate a news article in Dhivehi with the title: {article['title']}<end_of_turn>\n\n<start_of_turn>model\n{article['content']}<end_of_turn>"
        }
        
        # Format 2: Article summarization
        summary_format = {
            "text": f"<start_of_turn>user\nSummarize the following Dhivehi news article:\n\n{article['content']}<end_of_turn>\n\n<start_of_turn>model\n{article['title']}<end_of_turn>"
        }
        
        # Format 3: News information extraction (improved)
        # Extract first sentence as a potential key point to make the task more concrete
        first_sentence = re.split(r'[.!?]', article['content'])[0] if article['content'] else ""
        
        info_format = {
            "text": f"<start_of_turn>user\nExtract the key information from this Dhivehi news article:\n\n{article['content']}<end_of_turn>\n\n<start_of_turn>model\nTitle: {article['title']}\nKey points:\n- {first_sentence}\n- [Second key point extracted from content]\n- [Third key point extracted from content]<end_of_turn>"
        }
        
        formatted_data.extend([title_format, summary_format, info_format])
    
    logging.info(f"Created {len(formatted_data)} formatted examples for Gemma from Dhivehi articles")
    return formatted_data

def create_dataset(processed_articles):
    """Create and split dataset for training"""
    # Format data for Gemma 2B
    formatted_data = format_for_gemma(processed_articles)
    
    # Create pandas DataFrame
    df = pd.DataFrame(formatted_data)
    
    # Split into train, validation, and test sets (80%, 10%, 10%)
    train_df, temp_df = train_test_split(df, test_size=0.2, random_state=42)
    val_df, test_df = train_test_split(temp_df, test_size=0.5, random_state=42)
    
    logging.info(f"Dataset split: Train={len(train_df)}, Validation={len(val_df)}, Test={len(test_df)}")
    
    # Save as JSONL files (one JSON object per line)
    train_path = 'backend/data/processed/gemma/train.jsonl'
    val_path = 'backend/data/processed/gemma/validation.jsonl'
    test_path = 'backend/data/processed/gemma/test.jsonl'
    
    train_df.to_json(train_path, orient='records', lines=True, force_ascii=False)
    val_df.to_json(val_path, orient='records', lines=True, force_ascii=False)
    test_df.to_json(test_path, orient='records', lines=True, force_ascii=False)
    
    logging.info(f"Saved dataset files: {train_path}, {val_path}, {test_path}")
    
    # Also save a few examples as plain text for inspection
    with open('backend/data/processed/gemma/examples.txt', 'w', encoding='utf-8') as f:
        f.write(f"DATASET EXAMPLES (Generated {datetime.now().strftime('%Y-%m-%d')})\n\n")
        f.write("="*80 + "\n\n")
        
        for i, example in enumerate(train_df.head(5).to_dict('records')):
            f.write(f"EXAMPLE {i+1}:\n")
            f.write(example['text'])
            f.write("\n\n" + "="*80 + "\n\n")
    
    # Create metadata file
    metadata = {
        'dataset_name': 'mihaaru_news_corpus',
        'version': '1.0',
        'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'description': 'Processed Dhivehi news articles for LLM training (title and content only)',
        'language': 'Dhivehi',
        'num_examples': len(formatted_data),
        'fields': ['title', 'content'],
        'split_sizes': {
            'train': len(train_df),
            'validation': len(val_df),
            'test': len(test_df)
        },
        'format': 'JSONL with text field for Gemma 2B training'
    }
    
    with open('backend/data/processed/gemma/metadata.json', 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=4)
    
    return {
        'train': train_path,
        'validation': val_path,
        'test': test_path,
        'metadata': 'backend/data/processed/gemma/metadata.json'
    }

def main():
    logging.info("Starting Dhivehi article processing for Gemma 2B training")
    
    # Step 1: Load raw article data
    articles = load_articles()
    
    # Optional: Sample a few articles to check quality filtering
    if len(articles) > 0:
        sample_size = min(5, len(articles))
        sample_articles = random.sample(articles, sample_size)
        
        logging.info("Quality check on sample articles:")
        for i, article in enumerate(sample_articles):
            check_result = sample_and_check_article(article)
            logging.info(f"Sample {i+1}:")
            logging.info(f"  Title: {check_result['title']}")
            logging.info(f"  Content preview: {check_result['content_preview']}")
            logging.info(f"  Content length: {check_result['content_length']} chars, {check_result['word_count']} words")
            logging.info(f"  Quality checks: {check_result['quality_checks']}")
            logging.info(f"  Is Dhivehi title: {check_result['quality_checks']['is_dhivehi_title']}")
            logging.info(f"  Is Dhivehi content: {check_result['quality_checks']['is_dhivehi_content']}")
            logging.info(f"  Original non-Dhivehi chars: {check_result['quality_checks']['orig_non_dhivehi_chars']}")
            logging.info(f"  Cleaned non-Dhivehi chars: {check_result['quality_checks']['cleaned_non_dhivehi_chars']}")
            logging.info(f"  Would be included: {check_result['would_be_included']}")
    
    # Step 2: Clean and preprocess articles with improved quality filtering and Dhivehi detection
    processed_articles = preprocess_articles(articles)
    
    # Check if we have enough quality Dhivehi articles
    if len(processed_articles) < 50:
        logging.warning(f"Only {len(processed_articles)} Dhivehi articles passed quality checks. Consider relaxing criteria if this is too few.")
    
    # Step 3: Save each processed article separately
    save_processed_articles(processed_articles)
    
    # Step 4: Create and save training dataset
    if len(processed_articles) > 0:
        dataset_paths = create_dataset(processed_articles)
        
        logging.info(f"Processing complete. Dhivehi dataset ready for Gemma 2B training.")
        logging.info(f"Training data: {dataset_paths['train']}")
        logging.info(f"Validation data: {dataset_paths['validation']}")
        logging.info(f"Test data: {dataset_paths['test']}")
        logging.info(f"Metadata: {dataset_paths['metadata']}")
    else:
        logging.error("No Dhivehi articles passed quality checks. Cannot create training dataset.")

if __name__ == "__main__":
    main()