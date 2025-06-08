# dialect_middleware.py
import re
import db

class DialectMiddleware:
    def __init__(self):
        # Keywords that indicate dialect-related queries (English only)
        self.dialect_keywords = [
            'dialect', 'dialects', 'male', 'huvadhoo', 'addu', 'translation',
            'translate', 'dhivehi', 'thaana', 'maldivian', 'regional',
            'how do you say', 'what is', 'meaning of', 'family', 'relatives'
        ]
        
        # English family terms that are in our database
        self.english_family_terms = [
            'mother', 'father', 'brother', 'sister', 'son', 'daughter', 
            'grandmother', 'grandfather', 'aunt', 'uncle'
        ]

    def should_handle_request(self, message_content, is_authenticated=False):
        """
        Determine if this request should be handled by dialect middleware
        Only for authenticated users asking in English about dialects specifically
        """
        if not is_authenticated:
            return False
        
        # Check if message contains non-Latin characters (likely not English)
        if self._contains_non_latin_chars(message_content):
            return False
            
        message_lower = message_content.lower()
        
        # More specific dialect-related patterns
        dialect_patterns = [
            r"how (?:do you|to) say .+ in .+dialect",
            r"how (?:do you|to) say .+ in (male|huvadhoo|addu)",
            r"what is .+ in .+dialect",
            r"what is .+ in (male|huvadhoo|addu)",
            r"translate .+ to (male|huvadhoo|addu)",
            r".+ in (male|huvadhoo|addu) dialect",
            r"maldivian dialect",
            r"dhivehi dialect",
            r"regional dialect"
        ]
        
        # Check for specific dialect query patterns
        for pattern in dialect_patterns:
            if re.search(pattern, message_lower):
                return True
        
        # Check if asking about family terms AND mentioning dialects/translation
        has_family_term = any(term in message_lower for term in self.english_family_terms)
        has_dialect_context = any(keyword in message_lower for keyword in ['dialect', 'translate', 'huvadhoo', 'addu', 'male', 'maldivian', 'dhivehi'])
        
        if has_family_term and has_dialect_context:
            return True
                
        return False

    def _contains_non_latin_chars(self, text):
        """
        Check if text contains non-Latin characters (like Dhivehi/Thaana)
        """
        # Check for common non-Latin character ranges
        for char in text:
            # Thaana script range (U+0780 to U+07BF)
            if '\u0780' <= char <= '\u07BF':
                return True
            # Arabic script range (often used with Dhivehi)
            if '\u0600' <= char <= '\u06FF':
                return True
            # Other non-Latin ranges can be added here if needed
        return False

    def extract_search_term(self, message_content):
        """
        Extract the term user is asking about from their message
        """
        message_lower = message_content.lower()
        
        # Patterns to extract search terms
        patterns = [
            r"translate ['\"]?([^'\"?]+)['\"]? to dialects",
            r"['\"]?([^'\"?]+)['\"]? in male dialect",
            r"['\"]?([^'\"?]+)['\"]? in huvadhoo",
            r"['\"]?([^'\"?]+)['\"]? in addu"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message_lower)
            if match:
                extracted = match.group(1).strip()
                # Clean up common words that might be captured
                cleaned = re.sub(r'\b(the|a|an)\b', '', extracted).strip()
                return cleaned if cleaned else extracted
        
        # If no pattern matches, try to find known English family terms
        words = message_lower.split()
        for word in words:
            if word in self.english_family_terms:
                return word
                
        return None

    def search_dialects(self, search_term):
        """
        Search for dialect information in the database
        """
        if not search_term:
            return None
            
        # First try exact English match
        result = db.get_dialect_by_english_term(search_term)
        if result:
            return result
            
        # Try partial match
        results = db.search_dialects(search_term)
        return results

    def format_dialect_response(self, dialect_data, search_term=None):
        """
        Format the dialect data into a user-friendly response
        """
        if not dialect_data:
            available_terms = ", ".join(self.english_family_terms)
            return f"I couldn't find dialect information for that word. Please ask about family terms in English like: {available_terms}"
        
        # Handle single result
        if isinstance(dialect_data, dict):
            return self._format_single_dialect(dialect_data)
        
        # Handle multiple results
        if isinstance(dialect_data, list):
            if len(dialect_data) == 1:
                return self._format_single_dialect(dialect_data[0])
            else:
                return self._format_multiple_dialects(dialect_data, search_term)
                
        return "Unable to format dialect information."

    def _format_single_dialect(self, dialect):
        """Format a single dialect entry"""
        response = f"**{dialect['eng_term']}** in Maldivian dialects:\n\n"
        response += f"**Malé**: {dialect['male_term']}\n"
        response += f"**Huvadhoo**: {dialect['huvadhoo_term']}\n"
        response += f"**Addu**: {dialect['addu_term']}\n\n"
        response += "These are the regional variations of this word across different atolls in the Maldives."
        return response

    def _format_multiple_dialects(self, dialects, search_term):
        """Format multiple dialect entries"""
        response = f"I found {len(dialects)} dialect entries related to '{search_term}':\n\n"
        
        for i, dialect in enumerate(dialects[:5], 1):  # Limit to 5 results
            response += f"**{i}. {dialect['eng_term']}**\n"
            response += f"   Malé: {dialect['male_term']} | "
            response += f"Huvadhoo: {dialect['huvadhoo_term']} | "
            response += f"Addu: {dialect['addu_term']}\n\n"
            
        if len(dialects) > 5:
            response += f"... and {len(dialects) - 5} more results. Please be more specific for better results."
            
        return response

    def process_dialect_request(self, message_content, is_authenticated=False):
        """
        Main method to process dialect requests
        Returns None if request should go to Gemini, otherwise returns dialect response
        """
        if not self.should_handle_request(message_content, is_authenticated):
            return None
            
        search_term = self.extract_search_term(message_content)
        dialect_data = self.search_dialects(search_term)
        
        return self.format_dialect_response(dialect_data, search_term)