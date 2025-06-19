import re
from dhivehi_nlp import dictionary

class DictionaryMiddleware:
    def __init__(self):
        # Keywords that indicate dictionary-related queries
        self.dictionary_keywords = [
            'meaning', 'definition', 'define', 'translate', 'dictionary'
        ]

    def should_handle_request(self, message_content, is_authenticated=False):
        """
        Determine if this request should be handled by dictionary middleware
        """
        message_lower = message_content.lower()
        
        # Exclude dialect-related queries first
        dialect_indicators = [
            'dialect', 'dialects', 'male', 'huvadhoo', 'addu', 
            'to dialects', 'in dialect', 'regional'
        ]
        
        # If it contains dialect indicators, don't handle with dictionary
        if any(indicator in message_lower for indicator in dialect_indicators):
            return False
        
        # Dictionary-related patterns - made more specific
        dictionary_patterns = [
            r"what (?:does|is) (.+?) mean(?:\?|$)",      # "what does X mean?" - must end with "mean"
            r"meaning of (.+?)(?:\?|$)",                  # "meaning of X"
            r"define (.+?)(?:\?|$)",                      # "define X"
            r"definition of (.+?)(?:\?|$)",               # "definition of X"
            r"(.+?) meaning(?:\?|$)",                     # "X meaning"
            r"what does (.+?) mean(?:\?|$)",              # "what does X mean?"
        ]
        
        # Check for specific dictionary query patterns first
        for pattern in dictionary_patterns:
            if re.search(pattern, message_lower):
                return True
        
        # More specific keyword checking - avoid false positives
        # Only trigger on isolated dictionary keywords, not as part of other queries
        for keyword in self.dictionary_keywords:
            # Use word boundaries to avoid partial matches
            if re.search(r'\b' + re.escape(keyword) + r'\b', message_lower):
                # Additional checks to avoid false positives
                if any(exclusion in message_lower for exclusion in [
                    'dhivehi word for', 'in dhivehi', 'to dialects', 'in dialect',
                    'translate', 'translation to', 'how to say'
                ]):
                    continue
                return True
                
        return False

    def extract_search_term(self, message_content):
        """
        Extract the word user is asking about from their message
        """
        message_lower = message_content.lower()
        
        # Dictionary lookup patterns
        dictionary_patterns = [
            r"what (?:does|is) (.+?) mean(?:\?|$)",  # "what does X mean" - must end with "mean"
            r"meaning of (.+?)(?:\?|$)",     # "meaning of X"
            r"define (.+?)(?:\?|$)",         # "define X"
            r"definition of (.+?)(?:\?|$)",  # "definition of X"
            r"(.+?) meaning(?:\?|$)",        # "X meaning"
        ]
        
        for pattern in dictionary_patterns:
            match = re.search(pattern, message_lower)
            if match:
                search_term = match.group(1).strip()
                # Clean up common words that might be captured
                cleaned = re.sub(r'\b(the|a|an|this|that)\b', '', search_term).strip()
                return cleaned if cleaned else search_term
        
        # If no pattern matches, check if it's a simple single word
        words = message_content.split()
        if len(words) == 1:
            return words[0].strip()
                
        return None

    def search_dictionary(self, search_term):
        """
        Search for word definition in the dictionary
        """
        if not search_term:
            return None
            
        try:
            # Try to get definition from dhivehi_nlp dictionary
            definition = dictionary.get_definition(search_term)
            if definition:
                return {
                    'word': search_term,
                    'definition': definition,
                    'found': True
                }
        except Exception as e:
            print(f"Error searching dictionary for '{search_term}': {str(e)}")
        
        # If not found, try to get similar words
        try:
            word_list = dictionary.get_word_list()
            similar_words = []
            search_lower = search_term.lower()
            
            # Find words that contain the search term or vice versa
            for word in word_list:
                if search_lower in word.lower() or word.lower() in search_lower:
                    similar_words.append(word)
                    if len(similar_words) >= 5:  # Limit to 5 suggestions
                        break
            
            return {
                'word': search_term,
                'definition': None,
                'found': False,
                'similar_words': similar_words
            }
        except Exception as e:
            print(f"Error getting similar words: {str(e)}")
            return None

    def format_dictionary_response(self, dictionary_data):
        """
        Format the dictionary data into a user-friendly response
        """
        if not dictionary_data:
            return "I couldn't find that word in the dictionary. Please check the spelling and try again."
        
        word = dictionary_data.get('word', '')
        definition = dictionary_data.get('definition')
        found = dictionary_data.get('found', False)
        similar_words = dictionary_data.get('similar_words', [])
        
        if found and definition:
            response = f"**{word}**\n\n{definition}"
            return response
        else:
            response = f"'{word}' was not found in the dictionary."
            
            if similar_words:
                response += "\n\nDid you mean one of these words?\n"
                for similar_word in similar_words:
                    response += f"• {similar_word}\n"
            
            return response

    def process_dictionary_request(self, message_content, is_authenticated=False):
        """
        Main method to process dictionary requests
        Returns None if not a dictionary query or if user needs to be authenticated
        Returns dictionary response string if it's a dictionary query and user can access it
        """
        # First check if this looks like a dictionary query
        is_dictionary_query = self.should_handle_request(message_content, is_authenticated)
        
        if not is_dictionary_query:
            return None
        
        # Process the request regardless of authentication status
        search_term = self.extract_search_term(message_content)
        
        # Search for dictionary data
        dictionary_data = self.search_dictionary(search_term)
        
        # Format and return response
        return self.format_dictionary_response(dictionary_data)