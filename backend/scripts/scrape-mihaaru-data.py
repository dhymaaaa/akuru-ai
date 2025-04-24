import requests
from bs4 import BeautifulSoup
import time
import random
import os
from datetime import datetime
import re
import json
import logging

# Create folder if it doesn't exist BEFORE setting up logging
if not os.path.exists('backend/data/raw/mihaaru'):
    os.makedirs('backend/data/raw/mihaaru')

# # Set up logging AFTER directory is created
# logging.basicConfig(
#     level=print,
#     format='%(asctime)s - %(levelname)s - %(message)s',
#     handlers=[
#         logging.FileHandler("backend/data/raw/mihaaru/scraping.log"),
#         logging.StreamHandler()
#     ]
# )

# Function to scrape a Mihaaru article
def scrape_mihaaru_article(url):
    try:
        # Add headers to avoid being blocked
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code != 200:
            logging.warning(f"Failed to fetch {url}, status code: {response.status_code}")
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract article title
        title = soup.find('h1')
        title_text = title.text.strip() if title else "No title found"
        
        # Extract date - look for time element or a specific class pattern
        date_element = soup.find('time') or soup.find('div', class_='text-warm-grey-two')
        date_text = date_element.text.strip() if date_element else "No date found"
        
        # Extract article content - look for article text content
        content_paragraphs = []
        
        # Find all paragraph elements in the article
        paragraphs = soup.find_all('p', class_=lambda c: c and ('text-waheed' in c or 'article-content' in c))
        
        # If no specific paragraphs found, try to find the main article container
        if not paragraphs:
            article_container = soup.find('div', class_=lambda c: c and 'container' in c and 'overflow-hidden' in c)
            if article_container:
                paragraphs = article_container.find_all('p')
        
        # If still no paragraphs, get all paragraphs and filter
        if not paragraphs:
            all_paragraphs = soup.find_all('p')
            # Filter out very short paragraphs that might be metadata
            paragraphs = [p for p in all_paragraphs if len(p.text.strip()) > 20]
        
        for p in paragraphs:
            if p.text.strip():  # Skip empty paragraphs
                content_paragraphs.append(p.text.strip())
        
        content_text = "\n\n".join(content_paragraphs)
        
        # If no content was found, try one more approach - get all text in the main div
        if not content_text:
            main_content = soup.find('div', class_=lambda c: c and 'flex-col' in c and 'justify-between' in c)
            if main_content:
                content_text = main_content.get_text(strip=True, separator="\n\n")
        
        # Check if we actually found content
        if not content_text:
            logging.warning(f"No content found in {url}")
            return None
        
        # Store the raw HTML as well
        html_content = response.text
        
        return {
            'url': url,
            'title': title_text,
            'date': date_text,
            'content': content_text,
            # 'html': html_content,
            # 'source': 'mihaaru',
            # 'scraped_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
    except Exception as e:
        logging.error(f"Error scraping {url}: {str(e)}")
        return None

# Function to get article links from Mihaaru
def get_mihaaru_article_links(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        links = []
        article_elements = soup.find_all('a', href=lambda href: href and '/news/' in href)
        
        base_url = "https://mihaaru.com"
        
        for element in article_elements:
            href = element['href']
            # Make sure it's a full URL
            if href.startswith('http'):
                links.append(href)
            else:
                links.append(base_url + href if not href.startswith('/') else base_url + href)
        
        # Remove duplicates
        return list(set(links))
        
    except Exception as e:
        logging.error(f"Error getting Mihaaru article links from {url}: {str(e)}")
        return []

# Function to extract article ID from URL
def extract_article_id(url):
    # Pattern like https://mihaaru.com/news/144535
    match = re.search(r'/news/(\d+)', url)
    if match:
        return match.group(1)
    
    # Default: use a timestamp-based ID
    return f"article_{int(time.time())}"

# Function to scrape by article IDs for Mihaaru
def scrape_mihaaru_by_ids(start_id=144000, max_articles=600):
    articles = []
    articles_scraped = 0
    current_id = start_id
    failed_consecutive = 0
    
    # Keep track of successful and failed IDs
    successful_ids = []
    failed_ids = []
    
    while articles_scraped < max_articles and failed_consecutive < 50:  # Stop if too many consecutive failures
        url = f"https://mihaaru.com/news/{current_id}"
        print(f"Trying Mihaaru article ID: {current_id} ({articles_scraped+1}/{max_articles})")
        
        article_data = scrape_mihaaru_article(url)
        
        if article_data:
            # Save individual article to JSON
            article_file = f'backend/data/raw/mihaaru/mihaaru_article_{current_id}.json'
            with open(article_file, 'w', encoding='utf-8') as f:
                json.dump(article_data, f, ensure_ascii=False, indent=4)
            
            articles.append(article_data)
            successful_ids.append(current_id)
            articles_scraped += 1
            failed_consecutive = 0  # Reset counter on success
            
            # Save progress periodically
            if articles_scraped % 10 == 0:
                print(f"Scraped {articles_scraped} Mihaaru articles")
        else:
            failed_ids.append(current_id)
            failed_consecutive += 1
            logging.warning(f"Failed to scrape Mihaaru article ID: {current_id}")
            
            # # Log failed IDs
            # with open('backend/data/raw/mihaaru/mihaaru_failed_ids.txt', 'a') as f:
            #     f.write(f"{current_id}\n")
        
        # Move to next ID
        current_id += 1
        
        # Be nice to the server with a small delay
        time.sleep(random.uniform(2, 5))
    
    # # Save successful IDs
    # with open('backend/data/raw/mihaaru/mihaaru_successful_ids.txt', 'w') as f:
    #     for id in successful_ids:
    #         f.write(f"{id}\n")
    
    print(f"Finished scraping {len(articles)} Mihaaru articles")
    return articles

# Function to navigate pages and find articles for Mihaaru
def scrape_mihaaru_by_navigation(max_articles=600):
    all_articles = []
    articles_scraped = 0
    page_num = 1
    
    # Keep track of URLs we've already scraped
    scraped_urls = set()
    
    # Read already scraped URLs if resuming a previous run
    if os.path.exists('backend/data/raw/mihaaru/mihaaru_scraped_urls.txt'):
        with open('backend/data/raw/mihaaru/mihaaru_scraped_urls.txt', 'r') as f:
            scraped_urls = set(line.strip() for line in f)
    
    # Keep going until we have enough articles or run out of new content
    while articles_scraped < max_articles:
        possible_urls = [
            "https://mihaaru.com/",
            f"https://mihaaru.com/news?page={page_num}",
            "https://mihaaru.com/news/latest",
        ]
        
        # Try to find article links from each URL
        found_new_links = False
        
        for base_url in possible_urls:
            print(f"Getting article links from {base_url}")
            article_links = get_mihaaru_article_links(base_url)
            
            if not article_links:
                logging.warning(f"No article links found on {base_url}")
                continue
                
            print(f"Found {len(article_links)} links")
            
            # Process each article
            for link in article_links:
                # Skip already scraped URLs
                if link in scraped_urls:
                    continue
                    
                found_new_links = True
                print(f"Scraping Mihaaru article {articles_scraped+1}/{max_articles}: {link}")
                
                article_data = scrape_mihaaru_article(link)
                
                if article_data:
                    # Extract article ID for filename
                    article_id = extract_article_id(link) or f"mihaaru_{articles_scraped}"
                    
                    # Save individual article to JSON
                    article_file = f'backend/data/raw/mihaaru/mihaaru_article_{article_id}.json'
                    with open(article_file, 'w', encoding='utf-8') as f:
                        json.dump(article_data, f, ensure_ascii=False, indent=4)
                    
                    all_articles.append(article_data)
                    scraped_urls.add(link)
                    articles_scraped += 1
                    
                    # Update scraped URLs file
                    with open('backend/data/raw/mihaaru/mihaaru_scraped_urls.txt', 'a') as f:
                        f.write(f"{link}\n")
                    
                    # Save progress periodically
                    if articles_scraped % 10 == 0:
                        print(f"Saved {articles_scraped} Mihaaru articles")
                    
                    # Check if we've reached our target
                    if articles_scraped >= max_articles:
                        break
                
                # Be nice to the server with a small delay
                time.sleep(random.uniform(2, 5))
            
            if articles_scraped >= max_articles:
                break
        
        # If we didn't find any new links on this page, we might be at the end
        if not found_new_links:
            print(f"No new links found on page {page_num}, moving to next page")
        
        # Move to next page
        page_num += 1
        
        # Add a delay between page requests
        time.sleep(random.uniform(3, 7))
        
        # If we've gone through many pages without finding new content, we might be done
        if page_num > 50 and not found_new_links:
            logging.warning("Reached end of available content for Mihaaru")
            break
    
    print(f"Finished scraping {len(all_articles)} Mihaaru articles via navigation")
    return all_articles

# Main function to run the complete scraping operation
def main():
    # Method 1: Scrape Mihaaru by article IDs
    print("Starting Mihaaru scraping by article IDs")
    mihaaru_articles = scrape_mihaaru_by_ids(start_id=144000, max_articles=600)
    
    # If we didn't get enough articles, try navigation method
    if len(mihaaru_articles) < 600:
        print(f"Only scraped {len(mihaaru_articles)} articles by ID. Trying navigation method.")
        remaining_articles = 600 - len(mihaaru_articles)
        scrape_mihaaru_by_navigation(max_articles=remaining_articles)
    
    print("Finished scraping operation. Articles saved to 'raw' folder.")

if __name__ == "__main__":
    main()