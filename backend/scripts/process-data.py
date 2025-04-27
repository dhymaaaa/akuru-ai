import os
import json
import re
import random
from datetime import datetime
import logging
from tqdm import tqdm
import pandas as pd
from sklearn.model_selection import train_test_split
import glob
import sys
import codecs

# Fix console encoding for Windows to handle Dhivehi characters
if sys.platform == 'win32':
    # Force UTF-8 encoding for stdout and stderr
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Create necessary directories
os.makedirs('backend/data/processed', exist_ok=True)
os.makedirs('backend/data/processed/logs', exist_ok=True)
os.makedirs('backend/data/processed/gemma3', exist_ok=True)
os.makedirs('backend/data/processed/articles', exist_ok=True)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("backend/data/processed/logs/processing.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Safe logging function to handle encoding errors
def safe_log(message, level="info"):
    try:
        if level == "info":
            logging.info(message)
        elif level == "warning":
            logging.warning(message)
        elif level == "error":
            logging.error(message)
    except UnicodeEncodeError:
        # Fall back to basic ASCII with replacements if there's an encoding error
        ascii_message = message.encode('ascii', 'replace').decode('ascii')
        if level == "info":
            logging.info(ascii_message + " [Contains non-ASCII characters]")
        elif level == "warning":
            logging.warning(ascii_message + " [Contains non-ASCII characters]")
        elif level == "error":
            logging.error(ascii_message + " [Contains non-ASCII characters]")

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
    
    # Remove common footer elements across different news sites
    text = re.sub(r'Copyright © \d+ (Mihaaru|Sun|Raajje|Adhadhu|PSM).*', '', text)
    text = re.sub(r"SMS 'sub (mihaaru|sun|raajje|adhadhu|psm)' to \d+", '', text)
    text = re.sub(r'Deliver popular news headlines to your inbox!.*', '', text)
    
    # Remove PSM specific footer
    text = re.sub(r"Public Service Media\s+Radio Building, Ameenee Magu\s+Male', \d+, Republic of Maldives", '', text)
    text = re.sub(r"© \d+ PSM News\. Public Service Media\. All rights reserved\.", '', text)
    
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
    return dhivehi_percentage >= 95

def is_valid_content(text):
    """Check if content appears to be a valid article rather than random words or names"""
    if not text:
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

def load_all_articles(raw_data_dir='backend/data/raw'):
    """Load articles from all 5 news websites"""
    all_articles = []
    site_counts = {}
    
    # Define each news site's folder and article prefix pattern
    news_sites = [
        {'folder': 'sun', 'pattern': 'sun_article_*.json'},
        {'folder': 'mihaaru', 'pattern': 'mihaaru_article_*.json'},
        {'folder': 'raajje', 'pattern': 'raajje_article_*.json'},
        {'folder': 'adhadhu', 'pattern': 'adhadhu_article_*.json'},
        {'folder': 'psm', 'pattern': 'psm_article_*.json'}
    ]
    
    for site in news_sites:
        folder = site['folder']
        pattern = site['pattern']
        site_folder = os.path.join(raw_data_dir, folder)
        
        if not os.path.exists(site_folder):
            safe_log(f"Directory {site_folder} does not exist, skipping.", "warning")
            site_counts[folder] = 0
            continue
        
        # Get all JSON files that match the pattern
        file_pattern = os.path.join(site_folder, pattern)
        json_files = glob.glob(file_pattern)
        
        safe_log(f"Found {len(json_files)} article files from {folder}")
        site_articles = []
        
        for filename in tqdm(json_files, desc=f"Loading {folder} articles"):
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    article_data = json.load(f)
                    
                    # Add source information
                    article_data['source'] = folder
                    
                    # Only include articles with actual content
                    if article_data and 'content' in article_data:
                        site_articles.append(article_data)
            except Exception as e:
                safe_log(f"Error loading {filename}: {str(e)}", "error")
        
        site_counts[folder] = len(site_articles)
        all_articles.extend(site_articles)
    
    # Log article counts by source
    safe_log("Articles by source:")
    for site, count in site_counts.items():
        safe_log(f"  {site}: {count} articles")
    
    safe_log(f"Successfully loaded {len(all_articles)} total articles from all sources")
    return all_articles

def sample_and_check_article(article):
    """Debug function to check if an article meets quality criteria"""
    cleaned_content = clean_text(article['content'])
    cleaned_title = clean_text(article.get('title', ''))
    
    # Count non-Dhivehi characters in original vs cleaned content
    original_non_dhivehi = sum(1 for char in article['content'] 
                             if not (char.isspace() or char.isdigit() or 
                                    char in ".,;:!?-()[]{}\"'،" or 
                                    '\u0780' <= char <= '\u07BF'))
    
    cleaned_non_dhivehi = sum(1 for char in cleaned_content 
                            if not (char.isspace() or char.isdigit() or 
                                   char in ".,;:!?-()[]{}\"'،" or 
                                   '\u0780' <= char <= '\u07BF'))
    
    # For Sun articles missing title, check if we'd generate a valid title
    if article.get('source') == 'sun' and (not cleaned_title or not is_dhivehi_text(cleaned_title)):
        first_sentence = re.split(r'[.!?،]', cleaned_content)[0] if cleaned_content else ""
        if len(first_sentence) > 15:
            # Use first sentence as title
            generated_title = first_sentence
            has_generated_title = True
        else:
            # Use placeholder title in Dhivehi ("Sun News Article")
            generated_title = "ސަން ނިއުސް އާޓިކަލް"
            has_generated_title = True
    else:
        generated_title = None
        has_generated_title = False
    
    checks = {
        "title_length_ok": len(cleaned_title) >= 15 if not has_generated_title else len(generated_title) >= 15,
        "has_punctuation": bool(re.search(r'[.،:؛!?]', cleaned_content)),
        "word_count_ok": len(cleaned_content.split()) >= 30,
        "passes_validity_check": is_valid_content(cleaned_content),
        "is_dhivehi_title": is_dhivehi_text(cleaned_title) if not has_generated_title else True,
        "is_dhivehi_content": is_dhivehi_text(cleaned_content),
        "orig_non_dhivehi_chars": original_non_dhivehi,
        "cleaned_non_dhivehi_chars": cleaned_non_dhivehi,
        "has_generated_title": has_generated_title,
        "generated_title": generated_title
    }
    
    return {
        "source": article.get('source', 'unknown'),
        "title": cleaned_title if not has_generated_title else generated_title,
        "content_preview": cleaned_content[:100] + "..." if len(cleaned_content) > 100 else cleaned_content,
        "content_length": len(cleaned_content),
        "word_count": len(cleaned_content.split()),
        "quality_checks": checks,
        "would_be_included": all([v for k, v in checks.items() if k not in ["orig_non_dhivehi_chars", "cleaned_non_dhivehi_chars", "has_generated_title", "generated_title"]])
    }

def preprocess_articles(articles):
    """Clean and preprocess article data with improved quality filtering and Dhivehi detection"""
    processed_articles = []
    filtered_count = 0
    non_dhivehi_count = 0
    generated_titles_count = 0
    source_stats = {}
    
    for article in tqdm(articles, desc="Preprocessing articles"):
        try:
            source = article.get('source', 'unknown')
            if source not in source_stats:
                source_stats[source] = {'processed': 0, 'filtered': 0, 'non_dhivehi': 0, 'generated_titles': 0}
            
            # Clean article content with Dhivehi-only filter
            cleaned_content = clean_text(article.get('content', ''))
            
            # Check if the content is primarily Dhivehi
            if not is_dhivehi_text(cleaned_content):
                non_dhivehi_count += 1
                source_stats[source]['non_dhivehi'] += 1
                continue
            
            # Special handling for Sun articles with missing titles
            if source == 'sun' and (not article.get('title') or not is_dhivehi_text(clean_text(article.get('title', '')))):
                # Extract first sentence as title or use placeholder
                sentences = re.split(r'[.!?،]', cleaned_content)
                first_sentence = sentences[0] if sentences else ""
                
                if len(first_sentence) > 15:
                    # Use first sentence as title if it's long enough
                    cleaned_title = first_sentence
                else:
                    # Use placeholder title in Dhivehi ("Sun News Article")
                    cleaned_title = "ސަން ނިއުސް އާޓިކަލް"
                
                generated_titles_count += 1
                source_stats[source]['generated_titles'] += 1
            else:
                # Clean title with Dhivehi-only filter
                cleaned_title = clean_text(article.get('title', ''))
                
                # Check if the title is in Dhivehi
                if not is_dhivehi_text(cleaned_title):
                    non_dhivehi_count += 1
                    source_stats[source]['non_dhivehi'] += 1
                    continue
            
            # Apply quality checks
            if len(cleaned_title) < 15:  # Title should be substantial
                filtered_count += 1
                source_stats[source]['filtered'] += 1
                continue
                
            if not is_valid_content(cleaned_content):
                filtered_count += 1
                source_stats[source]['filtered'] += 1
                continue
            
            # Create simplified article object with title, content and source
            processed_article = {
                'title': cleaned_title,
                'content': cleaned_content,
                'source': source
            }
            
            processed_articles.append(processed_article)
            source_stats[source]['processed'] += 1
            
        except Exception as e:
            safe_log(f"Error preprocessing article: {str(e)}", "error")
            filtered_count += 1
    
    # Log statistics by source
    safe_log("Processing statistics by source:")
    for source, stats in source_stats.items():
        total = stats['processed'] + stats['filtered'] + stats['non_dhivehi']
        generated_titles_info = f", {stats['generated_titles']} with generated titles" if stats['generated_titles'] > 0 else ""
        safe_log(f"  {source}: {stats['processed']} processed, {stats['filtered']} filtered, {stats['non_dhivehi']} non-Dhivehi (from {total} total){generated_titles_info}")
    
    safe_log(f"Preprocessed {len(processed_articles)} quality Dhivehi articles from all sources")
    safe_log(f"Filtered out: {filtered_count} low-quality articles, {non_dhivehi_count} non-Dhivehi articles")
    if generated_titles_count > 0:
        safe_log(f"Generated titles for {generated_titles_count} articles with missing or non-Dhivehi titles")
    
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
    
    safe_log(f"Saved {len(processed_articles)} high-quality article files to {processed_dir}")
    safe_log(f"Saved all processed articles to {processed_path}")

def format_for_gemma3(articles):
    """Format articles for Gemma 3 1B training with improved prompts for Dhivehi"""
    formatted_data = []
    
    for article in tqdm(articles, desc="Formatting for Gemma 3"):
        # Skip any problematic articles (extra safety check)
        if not article.get('title') or not article.get('content'):
            continue
            
        # Extra check to ensure it's Dhivehi
        if not is_dhivehi_text(article['title']) or not is_dhivehi_text(article['content']):
            continue
            
        # Format 1: Article generation from title
        title_format = {
            "messages": [
                {"role": "user", "content": f"Generate a news article in Dhivehi with the title: {article['title']}"},
                {"role": "assistant", "content": article['content']}
            ]
        }
        
        # Format 2: Article summarization
        summary_format = {
            "messages": [
                {"role": "user", "content": f"Summarize the following Dhivehi news article:\n\n{article['content']}"},
                {"role": "assistant", "content": article['title']}
            ]
        }
        
        # Format 3: News information extraction
        # Extract first sentence as a potential key point to make the task more concrete
        first_sentence = re.split(r'[.!?]', article['content'])[0] if article['content'] else ""
        
        info_format = {
            "messages": [
                {"role": "user", "content": f"Extract the key information from this Dhivehi news article:\n\n{article['content']}"},
                {"role": "assistant", "content": f"Title: {article['title']}\nKey points:\n- {first_sentence}\n- [Additional key information from the article]\n- [Further important details from the text]"}
            ]
        }
        
        # Format 4: Continue article from beginning
        # Take first third of article as prompt and rest as completion
        tokens = article['content'].split()
        first_third = " ".join(tokens[:len(tokens)//3])
        rest_of_article = " ".join(tokens[len(tokens)//3:])
        
        if len(first_third) > 100 and len(rest_of_article) > 100:  # Only if we have enough content
            continuation_format = {
                "messages": [
                    {"role": "user", "content": f"Continue this Dhivehi news article:\n\n{first_third}"},
                    {"role": "assistant", "content": rest_of_article}
                ]
            }
            formatted_data.append(continuation_format)
        
        formatted_data.extend([title_format, summary_format, info_format])
    
    safe_log(f"Created {len(formatted_data)} formatted examples for Gemma 3 from Dhivehi articles")
    return formatted_data

def create_dataset(processed_articles):
    """Create and split dataset for training Gemma 3 1B"""
    # Format data for Gemma 3
    formatted_data = format_for_gemma3(processed_articles)
    
    # Create pandas DataFrame
    df = pd.DataFrame({'json': [json.dumps(item, ensure_ascii=False) for item in formatted_data]})
    
    # Split into train, validation, and test sets (80%, 10%, 10%)
    train_df, temp_df = train_test_split(df, test_size=0.2, random_state=42)
    val_df, test_df = train_test_split(temp_df, test_size=0.5, random_state=42)
    
    safe_log(f"Dataset split: Train={len(train_df)}, Validation={len(val_df)}, Test={len(test_df)}")
    
    # Save as JSONL files (one JSON object per line)
    train_path = 'backend/data/processed/gemma3/train.jsonl'
    val_path = 'backend/data/processed/gemma3/validation.jsonl'
    test_path = 'backend/data/processed/gemma3/test.jsonl'
    
    with open(train_path, 'w', encoding='utf-8') as f:
        for json_str in train_df['json']:
            f.write(json_str + '\n')
            
    with open(val_path, 'w', encoding='utf-8') as f:
        for json_str in val_df['json']:
            f.write(json_str + '\n')
            
    with open(test_path, 'w', encoding='utf-8') as f:
        for json_str in test_df['json']:
            f.write(json_str + '\n')
    
    safe_log(f"Saved dataset files: {train_path}, {val_path}, {test_path}")
    
    # Also save a few examples as plain text for inspection
    with open('backend/data/processed/gemma3/examples.txt', 'w', encoding='utf-8') as f:
        f.write(f"DATASET EXAMPLES (Generated {datetime.now().strftime('%Y-%m-%d')})\n\n")
        f.write("="*80 + "\n\n")
        
        for i, json_str in enumerate(train_df.head(5)['json']):
            example = json.loads(json_str)
            f.write(f"EXAMPLE {i+1}:\n")
            for message in example['messages']:
                f.write(f"{message['role'].upper()}: {message['content']}\n\n")
            f.write("="*80 + "\n\n")
    
    # Create metadata file
    metadata = {
        'dataset_name': 'dhivehi_news_corpus',
        'version': '1.0',
        'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'description': 'Processed Dhivehi news articles from multiple sources for Gemma 3 1B training',
        'language': 'Dhivehi',
        'num_examples': len(formatted_data),
        'sources': list(set([article.get('source', 'unknown') for article in processed_articles])),
        'split_sizes': {
            'train': len(train_df),
            'validation': len(val_df),
            'test': len(test_df)
        },
        'format': 'JSONL with chat format for Gemma 3 1B training'
    }
    
    with open('backend/data/processed/gemma3/metadata.json', 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=4)
    
    return {
        'train': train_path,
        'validation': val_path,
        'test': test_path,
        'metadata': 'backend/data/processed/gemma3/metadata.json'
    }

def main():
    safe_log("Starting Dhivehi article processing for Gemma 3 1B training")
    
    # Step 1: Load raw article data from all sources
    articles = load_all_articles()
    
    # # Optional: Sample a few articles from each source to check quality filtering
    # if articles:
    #     # Group articles by source
    #     articles_by_source = {}
    #     for article in articles:
    #         source = article.get('source', 'unknown')
    #         if source not in articles_by_source:
    #             articles_by_source[source] = []
    #         articles_by_source[source].append(article)
        
    #     # Sample from each source
    #     safe_log("Quality check on sample articles by source:")
    #     for source, source_articles in articles_by_source.items():
    #         sample_size = min(3, len(source_articles))
    #         if sample_size > 0:
    #             sample_articles = random.sample(source_articles, sample_size)
                
    #             safe_log(f"Samples from {source}:")
    #             for i, article in enumerate(sample_articles):
    #                 check_result = sample_and_check_article(article)
    #                 safe_log(f"  Sample {i+1}:")
    #                 safe_log(f"    Title: {check_result['title']}")
    #                 safe_log(f"    Content preview: {check_result['content_preview']}")
    #                 safe_log(f"    Content length: {check_result['content_length']} chars, {check_result['word_count']} words")
    #                 safe_log(f"    Is Dhivehi title: {check_result['quality_checks']['is_dhivehi_title']}")
    #                 safe_log(f"    Is Dhivehi content: {check_result['quality_checks']['is_dhivehi_content']}")
                    
    #                 # Show generated title info if applicable
    #                 if check_result['quality_checks'].get('has_generated_title', False):
    #                     safe_log(f"    Generated title: {check_result['quality_checks']['generated_title']}")
                    
    #                 safe_log(f"    Would be included: {check_result['would_be_included']}")
    
    # Step 2: Clean and preprocess articles
    processed_articles = preprocess_articles(articles)
    
    # Check if we have enough quality Dhivehi articles
    if len(processed_articles) < 100:
        safe_log(f"Only {len(processed_articles)} Dhivehi articles passed quality checks. Consider relaxing criteria.", "warning")
    
    # Step 3: Save each processed article separately
    save_processed_articles(processed_articles)
    
    # Step 4: Create and save training dataset for Gemma 3 1B
    if len(processed_articles) > 0:
        dataset_paths = create_dataset(processed_articles)
        
        safe_log("Processing complete. Dhivehi dataset ready for Gemma 3 1B training.")
        safe_log(f"Training data: {dataset_paths['train']}")
        safe_log(f"Validation data: {dataset_paths['validation']}")
        safe_log(f"Test data: {dataset_paths['test']}")
        safe_log(f"Metadata: {dataset_paths['metadata']}")
    else:
        safe_log("No Dhivehi articles passed quality checks. Cannot create training dataset.", "error")

if __name__ == "__main__":
    main()