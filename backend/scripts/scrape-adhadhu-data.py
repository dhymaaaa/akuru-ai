import requests
from bs4 import BeautifulSoup
import time
import random
import os
import re
import json

# Create folder if it doesn't exist
if not os.path.exists('backend/data/raw/adhadhu'):
    os.makedirs('backend/data/raw/adhadhu')

# Function to scrape an Adhadhu article
def scrape_adhadhu_article(url):
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
        
        # Extract article title - based on the updated HTML structure
        # From the new image, title appears to be in p tags with class="font-faseyha font-19 color-black text-right mb-4"
        title = soup.find('p', class_='font-faseyha')
        title_text = title.text.strip() if title else "No title found"
        
        # Extract article image URL
        # From the new image, images have class="img-fluid w-100 h-100"
        image = soup.find('img', class_='img-fluid')
        if not image:
            image = soup.find('img', style='object-fit: cover;')
        image_url = image['src'] if image and 'src' in image.attrs else ""
        
        # Extract date - looking for date information
        # Date doesn't appear directly in the image but might be in metadata or other elements
        date_element = soup.find('meta', property='article:published_time') or soup.find('time')
        date_text = date_element['content'].strip() if date_element and 'content' in date_element.attrs else "No date found"
        
        # Extract article content - look for article text content
        content_paragraphs = []
        
        # From the updated image, content appears to be in p tags with class="font-faseyha font-19 color-black text-right mb-4"
        article_paragraphs = soup.find_all('p', class_='font-faseyha')
        
        if article_paragraphs:
            for p in article_paragraphs:
                if p.text.strip() and len(p.text.strip()) > 10:  # Lower threshold to catch shorter paragraphs
                    content_paragraphs.append(p.text.strip())
        else:
            # Try alternate approach to find content
            article_container = soup.find('article') or soup.find('div', class_='item')
            if article_container:
                paragraphs = article_container.find_all('p')
                for p in paragraphs:
                    if p.text.strip() and len(p.text.strip()) > 20:
                        content_paragraphs.append(p.text.strip())
        
        # Join paragraphs with double newlines
        content_text = "\n\n".join(content_paragraphs)
        
        # Check if we actually found content 
        if not content_text or len(content_text) < 100:  
            print(f"No substantial content found in {url}")
            return None
        
        # Extract category if available
        category_element = soup.find('div', class_='category-news')
        category = category_element.text.strip() if category_element else ""
        
        return {
            'url': url,
            'title': title_text,
            'date': date_text,
            'content': content_text
        }
        
    except Exception as e:
        print(f"Error scraping {url}: {str(e)}")
        return None

# Function to get article links from Adhadhu
def get_adhadhu_article_links(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        links = []
        # From the image, we can see links like "/article/67570", "/article/67567", "/article/67572"
        # Look for anchor tags with href containing '/article/'
        article_elements = soup.find_all('a', class_='item', href=lambda href: href and '/article/' in href)
        
        for element in article_elements:
            href = element['href']
            # Ensure it's a complete URL
            if href.startswith('/'):
                href = f"https://adhadhu.com{href}"
            elif not href.startswith('http'):
                href = f"https://adhadhu.com/{href}"
            
            if href not in links:
                links.append(href)
        
        # Remove duplicates
        return list(set(links))
        
    except Exception as e:
        print(f"Error getting Adhadhu article links from {url}: {str(e)}")
        return []

# Function to extract article ID from URL
def extract_article_id(url):
    # Pattern like /article/67570 or /article/67567
    match = re.search(r'/article/(\d+)', url)
    if match:
        return match.group(1)
    
    # Default: use a timestamp-based ID
    return f"adhadhu_{int(time.time())}"

# Function to scrape by article IDs for Adhadhu
def scrape_adhadhu_by_ids(start_id=67000, max_articles=117):
    articles = []
    articles_scraped = 0
    current_id = start_id
    failed_consecutive = 0
    
    while articles_scraped < max_articles and failed_consecutive < 50:  # Stop if too many consecutive failures
        url = f"https://adhadhu.com/article/{current_id}"
        print(f"Trying Adhadhu article ID: {current_id} ({articles_scraped+1}/{max_articles})")
        
        article_data = scrape_adhadhu_article(url)
        
        if article_data:
            # Save individual article to JSON
            article_file = f'backend/data/raw/adhadhu/adhadhu_article_{current_id}.json'
            with open(article_file, 'w', encoding='utf-8') as f:
                json.dump(article_data, f, ensure_ascii=False, indent=4)
            
            articles.append(article_data)
            articles_scraped += 1
            failed_consecutive = 0  # Reset counter on success
            
            # Save progress periodically
            if articles_scraped % 10 == 0:
                print(f"Scraped {articles_scraped} Adhadhu articles")
        else:
            failed_consecutive += 1
            print(f"Failed to scrape Adhadhu article ID: {current_id}")
        
        current_id += 1
        time.sleep(random.uniform(2, 5))
    
    print(f"Finished scraping {len(articles)} Adhadhu articles")
    return articles

# Function to navigate pages and find articles for Adhadhu
def scrape_adhadhu_by_navigation(max_articles=117):
    all_articles = []
    articles_scraped = 0
    page_num = 1
    
    # Keep track of URLs we've already scraped
    scraped_urls = set()
    
    # Keep going until we have enough articles or run out of new content
    while articles_scraped < max_articles:
        possible_urls = [
            "https://adhadhu.com/",
            f"https://adhadhu.com/category/news?page={page_num}",
            f"https://adhadhu.com/latest?page={page_num}"
        ]
        
        # Try to find article links from each URL
        found_new_links = False
        
        for base_url in possible_urls:
            print(f"Getting article links from {base_url}")
            article_links = get_adhadhu_article_links(base_url)
            
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
                print(f"Scraping Adhadhu article {articles_scraped+1}/{max_articles}: {link}")
                
                article_data = scrape_adhadhu_article(link)
                
                if article_data:
                    # Extract article ID for filename
                    article_id = extract_article_id(link)
                    
                    # Save individual article to JSON
                    article_file = f'backend/data/raw/adhadhu/adhadhu_article_{article_id}.json'
                    with open(article_file, 'w', encoding='utf-8') as f:
                        json.dump(article_data, f, ensure_ascii=False, indent=4)
                    
                    all_articles.append(article_data)
                    scraped_urls.add(link)
                    articles_scraped += 1
                    
                    # Save progress periodically
                    if articles_scraped % 10 == 0:
                        print(f"Saved {articles_scraped} Adhadhu articles")
                    
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
            print("Reached end of available content for Adhadhu")
            break
    
    print(f"Finished scraping {len(all_articles)} Adhadhu articles via navigation")
    return all_articles

# Main function to run the complete scraping operation
def main():
    # Method 1: Scrape by article IDs
    print("Starting Adhadhu scraping by article IDs")
    adhadhu_articles = scrape_adhadhu_by_ids(start_id=67000, max_articles=117)
    
    # If we didn't get enough articles, try navigation method
    if len(adhadhu_articles) < 117:
        print(f"Only scraped {len(adhadhu_articles)} articles by ID. Trying navigation method.")
        remaining_articles = 117 - len(adhadhu_articles)
        scrape_adhadhu_by_navigation(max_articles=remaining_articles)
    
    print(f"Finished scraping operation. Articles saved to 'backend/data/raw/adhadhu' folder.")

if __name__ == "__main__":
    main()