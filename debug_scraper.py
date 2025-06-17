#!/usr/bin/env python3
"""
Debug version to see what StreetEasy returns
"""

import requests
from bs4 import BeautifulSoup
import random

STREETEASY_URL = "https://streeteasy.com/for-rent/nyc/price:-4700%7Carea:102,119,136,141%7Cbeds%3E=2"

def get_user_agent():
    """Return a realistic user agent"""
    agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0'
    ]
    return random.choice(agents)

def debug_scrape():
    """Debug what we're getting from StreetEasy"""
    headers = {
        'User-Agent': get_user_agent(),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    print(f"🔍 Fetching: {STREETEASY_URL}")
    print(f"📱 User-Agent: {headers['User-Agent']}")
    
    try:
        response = requests.get(STREETEASY_URL, headers=headers, timeout=30)
        print(f"📊 Status Code: {response.status_code}")
        print(f"📏 Content Length: {len(response.content)} bytes")
        
        if response.status_code != 200:
            print(f"❌ Bad status code: {response.status_code}")
            print(f"📄 Response text (first 500 chars):")
            print(response.text[:500])
            return
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Check if we're getting a real page or a block/redirect
        title = soup.find('title')
        print(f"📰 Page Title: {title.get_text() if title else 'No title found'}")
        
        # Look for any obvious blocking messages
        body_text = soup.get_text().lower()
        blocking_keywords = ['blocked', 'robot', 'captcha', 'verification', 'access denied', 'forbidden']
        for keyword in blocking_keywords:
            if keyword in body_text:
                print(f"🚫 Possible blocking detected: '{keyword}' found in page")
        
        # Save the HTML for inspection
        with open('debug_page.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        print("💾 Saved full HTML to 'debug_page.html' for inspection")
        
        # Try to find listing elements with various selectors
        potential_selectors = [
            '[data-testid="listing-card"]',
            '[class*="ListingCard-module__cardContainer"]',
            'article',
            '[class*="listing"]',
            '[class*="card"]',
            '[class*="item"]',
            '[data-gtm*="listing"]',
            'a[href*="/building/"]',
            '[class*="search-result"]'
        ]
        
        print("\n🔍 Searching for listing elements:")
        for selector in potential_selectors:
            elements = soup.select(selector)
            print(f"  {selector}: {len(elements)} elements")
            if elements and len(elements) > 0:
                # Show some attributes of the first element
                first_elem = elements[0]
                classes = first_elem.get('class', [])
                print(f"    First element classes: {classes}")
        
        # Test the actual parsing logic
        print("\n🏠 Testing actual listing extraction:")
        listing_elements = soup.find_all('div', {'data-testid': 'listing-card'})
        
        if not listing_elements:
            listing_elements = soup.find_all('div', class_=lambda x: x and 'ListingCard-module__cardContainer' in str(x))
        
        print(f"Found {len(listing_elements)} listing card elements")
        
        if listing_elements:
            print("\n📋 Testing first listing extraction:")
            element = listing_elements[0]
            
            # Test address link extraction
            address_link = element.find('a', class_=lambda x: x and 'ListingDescription-module__addressTextAction' in str(x))
            if address_link:
                print(f"  ✅ Address link: {address_link.get('href')}")
                print(f"  ✅ Address text: {address_link.get_text().strip()}")
            else:
                print("  ❌ No address link found")
            
            # Test price extraction
            price_elem = element.find('span', class_=lambda x: x and 'PriceInfo-module__price' in str(x))
            if price_elem:
                print(f"  ✅ Price: {price_elem.get_text().strip()}")
            else:
                print("  ❌ No price found")
            
            # Test title extraction
            title_elem = element.find('p', class_=lambda x: x and 'ListingDescription-module__title' in str(x))
            if title_elem:
                print(f"  ✅ Title: {title_elem.get_text().strip()}")
            else:
                print("  ❌ No title found")
            
            # Test bed/bath extraction
            bed_bath_items = element.find_all('span', class_=lambda x: x and 'BedsBathsSqft-module__text' in str(x))
            if bed_bath_items:
                bed_bath_texts = [item.get_text().strip() for item in bed_bath_items]
                print(f"  ✅ Bed/Bath info: {bed_bath_texts}")
            else:
                print("  ❌ No bed/bath info found")
        
        if rental_links:
            print("📋 First few rental links:")
            for i, link in enumerate(rental_links[:5]):
                href = link.get('href')
                text = link.get_text().strip()[:50]
                print(f"  {i+1}. {href} - {text}")
        
        # Look for building links specifically
        building_links = soup.find_all('a', href=lambda x: x and '/building/' in x)
        print(f"\n🏠 Found {len(building_links)} links with '/building/' in href")
        
        if building_links:
            print("📋 First few building links:")
            for i, link in enumerate(building_links[:5]):
                href = link.get('href')
                text = link.get_text().strip()[:50]
                print(f"  {i+1}. {href} - {text}")
        
        if rental_links:
            print("📋 First few rental links:")
            for i, link in enumerate(rental_links[:5]):
                href = link.get('href')
                text = link.get_text().strip()[:50]
                print(f"  {i+1}. {href} - {text}")
        
        # Check for pagination or "no results" messages
        no_results = soup.find(string=lambda x: x and 'no' in x.lower() and ('result' in x.lower() or 'listing' in x.lower()))
        if no_results:
            print(f"🔍 Possible 'no results' message: {no_results.strip()}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_scrape()