import xml.etree.cElementTree as etree 
import sys

tree = etree.fromstring(sys.stdin.read())

def dump(tree, indent):
    print indent+tree.tag
    for a in tree.attrib.keys():
        print indent+"  "+a+"="+tree.get(a)
    for c in tree:
        dump(c, indent+"  ")
    text = tree.tail
    if text:
        text = text.strip()
        if text:
            print indent+"text: "+repr(text)

dump(tree, "")
