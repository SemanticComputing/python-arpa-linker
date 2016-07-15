import re
import sys
from link_helper import process_stage


def preprocessor(text, *args):
    text = text.strip()
    text = re.sub(':\w+', ' ', text)
    return text

if __name__ == '__main__':
    process_stage(sys.argv, preprocessor=preprocessor)
