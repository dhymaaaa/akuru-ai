import requests
from bs4 import BeautifulSoup
import time
import random
import os
import re
import json
from datetime import datetime

# Create folder if it doesn't exist
if not os.path.exists('backend/data/raw/psm'):
    os.makedirs('backend/data/raw/psm')

# Function to scrape a PSM News article
def scrape_psm_article(url):
    try:
        # Add headers to avoid being blocked
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code != 200:
            print(f"Failed to fetch {url}, status code: {response.status_code}")
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract article title - based on the HTML structure from inspect
        title = soup.find('h2', class_='font-waheed')
        title_text = title.text.strip() if title else "No title found"
        
        # Extract date - might be in various locations
        date_element = soup.find('time') or soup.find('div', class_=lambda c: c and 'text-grey' in c)
        date_text = date_element.text.strip() if date_element else "No date found"
        
        # Extract article content - look for article text content
        content_paragraphs = []
        
        # Find all paragraph elements in the article - based on the HTML structure
        article_container = soup.find('div', class_=lambda c: c and 'p-4' in c)
        if article_container:
            paragraphs = article_container.find_all('p')
        else:
            # Try alternate approach to find the main content
            article_containers = soup.find_all('div', class_=lambda c: c and 'flex-col' in c)
            paragraphs = []
            for container in article_containers:
                paragraphs.extend(container.find_all('p'))
        
        # If still no paragraphs, get all paragraphs
        if not paragraphs:
            paragraphs = soup.find_all('p')
        
        for p in paragraphs:
            if p.text.strip() and len(p.text.strip()) > 20:  # Skip short paragraphs
                content_paragraphs.append(p.text.strip())
        
        content_text = "\n\n".join(content_paragraphs)
        
        # If no content was found, try one more approach
        if not content_text:
            main_content = soup.find('div', class_=lambda c: c and 'flex-col' in c)
            if main_content:
                content_text = main_content.get_text(strip=True, separator="\n\n")
        
        # Check if we actually found content
        if not content_text or len(content_text) < 100:  # Minimum content length check
            print(f"No substantial content found in {url}")
            return None
        
        # Extract images if available
        images = []
        for img in soup.find_all('figure', class_=lambda c: c and 'bg-cover' in c):
            style = img.get('style', '')
            img_url_match = re.search(r'url\("([^"]+)"\)', style)
            if img_url_match:
                images.append(img_url_match.group(1))
        
        return {
            'url': url,
            'title': title_text,
            'date': date_text,
            'content': content_text,
            # 'images': images,
            # 'source': 'psm',
            # 'scraped_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
    except Exception as e:
        print(f"Error scraping {url}: {str(e)}")
        return None

# Function to get article links from PSM News
def get_psm_article_links(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        links = []
        # Find all article links - based on the HTML structure from inspect
        article_elements = soup.find_all('a', href=lambda href: href and 'psmnews.mv' in href and '/156' in href)
        
        for element in article_elements:
            href = element['href']
            if href not in links:
                links.append(href)
        
        # Remove duplicates
        return list(set(links))
        
    except Exception as e:
        print(f"Error getting PSM article links from {url}: {str(e)}")
        return []

# Function to extract article ID from URL
def extract_article_id(url):
    # Pattern like https://psmnews.mv/156365
    match = re.search(r'psmnews\.mv/(\d+)', url)
    if match:
        return match.group(1)
    
    # Default: use a timestamp-based ID
    return f"psm_{int(time.time())}"

# Function to scrape by article IDs for PSM
def scrape_psm_by_ids(start_id=156000, max_articles=275):
    articles = []
    articles_scraped = 0
    current_id = start_id
    failed_consecutive = 0
    
    while articles_scraped < max_articles and failed_consecutive < 50:  # Stop if too many consecutive failures
        url = f"https://psmnews.mv/{current_id}"
        print(f"Trying PSM article ID: {current_id} ({articles_scraped+1}/{max_articles})")
        
        article_data = scrape_psm_article(url)
        
        if article_data:
            # Save individual article to JSON
            article_file = f'backend/data/raw/psm/psm_article_{current_id}.json'
            with open(article_file, 'w', encoding='utf-8') as f:
                json.dump(article_data, f, ensure_ascii=False, indent=4)
            
            articles.append(article_data)
            articles_scraped += 1
            failed_consecutive = 0  # Reset counter on success
            
            # Save progress periodically
            if articles_scraped % 10 == 0:
                print(f"Scraped {articles_scraped} PSM articles")
        else:
            failed_consecutive += 1
            print(f"Failed to scrape PSM article ID: {current_id}")
        
        # Move to next ID
        current_id += 1
        
        # Be nice to the server with a small delay
        time.sleep(random.uniform(2, 5))
    
    print(f"Finished scraping {len(articles)} PSM articles")
    return articles

# Function to navigate pages and find articles for PSM
def scrape_psm_by_navigation(max_articles=275):
    all_articles = []
    articles_scraped = 0
    page_num = 1
    
    # Keep track of URLs we've already scraped
    scraped_urls = set()
    
    # Keep going until we have enough articles or run out of new content
    while articles_scraped < max_articles:
        possible_urls = [
            "https://psmnews.mv/",
            f"https://psmnews.mv/news?page={page_num}",
            "https://psmnews.mv/latest"
        ]
        
        # Try to find article links from each URL
        found_new_links = False
        
        for base_url in possible_urls:
            print(f"Getting article links from {base_url}")
            article_links = get_psm_article_links(base_url)
            
            if not article_links:
                print(f"No article links found on {base_url}")
                continue
                
            print(f"Found {len(article_links)} links")
            
            # Process each article
            for link in article_links:
                # Skip already scraped URLs
                if link in scraped_urls:
                    continue
                    
                found_new_links = True
                print(f"Scraping PSM article {articles_scraped+1}/{max_articles}: {link}")
                
                article_data = scrape_psm_article(link)
                
                if article_data:
                    # Extract article ID for filename
                    article_id = extract_article_id(link)
                    
                    # Save individual article to JSON
                    article_file = f'backend/data/raw/psm/psm_article_{article_id}.json'
                    with open(article_file, 'w', encoding='utf-8') as f:
                        json.dump(article_data, f, ensure_ascii=False, indent=4)
                    
                    all_articles.append(article_data)
                    scraped_urls.add(link)
                    articles_scraped += 1
                    
                    # Save progress periodically
                    if articles_scraped % 10 == 0:
                        print(f"Saved {articles_scraped} PSM articles")
                    
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
            print("Reached end of available content for PSM")
            break
    
    print(f"Finished scraping {len(all_articles)} PSM articles via navigation")
    return all_articles

# Main function to run the complete scraping operation
def main():
    # Method 1: Scrape by article IDs
    print("Starting PSM scraping by article IDs")
    psm_articles = scrape_psm_by_ids(start_id=156000, max_articles=275)
    
    # If we didn't get enough articles, try navigation method
    if len(psm_articles) < 275:
        print(f"Only scraped {len(psm_articles)} articles by ID. Trying navigation method.")
        remaining_articles = 275 - len(psm_articles)
        scrape_psm_by_navigation(max_articles=remaining_articles)
    
    print(f"Finished scraping operation. Articles saved to 'backend/data/raw/psm' folder.")

if __name__ == "__main__":
    main()