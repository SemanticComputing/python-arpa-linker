import re
import sys
from link_helper import process_stage


def preprocessor(text, *args):
    text = text.strip()
    text = re.sub(r':\w+', ' ', text)
    # KLo = Kotkan Lohko
    text = re.sub(r'\bklo\b', '', text, re.IGNORECASE)
    return text

if __name__ == '__main__':
    process_stage(sys.argv, preprocessor=preprocessor)
