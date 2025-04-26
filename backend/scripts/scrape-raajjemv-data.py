import requests
from bs4 import BeautifulSoup
import time
import random
import os
import re
import json

# Create folder if it doesn't exist
if not os.path.exists('backend/data/raw/raajjemv'):
    os.makedirs('backend/data/raw/raajjemv')

# Function to scrape a Raajje.mv article
def scrape_raajje_article(url):
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
        
        # Extract article title - based on the HTML structure from image
        # Looking for spans with Thaana text that appear to be titles
        title = soup.find('span') or soup.find('div', class_='text-xl')
        title_text = title.text.strip() if title else "No title found"
        
        # Extract date - looking for the date format seen in the image
        # The image shows "2025-04-25" format with Thaana text
        date_element = soup.find('img', alt=lambda alt: alt and '-' in alt)
        date_text = date_element['alt'] if date_element and 'alt' in date_element.attrs else "No date found"
        
        # Extract article content - look for article text content
        content_paragraphs = []
        
        # Based on the HTML in the image, content might be in these elements:
        article_container = soup.find('div', class_='leading-relaxed') or soup.find('span')
        if article_container:
            # The image shows text within span tags
            content_text = article_container.get_text(strip=True)
        else:
            # Try alternate approaches if the above doesn't work
            paragraphs = soup.find_all('span') or soup.find_all('div', class_='text-xl')
            
            for p in paragraphs:
                if p.text.strip() and len(p.text.strip()) > 20:  # Skip short paragraphs
                    content_paragraphs.append(p.text.strip())
            
            content_text = "\n\n".join(content_paragraphs)
        
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

# Function to get article links from Raajje.mv
def get_raajje_article_links(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        links = []
        # From the image, we can see links like "https://raajje.mv/165373"
        # Look for links containing the pattern '/165' which seems to be the article ID pattern
        article_elements = soup.find_all('a', href=lambda href: href and 'raajje.mv' in href and '/165' in href)
        
        for element in article_elements:
            href = element['href']
            # Ensure it's a complete URL
            if not href.startswith('http'):
                href = f"https://{href}" if not href.startswith('//') else f"https:{href}"
            
            if href not in links:
                links.append(href)
        
        # Remove duplicates
        return list(set(links))
        
    except Exception as e:
        print(f"Error getting Raajje article links from {url}: {str(e)}")
        return []

# Function to extract article ID from URL
def extract_article_id(url):
    # Pattern like https://raajje.mv/165373
    match = re.search(r'raajje\.mv/(\d+)', url)
    if match:
        return match.group(1)
    
    # Default: use a timestamp-based ID
    return f"raajje_{int(time.time())}"

# Function to scrape by article IDs for Raajje.mv
def scrape_raajje_by_ids(start_id=165000, max_articles=120):
    articles = []
    articles_scraped = 0
    current_id = start_id
    failed_consecutive = 0
    
    while articles_scraped < max_articles and failed_consecutive < 50:  # Stop if too many consecutive failures
        url = f"https://raajje.mv/{current_id}"
        print(f"Trying Raajje article ID: {current_id} ({articles_scraped+1}/{max_articles})")
        
        article_data = scrape_raajje_article(url)
        
        if article_data:
            # Save individual article to JSON
            article_file = f'backend/data/raw/raajjemv/raajje_article_{current_id}.json'
            with open(article_file, 'w', encoding='utf-8') as f:
                json.dump(article_data, f, ensure_ascii=False, indent=4)
            
            articles.append(article_data)
            articles_scraped += 1
            failed_consecutive = 0  # Reset counter on success
            
            # Save progress periodically
            if articles_scraped % 10 == 0:
                print(f"Scraped {articles_scraped} Raajje articles")
        else:
            failed_consecutive += 1
            print(f"Failed to scrape Raajje article ID: {current_id}")
        
        current_id += 1
        time.sleep(random.uniform(2, 5))
    
    print(f"Finished scraping {len(articles)} Raajje articles")
    return articles

# Function to navigate pages and find articles for Raajje.mv
def scrape_raajje_by_navigation(max_articles=120):
    all_articles = []
    articles_scraped = 0
    page_num = 1
    
    # Keep track of URLs we've already scraped
    scraped_urls = set()
    
    # Keep going until we have enough articles or run out of new content
    while articles_scraped < max_articles:
        possible_urls = [
            "https://raajje.mv/",
            f"https://raajje.mv/latest?page={page_num}",
            f"https://raajje.mv/category/news?page={page_num}"
        ]
        
        # Try to find article links from each URL
        found_new_links = False
        
        for base_url in possible_urls:
            print(f"Getting article links from {base_url}")
            article_links = get_raajje_article_links(base_url)
            
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
                print(f"Scraping Raajje article {articles_scraped+1}/{max_articles}: {link}")
                
                article_data = scrape_raajje_article(link)
                
                if article_data:
                    # Extract article ID for filename
                    article_id = extract_article_id(link)
                    
                    # Save individual article to JSON
                    article_file = f'backend/data/raw/raajjemv/raajje_article_{article_id}.json'
                    with open(article_file, 'w', encoding='utf-8') as f:
                        json.dump(article_data, f, ensure_ascii=False, indent=4)
                    
                    all_articles.append(article_data)
                    scraped_urls.add(link)
                    articles_scraped += 1
                    
                    # Save progress periodically
                    if articles_scraped % 10 == 0:
                        print(f"Saved {articles_scraped} Raajje articles")
                    
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
            print("Reached end of available content for Raajje")
            break
    
    print(f"Finished scraping {len(all_articles)} Raajje articles via navigation")
    return all_articles

# Main function to run the complete scraping operation
def main():
    # Method 1: Scrape by article IDs
    print("Starting Raajje.mv scraping by article IDs")
    raajje_articles = scrape_raajje_by_ids(start_id=165000, max_articles=120)
    
    # If we didn't get enough articles, try navigation method
    if len(raajje_articles) < 120:
        print(f"Only scraped {len(raajje_articles)} articles by ID. Trying navigation method.")
        remaining_articles = 120 - len(raajje_articles)
        scrape_raajje_by_navigation(max_articles=remaining_articles)
    
    print(f"Finished scraping operation. Articles saved to 'backend/data/raw/raajjemv' folder.")

if __name__ == "__main__":
    main()