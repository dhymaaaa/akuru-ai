import re
import db

class DialectMiddleware:
    def __init__(self):
        # Keywords that indicate dialect-related queries (English only)
        self.dialect_keywords = [
            'dialect', 'dialects', 'male', 'huvadhoo', 'addu', 'translation', 'regional'
        ]
        
        # English family terms that are in our database
        self.english_family_terms = [
            'mother', 'father', 'brother', 'sister', 'son', 'daughter', 
            'grandmother', 'grandfather', 'aunt', 'uncle'
        ]

    def should_handle_request(self, message_content, is_authenticated=False):
        """
        Determine if this request should be handled by dialect middleware
        For authenticated users: handle the request normally
        For guest users: detect dialect queries but don't process them
        """
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

    def determine_display_format(self, user_query):
        """Determine display format based on user query patterns"""
        patterns = [
            (r"translate ['\"]?([^'\"?]+)['\"]? to dialects", 'all'),
            (r"['\"]?([^'\"?]+)['\"]? in male dialect", 'male'),
            (r"['\"]?([^'\"?]+)['\"]? in huvadhoo", 'huvadhoo'),
            (r"['\"]?([^'\"?]+)['\"]? in addu", 'addu')
        ]
        
        for pattern, format_type in patterns:
            match = re.search(pattern, user_query, re.IGNORECASE)
            if match:
                search_term = match.group(1).strip()
                # Clean up common words that might be captured
                cleaned = re.sub(r'\b(the|a|an)\b', '', search_term).strip()
                return (cleaned if cleaned else search_term), format_type
        
        return None, 'auto'

    def extract_search_term(self, message_content):
        """
        Extract the term user is asking about from their message
        """
        # First try the pattern-based extraction
        search_term, _ = self.determine_display_format(message_content)
        if search_term:
            return search_term
            
        # Fallback to original logic
        message_lower = message_content.lower()
        
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

    def _format_dialect_term(self, dhivehi_term, transliteration):
        """Helper method to format Dhivehi term with transliteration"""
        if transliteration:
            return f"{dhivehi_term} ({transliteration})"
        return dhivehi_term

    def format_single_dialect_only(self, dialect, dialect_name):
        """Format showing only one specific dialect"""
        dialect_map = {
            'male': ('Malé', dialect['male_term'], dialect.get('male_transliteration')),
            'huvadhoo': ('Huvadhoo', dialect['huvadhoo_term'], dialect.get('huvadhoo_transliteration')),
            'addu': ('Addu', dialect['addu_term'], dialect.get('addu_transliteration'))
        }
        
        display_name, term, transliteration = dialect_map[dialect_name]
        formatted_term = self._format_dialect_term(term, transliteration)
        return f"**{dialect['eng_term']}** in {display_name} dialect: {formatted_term}"

    def format_multiple_dialects_single_column(self, dialects, search_term, dialect_name):
        """Format multiple results showing only one dialect column"""
        dialect_map = {
            'male': ('Malé', 'male_term', 'male_transliteration'),
            'huvadhoo': ('Huvadhoo', 'huvadhoo_term', 'huvadhoo_transliteration'),
            'addu': ('Addu', 'addu_term', 'addu_transliteration')
        }
        
        display_name, term_key, trans_key = dialect_map[dialect_name]
        response = f"There are {len(dialects)} ways to say '{search_term}' in {display_name} dialect:\n\n"
        
        for i, dialect in enumerate(dialects[:5], 1):
            dhivehi_term = dialect[term_key]
            transliteration = dialect.get(trans_key)
            formatted_term = self._format_dialect_term(dhivehi_term, transliteration)
            response += f"**{i}. {dialect['eng_term']}**: {formatted_term}\n"
        
        if len(dialects) > 5:
            response += f"\n... and {len(dialects) - 5} more results."
        
        return response

    def format_dialect_response(self, dialect_data, search_term=None, format_type='auto'):
        """
        Format the dialect data into a user-friendly response
        """
        if not dialect_data:
            available_terms = ", ".join(self.english_family_terms)
            return f"I couldn't find dialect information for that word. Please ask about family terms in English like: {available_terms}"
        
        # Handle single result
        if isinstance(dialect_data, dict):
            if format_type == 'all' or format_type == 'auto':
                return self._format_single_dialect(dialect_data)
            elif format_type in ['male', 'huvadhoo', 'addu']:
                return self.format_single_dialect_only(dialect_data, format_type)
        
        # Handle multiple results
        if isinstance(dialect_data, list):
            if len(dialect_data) == 1:
                dialect = dialect_data[0]
                if format_type == 'all' or format_type == 'auto':
                    return self._format_single_dialect(dialect)
                elif format_type in ['male', 'huvadhoo', 'addu']:
                    return self.format_single_dialect_only(dialect, format_type)
            else:
                if format_type == 'all' or format_type == 'auto':
                    return self._format_multiple_dialects(dialect_data, search_term)
                elif format_type in ['male', 'huvadhoo', 'addu']:
                    return self.format_multiple_dialects_single_column(dialect_data, search_term, format_type)
                
        return "Unable to format dialect information."

    def _format_single_dialect(self, dialect):
        """Format a single dialect entry with transliterations"""
        response = f"**{dialect['eng_term']}** in Maldivian dialects:\n\n"
        
        # Format each dialect with transliteration
        male_formatted = self._format_dialect_term(
            dialect['male_term'], 
            dialect.get('male_transliteration')
        )
        huvadhoo_formatted = self._format_dialect_term(
            dialect['huvadhoo_term'], 
            dialect.get('huvadhoo_transliteration')
        )
        addu_formatted = self._format_dialect_term(
            dialect['addu_term'], 
            dialect.get('addu_transliteration')
        )
        
        response += f"**Malé**: {male_formatted}\n"
        response += f"**Huvadhoo**: {huvadhoo_formatted}\n"
        response += f"**Addu**: {addu_formatted}\n\n"
        response += "These are the regional variations of this word across different dialects in the Maldives."
        return response

    def _format_multiple_dialects(self, dialects, search_term):
        """Format multiple dialect entries with transliterations"""
        response = f"I found {len(dialects)} dialect entries related to '{search_term}':\n\n"
        
        for i, dialect in enumerate(dialects[:5], 1):  # Limit to 5 results
            response += f"**{i}. {dialect['eng_term']}**\n"
            
            # Format each dialect with transliteration
            male_formatted = self._format_dialect_term(
                dialect['male_term'], 
                dialect.get('male_transliteration')
            )
            huvadhoo_formatted = self._format_dialect_term(
                dialect['huvadhoo_term'], 
                dialect.get('huvadhoo_transliteration')
            )
            addu_formatted = self._format_dialect_term(
                dialect['addu_term'], 
                dialect.get('addu_transliteration')
            )
            
            response += f"Malé: {male_formatted} | "
            response += f"Huvadhoo: {huvadhoo_formatted} | "
            response += f"Addu: {addu_formatted}\n\n"
            
        if len(dialects) > 5:
            response += f"... and {len(dialects) - 5} more results. Please be more specific for better results."
            
        return response

    def process_dialect_request(self, message_content, is_authenticated=False):
        """
        Main method to process dialect requests
        For authenticated users: Returns dialect response or None
        For guest users: Returns True if dialect detected, None otherwise
        """
        # First check if this looks like a dialect query
        is_dialect_query = self.should_handle_request(message_content, is_authenticated=True)  # Always check for dialect patterns
        
        if not is_dialect_query:
            return None
        
        # If it's a dialect query but user is not authenticated, return True to indicate detection
        if not is_authenticated:
            return True
        
        # For authenticated users, process the dialect request normally
        # Determine search term and format type from user query
        search_term, format_type = self.determine_display_format(message_content)
        
        # If no specific pattern matched, fall back to original extraction
        if not search_term:
            search_term = self.extract_search_term(message_content)
            format_type = 'auto'
        
        # Search for dialect data
        dialect_data = self.search_dialects(search_term)
        
        # Format and return response
        return self.format_dialect_response(dialect_data, search_term, format_type)