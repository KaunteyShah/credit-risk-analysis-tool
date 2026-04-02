"""
Web Content Scraper - Phase 2 Implementation

Intelligent web scraping for extracting business content from company websites
to enhance SIC classification accuracy through real business intelligence.
"""
import os
import time
import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import re
import urllib.parse
import logging

@dataclass
class ScrapingConfig:
    """Configuration for web scraping"""
    timeout: int = 30
    max_retries: int = 3
    delay_between_requests: float = 1.0
    max_content_length: int = 50000  # Max characters to extract
    user_agent: str = "CreditRiskAnalyzer/2.0 (Business Research)"
    max_pages_per_site: int = 3

class WebContentScraper:
    """
    Intelligent web scraper for extracting business content
    
    Features:
    - Respectful scraping with rate limiting
    - Content quality filtering
    - Business-relevant text extraction
    - Error handling and retries
    """
    
    def __init__(self, config: Optional[ScrapingConfig] = None):
        self.config = config or ScrapingConfig()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.config.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-GB,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = get_logger(__name__)
    
    def scrape_company_website(self, company_name: str, website_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Scrape company website for business intelligence
        
        Args:
            company_name: Name of the company
            website_url: Optional direct website URL
            
        Returns:
            Scraped content and metadata
        """
        try:
            # If no URL provided, try to find it
            if not website_url:
                website_url = self._find_company_website(company_name)
                if not website_url:
                    return {
                        "success": False,
                        "error": "Could not find company website",
                        "company_name": company_name
                    }
            
            # Normalize URL
            website_url = self._normalize_url(website_url)
            
            # Scrape main content
            content_data = self._scrape_website_content(website_url)
            
            if content_data["success"]:
                # Extract business intelligence
                business_intel = self._extract_business_intelligence(content_data["content"])
                
                return {
                    "success": True,
                    "company_name": company_name,
                    "website_url": website_url,
                    "scraped_at": datetime.now().isoformat(),
                    "content": content_data["content"],
                    "business_intelligence": business_intel,
                    "metadata": content_data["metadata"]
                }
            else:
                return {
                    "success": False,
                    "error": content_data["error"],
                    "company_name": company_name,
                    "website_url": website_url
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Scraping failed: {str(e)}",
                "company_name": company_name
            }
    
    def _find_company_website(self, company_name: str) -> Optional[str]:
        """
        Try to find company website using search
        
        Args:
            company_name: Company name to search for
            
        Returns:
            Website URL if found
        """
        try:
            # Simple Google search simulation (in production, use proper search API)
            search_query = f"{company_name} official website"
            
            # For now, return None - would implement actual search in production
            self.logger.info(f"Would search for: {search_query}")
            return None
            
        except Exception as e:
            self.logger.error(f"Website search failed: {e}")
            return None
    
    def _normalize_url(self, url: str) -> str:
        """Normalize and validate URL"""
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Basic URL validation
        parsed = urllib.parse.urlparse(url)
        if not parsed.netloc:
            raise ValueError(f"Invalid URL: {url}")
        
        return url
    
    def _scrape_website_content(self, url: str) -> Dict[str, Any]:
        """
        Scrape content from a website
        
        Args:
            url: Website URL to scrape
            
        Returns:
            Scraped content and metadata
        """
        for attempt in range(self.config.max_retries):
            try:
                time.sleep(self.config.delay_between_requests)
                
                response = self.session.get(url, timeout=self.config.timeout)
                response.raise_for_status()
                
                # Check content type
                content_type = response.headers.get('content-type', '').lower()
                if 'html' not in content_type:
                    return {
                        "success": False,
                        "error": f"Non-HTML content type: {content_type}"
                    }
                
                # Parse HTML
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Extract meaningful content
                extracted_content = self._extract_meaningful_content(soup, url)
                
                return {
                    "success": True,
                    "content": extracted_content,
                    "metadata": {
                        "url": url,
                        "status_code": response.status_code,
                        "content_length": len(response.content),
                        "scraped_at": datetime.now().isoformat(),
                        "attempt": attempt + 1
                    }
                }
                
            except requests.exceptions.Timeout:
                if attempt == self.config.max_retries - 1:
                    return {"success": False, "error": "Request timeout"}
                time.sleep(2 ** attempt)
                
            except requests.exceptions.RequestException as e:
                if attempt == self.config.max_retries - 1:
                    return {"success": False, "error": f"Request failed: {str(e)}"}
                time.sleep(2 ** attempt)
                
            except Exception as e:
                return {"success": False, "error": f"Parsing failed: {str(e)}"}
        
        return {"success": False, "error": "Max retries exceeded"}
    
    def _extract_meaningful_content(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """
        Extract meaningful content from HTML
        
        Args:
            soup: Parsed HTML
            url: Source URL
            
        Returns:
            Extracted content dictionary
        """
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
        
        # Extract title
        title = ""
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.get_text().strip()
        
        # Extract meta description
        meta_description = ""
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            meta_description = meta_desc.get('content', '').strip()
        
        # Extract main content areas
        content_text = []
        
        # Look for main content containers
        main_content_selectors = [
            'main', '[role="main"]', '.main-content', '#main-content',
            '.content', '#content', 'article', '.article'
        ]
        
        main_content = None
        for selector in main_content_selectors:
            main_content = soup.select_one(selector)
            if main_content:
                break
        
        if main_content:
            content_text.append(main_content.get_text(separator=' ', strip=True))
        else:
            # Fallback to body content
            body = soup.find('body')
            if body:
                content_text.append(body.get_text(separator=' ', strip=True))
        
        # Look for specific business-relevant sections
        business_sections = self._extract_business_sections(soup)
        
        # Combine all text
        full_text = ' '.join(content_text).strip()
        
        # Limit content length
        if len(full_text) > self.config.max_content_length:
            full_text = full_text[:self.config.max_content_length] + "..."
        
        # Clean up text
        full_text = re.sub(r'\s+', ' ', full_text)
        
        return {
            "title": title,
            "meta_description": meta_description,
            "main_content": full_text,
            "business_sections": business_sections,
            "word_count": len(full_text.split()),
            "url": url
        }
    
    def _extract_business_sections(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract business-specific content sections"""
        business_sections = {}
        
        # Common business section patterns
        section_patterns = {
            "about": [
                "about", "about-us", "about_us", "company", "who-we-are",
                "our-company", "overview", "profile"
            ],
            "services": [
                "services", "products", "what-we-do", "solutions",
                "offerings", "capabilities"
            ],
            "expertise": [
                "expertise", "specialties", "experience", "skills",
                "competencies", "focus-areas"
            ]
        }
        
        for section_name, patterns in section_patterns.items():
            for pattern in patterns:
                # Look for headers with these patterns
                headers = soup.find_all(['h1', 'h2', 'h3', 'h4'], 
                                      string=re.compile(pattern, re.I))
                
                for header in headers:
                    # Get content after this header
                    content_parts = []
                    next_element = header.find_next_sibling()
                    
                    while next_element and next_element.name not in ['h1', 'h2', 'h3']:
                        if next_element.name in ['p', 'div', 'ul', 'ol']:
                            text = next_element.get_text(separator=' ', strip=True)
                            if text:
                                content_parts.append(text)
                        next_element = next_element.find_next_sibling()
                    
                    if content_parts:
                        business_sections[section_name] = ' '.join(content_parts)
                        break
        
        return business_sections
    
    def _extract_business_intelligence(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract business intelligence from scraped content
        
        Args:
            content: Scraped content dictionary
            
        Returns:
            Business intelligence insights
        """
        main_text = content.get("main_content", "")
        title = content.get("title", "")
        meta_description = content.get("meta_description", "")
        business_sections = content.get("business_sections", {})
        
        # Combine all relevant text for analysis
        analysis_text = f"{title} {meta_description} {main_text}"
        for section_text in business_sections.values():
            analysis_text += f" {section_text}"
        
        # Extract business keywords and activities
        business_keywords = self._extract_business_keywords(analysis_text)
        industry_indicators = self._identify_industry_indicators(analysis_text)
        service_indicators = self._extract_service_indicators(analysis_text)
        
        return {
            "business_keywords": business_keywords,
            "industry_indicators": industry_indicators,
            "service_indicators": service_indicators,
            "content_quality_score": self._calculate_content_quality(content),
            "text_length": len(analysis_text),
            "business_focus": self._determine_business_focus(analysis_text),
            "extracted_at": datetime.now().isoformat()
        }
    
    def _extract_business_keywords(self, text: str) -> List[str]:
        """Extract business-relevant keywords"""
        # Common business activity keywords
        business_keywords = [
            'software', 'development', 'consulting', 'services', 'technology',
            'manufacturing', 'retail', 'wholesale', 'construction', 'engineering',
            'design', 'marketing', 'finance', 'insurance', 'healthcare',
            'education', 'training', 'research', 'management', 'solutions'
        ]
        
        text_lower = text.lower()
        found_keywords = [kw for kw in business_keywords if kw in text_lower]
        
        return found_keywords[:20]  # Limit to top 20
    
    def _identify_industry_indicators(self, text: str) -> List[str]:
        """Identify industry-specific indicators"""
        industry_patterns = {
            'technology': ['software', 'app', 'digital', 'cloud', 'AI', 'data'],
            'construction': ['building', 'construction', 'contractor', 'renovation'],
            'retail': ['shop', 'store', 'retail', 'ecommerce', 'online store'],
            'consulting': ['consulting', 'advisory', 'strategy', 'expertise'],
            'manufacturing': ['manufacturing', 'production', 'factory', 'industrial']
        }
        
        text_lower = text.lower()
        indicators = []
        
        for industry, patterns in industry_patterns.items():
            if any(pattern in text_lower for pattern in patterns):
                indicators.append(industry)
        
        return indicators
    
    def _extract_service_indicators(self, text: str) -> List[str]:
        """Extract service-type indicators"""
        service_patterns = [
            'provide', 'offer', 'deliver', 'specialize', 'expert',
            'solution', 'service', 'support', 'help', 'assist'
        ]
        
        text_lower = text.lower()
        found_services = [pattern for pattern in service_patterns if pattern in text_lower]
        
        return found_services
    
    def _calculate_content_quality(self, content: Dict[str, Any]) -> float:
        """Calculate content quality score (0-1)"""
        score = 0.0
        
        # Title quality
        if content.get("title") and len(content["title"]) > 10:
            score += 0.2
        
        # Meta description quality
        if content.get("meta_description") and len(content["meta_description"]) > 50:
            score += 0.2
        
        # Content length
        word_count = content.get("word_count", 0)
        if word_count > 100:
            score += 0.3
        if word_count > 500:
            score += 0.2
        
        # Business sections
        if content.get("business_sections"):
            score += 0.1
        
        return min(score, 1.0)
    
    def _determine_business_focus(self, text: str) -> str:
        """Determine primary business focus from content"""
        focus_keywords = {
            'Technology': ['software', 'app', 'digital', 'technology', 'IT', 'computer'],
            'Professional Services': ['consulting', 'advisory', 'professional', 'expertise'],
            'Manufacturing': ['manufacturing', 'production', 'industrial', 'factory'],
            'Retail': ['retail', 'shop', 'store', 'ecommerce', 'online'],
            'Construction': ['construction', 'building', 'contractor', 'property'],
            'Healthcare': ['healthcare', 'medical', 'health', 'clinical'],
            'Education': ['education', 'training', 'learning', 'school'],
            'Finance': ['finance', 'financial', 'accounting', 'investment']
        }
        
        text_lower = text.lower()
        focus_scores = {}
        
        for focus, keywords in focus_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                focus_scores[focus] = score
        
        if focus_scores:
            return max(focus_scores, key=focus_scores.get)
        else:
            return 'General Business'

# Mock scraper for development
class MockWebContentScraper:
    """Mock scraper that returns realistic test data"""
    
    def scrape_company_website(self, company_name: str, website_url: Optional[str] = None) -> Dict[str, Any]:
        """Return mock scraped content"""
        return {
            "success": True,
            "company_name": company_name,
            "website_url": website_url or f"https://www.{company_name.lower().replace(' ', '')}.com",
            "scraped_at": datetime.now().isoformat(),
            "content": {
                "title": f"{company_name} - Professional Business Solutions",
                "meta_description": f"{company_name} provides professional business solutions and services.",
                "main_content": f"Welcome to {company_name}. We are a leading provider of business solutions specializing in professional services, technology consulting, and strategic advisory services. Our experienced team delivers high-quality solutions to help businesses grow and succeed in today's competitive market.",
                "business_sections": {
                    "about": f"{company_name} has been serving clients for over 10 years with expertise in business consulting and technology solutions.",
                    "services": "We offer consulting services, software development, and business strategy advisory."
                },
                "word_count": 150,
                "url": website_url or f"https://www.{company_name.lower().replace(' ', '')}.com"
            },
            "business_intelligence": {
                "business_keywords": ["consulting", "services", "technology", "solutions"],
                "industry_indicators": ["technology", "consulting"],
                "service_indicators": ["provide", "offer", "specialize"],
                "content_quality_score": 0.8,
                "text_length": 300,
                "business_focus": "Professional Services",
                "extracted_at": datetime.now().isoformat()
            },
            "metadata": {
                "status_code": 200,
                "content_length": 5000,
                "scraped_at": datetime.now().isoformat(),
                "data_source": "mock_scraper"
            }
        }

# Factory function
def create_web_scraper(use_mock: bool = False) -> WebContentScraper:
    """Create web scraper - real or mock"""
    if use_mock:
        return MockWebContentScraper()
    else:
        return WebContentScraper()

# Example usage
if __name__ == "__main__":
    # Test the scraper
    scraper = create_web_scraper(use_mock=True)
    
    result = scraper.scrape_company_website("Test Company Ltd")
    
    if result["success"]:
        print("Scraping successful:")
        print(f"Business Focus: {result['business_intelligence']['business_focus']}")
        print(f"Keywords: {result['business_intelligence']['business_keywords']}")
        print(f"Content Quality: {result['business_intelligence']['content_quality_score']}")
    else:
        print(f"Scraping failed: {result['error']}")
