#!/usr/bin/env python3
"""
StreetEasy Apartment Monitor
Checks for new listings every 5 minutes and sends email alerts
"""

import requests
from bs4 import BeautifulSoup
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time
import random
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration
STREETEASY_URL = "https://streeteasy.com/for-rent/nyc/price:-4700%7Carea:102,119,136,141%7Cbeds%3E=2?sort_by=listed_desc"
SEEN_LISTINGS_FILE = "seen_listings.json"

# Email configuration (set these as environment variables)
EMAIL_FROM = os.getenv('EMAIL_FROM')  # Your Gmail address
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')  # Gmail app password
EMAIL_TO = os.getenv('EMAIL_TO')  # Where to send alerts

def load_seen_listings():
    """Load previously seen listing IDs from file"""
    try:
        with open(SEEN_LISTINGS_FILE, 'r') as f:
            return set(json.load(f))
    except FileNotFoundError:
        return set()

def save_seen_listings(seen_listings):
    """Save seen listing IDs to file"""
    with open(SEEN_LISTINGS_FILE, 'w') as f:
        json.dump(list(seen_listings), f)

def get_user_agent():
    """Return a realistic user agent"""
    agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0'
    ]
    return random.choice(agents)

def scrape_listings():
    """Scrape current listings from StreetEasy"""
    headers = {
        'User-Agent': get_user_agent(),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Ch-Ua': '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"macOS"',
        'Cache-Control': 'max-age=0',
    }
    
    try:
        print(f"[{datetime.now()}] Checking StreetEasy for new listings...")
        
        # Add a small delay to seem more human
        time.sleep(random.uniform(1, 3))
        
        # Use a session for better cookie handling
        session = requests.Session()
        response = session.get(STREETEASY_URL, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find listing containers using StreetEasy's current class names
        listings = []
        
        # Look for the specific StreetEasy listing cards
        listing_elements = soup.find_all('div', {'data-testid': 'listing-card'})
        
        if not listing_elements:
            # Fallback: look for ListingCard containers
            listing_elements = soup.find_all('div', class_=lambda x: x and 'ListingCard-module__cardContainer' in str(x))
        
        print(f"Found {len(listing_elements)} listing card elements")
        
        for element in listing_elements[:20]:  # Limit to first 20 to avoid overload
            try:
                # Skip featured and sponsored listings to avoid false positives
                featured_tag = element.find('span', {'data-testid': 'tag-text'}, string='Featured')
                sponsored_tag = element.find('p', class_=lambda x: x and 'ImageContainerFooter-module__sponsoredTag' in str(x))
                
                if featured_tag:
                    print(f"Skipping featured listing")
                    continue
                    
                if sponsored_tag:
                    print(f"Skipping sponsored listing")
                    continue
                
                # Extract listing URL from the address link
                address_link = element.find('a', class_=lambda x: x and 'ListingDescription-module__addressTextAction' in str(x))
                if not address_link:
                    # Fallback: look for any building link
                    address_link = element.find('a', href=lambda x: x and '/building/' in str(x))
                
                if not address_link:
                    continue
                    
                listing_url = address_link.get('href')
                if not listing_url.startswith('http'):
                    listing_url = 'https://streeteasy.com' + listing_url
                
                # Extract listing ID from URL 
                # Format: https://streeteasy.com/building/51-1-avenue-new_york/9
                url_parts = listing_url.split('/')
                listing_id = url_parts[-1] if url_parts else listing_url
                
                # Extract price
                price_elem = element.find('span', class_=lambda x: x and 'PriceInfo-module__price' in str(x))
                price_text = price_elem.get_text().strip() if price_elem else "Price not found"
                
                # Extract address from the link text
                address_text = address_link.get_text().strip() if address_link else "Address not found"
                
                # Extract neighborhood/title
                title_elem = element.find('p', class_=lambda x: x and 'ListingDescription-module__title' in str(x))
                title_text = title_elem.get_text().strip() if title_elem else address_text
                
                # Extract bed/bath info
                beds_baths = []
                bed_bath_items = element.find_all('span', class_=lambda x: x and 'BedsBathsSqft-module__text' in str(x))
                for item in bed_bath_items:
                    beds_baths.append(item.get_text().strip())
                
                beds_baths_text = " • ".join(beds_baths) if beds_baths else ""
                
                # Combine title with bed/bath info
                full_title = f"{title_text} - {beds_baths_text}" if beds_baths_text else title_text
                
                listings.append({
                    'id': listing_id,
                    'url': listing_url,
                    'title': full_title,
                    'price': price_text,
                    'address': address_text
                })
                
            except Exception as e:
                print(f"Error parsing listing element: {e}")
                continue
        
        print(f"Found {len(listings)} listings")
        return listings
        
    except requests.RequestException as e:
        print(f"Error fetching listings: {e}")
        return []

def send_email(new_listings):
    """Send email notification for new listings"""
    if not EMAIL_FROM or not EMAIL_PASSWORD or not EMAIL_TO:
        print("Email credentials not configured. Skipping email notification.")
        return
    
    # Handle multiple email recipients
    email_list = [email.strip() for email in EMAIL_TO.replace(';', ',').split(',')]
    
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_FROM
        msg['To'] = ', '.join(email_list)
        msg['Subject'] = f"🏠 {len(new_listings)} New StreetEasy Listing(s) Found!"
        
        body = "New apartments matching your criteria:\n\n"
        
        for listing in new_listings:
            body += f"📍 {listing['title']}\n"
            body += f"💰 {listing['price']}\n"
            body += f"📍 {listing['address']}\n"
            body += f"🔗 {listing['url']}\n"
            body += "-" * 50 + "\n\n"
        
        body += f"\nFound at: {datetime.now()}"
        body += f"\nSearch URL: {STREETEASY_URL}"
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Connect to Gmail SMTP
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_FROM, EMAIL_PASSWORD)
        
        # Send to all recipients
        server.send_message(msg, to_addrs=email_list)
        server.quit()
        
        print(f"✅ Email sent successfully to {len(email_list)} recipient(s): {', '.join(email_list)}")
        
    except Exception as e:
        print(f"❌ Error sending email: {e}")

def main():
    """Main function"""
    print("🏠 StreetEasy Monitor Starting...")
    print(f"Monitoring: {STREETEASY_URL}")
    
    seen_listings = load_seen_listings()
    print(f"Previously seen listings: {len(seen_listings)}")
    
    # Scrape current listings
    current_listings = scrape_listings()
    
    if not current_listings:
        print("⚠️  No listings found. Check if the scraper needs updating.")
        return
    
    # Find new listings
    new_listings = []
    current_ids = set()
    
    for listing in current_listings:
        current_ids.add(listing['id'])
        if listing['id'] not in seen_listings:
            new_listings.append(listing)
    
    # Update seen listings
    seen_listings.update(current_ids)
    save_seen_listings(seen_listings)
    
    # Send notifications for new listings
    if new_listings:
        print(f"🎉 Found {len(new_listings)} new listing(s)!")
        for listing in new_listings:
            print(f"  • {listing['title']} - {listing['price']}")
        
        send_email(new_listings)
    else:
        print("📭 No new listings found.")
    
    print(f"✅ Check completed at {datetime.now()}")

if __name__ == "__main__":
    main()