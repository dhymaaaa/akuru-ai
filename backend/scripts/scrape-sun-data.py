import requests
from bs4 import BeautifulSoup
import time
import random
import os
import re
import json

# Create folder if it doesn't exist
if not os.path.exists('backend/data/raw/sun'):
    os.makedirs('backend/data/raw/sun')

# Function to scrape a Sun.mv article
def scrape_sun_article(url):
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
        title = soup.find('h2', class_='thaana-eamaan')
        title_text = title.text.strip() if title else "No title found"
        
        # Extract date - looking for the time element
        date_element = soup.find('span', class_='time')
        date_text = date_element.text.strip() if date_element else "No date found"
        
        # Extract article content - look for article text content
        content_paragraphs = []
        
        # Find the main article container
        article_container = soup.find('main')
        if article_container:
            paragraphs = article_container.find_all('p')
        else:
            # Try alternate approach to find the main content
            article_container = soup.find('div', class_='content')
            paragraphs = article_container.find_all('p') if article_container else []
        
        # If still no paragraphs, get all paragraphs
        if not paragraphs:
            paragraphs = soup.find_all('p')
        
        for p in paragraphs:
            if p.text.strip() and len(p.text.strip()) > 20:  # Skip short paragraphs
                content_paragraphs.append(p.text.strip())
        
        content_text = "\n\n".join(content_paragraphs)
        
        # If no content was found, try one more approach
        if not content_text:
            main_content = soup.find('div', class_='article-content')
            if main_content:
                content_text = main_content.get_text(strip=True, separator="\n\n")
        
        # Check if we actually found content
        if not content_text or len(content_text) < 100:  # Minimum content length check
            print(f"No substantial content found in {url}")
            return None
        
        return {
            'url': url,
            'title': title_text,
            'date': date_text,
            'content': content_text
        }
        
    except Exception as e:
        print(f"Error scraping {url}: {str(e)}")
        return None

# Function to get article links from Sun.mv
def get_sun_article_links(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        links = []
        # Find all article links - based on the HTML structure from inspect
        # Looking for links in featured cards
        article_elements = soup.find_all('a', href=lambda href: href and 'sun.mv/' in href and '/205' in href)
        
        for element in article_elements:
            href = element['href']
            if href not in links:
                links.append(href)
        
        # Remove duplicates
        return list(set(links))
        
    except Exception as e:
        print(f"Error getting Sun article links from {url}: {str(e)}")
        return []

# Function to extract article ID from URL
def extract_article_id(url):
    # Pattern like https://sun.mv/205159
    match = re.search(r'sun\.mv/(\d+)', url)
    if match:
        return match.group(1)
    
    # Default: use a timestamp-based ID
    return f"sun_{int(time.time())}"

# Function to scrape by article IDs for Sun.mv
def scrape_sun_by_ids(start_id=205000, max_articles=125):
    articles = []
    articles_scraped = 0
    current_id = start_id
    failed_consecutive = 0
    
    while articles_scraped < max_articles and failed_consecutive < 50:  # Stop if too many consecutive failures
        url = f"https://sun.mv/{current_id}"
        print(f"Trying Sun article ID: {current_id} ({articles_scraped+1}/{max_articles})")
        
        article_data = scrape_sun_article(url)
        
        if article_data:
            # Save individual article to JSON
            article_file = f'backend/data/raw/sun/sun_article_{current_id}.json'
            with open(article_file, 'w', encoding='utf-8') as f:
                json.dump(article_data, f, ensure_ascii=False, indent=4)
            
            articles.append(article_data)
            articles_scraped += 1
            failed_consecutive = 0  # Reset counter on success
            
            # Save progress periodically
            if articles_scraped % 10 == 0:
                print(f"Scraped {articles_scraped} Sun articles")
        else:
            failed_consecutive += 1
            print(f"Failed to scrape Sun article ID: {current_id}")
        
        current_id += 1
        time.sleep(random.uniform(2, 5))
    
    print(f"Finished scraping {len(articles)} Sun articles")
    return articles

# Function to navigate pages and find articles for Sun.mv
def scrape_sun_by_navigation(max_articles=125):
    all_articles = []
    articles_scraped = 0
    page_num = 1
    
    # Keep track of URLs we've already scraped
    scraped_urls = set()
    
    # Keep going until we have enough articles or run out of new content
    while articles_scraped < max_articles:
        possible_urls = [
            "https://sun.mv/",
            f"https://sun.mv/category/featured?page={page_num}",
            f"https://sun.mv/latest?page={page_num}"
        ]
        
        # Try to find article links from each URL
        found_new_links = False
        
        for base_url in possible_urls:
            print(f"Getting article links from {base_url}")
            article_links = get_sun_article_links(base_url)
            
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
                print(f"Scraping Sun article {articles_scraped+1}/{max_articles}: {link}")
                
                article_data = scrape_sun_article(link)
                
                if article_data:
                    # Extract article ID for filename
                    article_id = extract_article_id(link)
                    
                    # Save individual article to JSON
                    article_file = f'backend/data/raw/sun/sun_article_{article_id}.json'
                    with open(article_file, 'w', encoding='utf-8') as f:
                        json.dump(article_data, f, ensure_ascii=False, indent=4)
                    
                    all_articles.append(article_data)
                    scraped_urls.add(link)
                    articles_scraped += 1
                    
                    # Save progress periodically
                    if articles_scraped % 10 == 0:
                        print(f"Saved {articles_scraped} Sun articles")
                    
                    # Check if we've reached our target
                    if articles_scraped >= max_articles:
                        break
                
                time.sleep(random.uniform(2, 5))
            
            if articles_scraped >= max_articles:
                break
        
        # If we didn't find any new links on this page, we might be at the end
        if not found_new_links:
            print(f"No new links found on page {page_num}, moving to next page")
        
        page_num += 1
        
        # Add a delay between page requests
        time.sleep(random.uniform(3, 7))
        
        # If we've gone through many pages without finding new content, we might be done
        if page_num > 50 and not found_new_links:
            print("Reached end of available content for Sun")
            break
    
    print(f"Finished scraping {len(all_articles)} Sun articles via navigation")
    return all_articles

# Main function to run the complete scraping operation
def main():
    # Method 1: Scrape by article IDs
    print("Starting Sun.mv scraping by article IDs")
    sun_articles = scrape_sun_by_ids(start_id=205000, max_articles=125)
    
    # If we didn't get enough articles, try navigation method
    if len(sun_articles) < 125:
        print(f"Only scraped {len(sun_articles)} articles by ID. Trying navigation method.")
        remaining_articles = 125 - len(sun_articles)
        scrape_sun_by_navigation(max_articles=remaining_articles)
    
    print(f"Finished scraping operation. Articles saved to 'backend/data/raw/sun' folder.")

if __name__ == "__main__":
    main()