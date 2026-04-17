import sys
from lxml import etree

def check_xml(filename):
    try:
        etree.parse(filename)
        print(f"{filename} is valid XML")
    except Exception as e:
        print(f"Error in {filename}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    check_xml(sys.argv[1])
