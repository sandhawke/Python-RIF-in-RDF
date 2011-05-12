#!/usr/bin/env python
# -*-mode: python -*-  -*- coding: utf-8 -*-
"""

Convert an RIF-in-RDF RDF document (stdin) into a RIF XML document
(stdout).  The rif-in-rdf "XTr" function.

By Sandro Hawke, sandro@w3.org, May 6 and May 12, 2011, based on a Jan
24 2010 program.

Copyright © 2010,2011 World Wide Web Consortium, (Massachusetts
Institute of Technology, European Research Consortium for Informatics
and Mathematics, Keio University). All Rights Reserved. This work is
distributed under the W3C® Software License [1] in the hope that it
will be useful, but WITHOUT ANY WARRANTY; without even the implied
warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

[1] http://www.w3.org/Consortium/Legal/202/copyright-software-20021231


"""
__version__="unknown"

import sys
import xml.sax.saxutils as saxutils
from rdflib import Graph, RDF, RDFS, URIRef, Literal, Namespace, BNode

indent = "  "
rdfns = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
rifns = "http://www.w3.org/2007/rif#"

RIF = Namespace(rifns)

def main():

    graph = Graph()
    graph.parse(sys.argv[1], format="n3")

    if len(sys.argv) > 2:
        doc = URIRef(sys.argv[2])
    else:
        docs = []
        for c in (RIF.Document, RIF.BLDDocument, 
                  RIF.PRDDocument, RIF.CoreDocument):
            for x in graph.subjects(RDF.type, c):
                docs.append(x)
        if len(docs) == 1:
            doc = docs[0]
        elif len(docs) > 1:
            print >>sys.stderr, "Input contains multiple Document nodes"
            print >>sys.stderr, indent+",".join([repr(x) for x in docs])
            print >>sys.stderr, "Name one on the command line to select it"
            sys.exit(1)
        elif len(docs) < 1:
            print >>sys.stderr, "Input contains no Document nodes"
            for (s,p,o) in graph:
                print s,p,o
            sys.exit(1)

    out = sys.stdout
    to_rif(out, graph, doc, root=True)

def localize(node):
    s = str(node)
    if s.startswith(rifns):
        return s[len(rifns):]
    else:
        # should probably raise an encoding error
        return "***"+s
    
def irimeta(out, graph, node, prefix, multiline):
    """Output any IRIMETA information"""

    multiline=True
    if isinstance(node, URIRef):
        if multiline:
            out.write(prefix+indent)
        out.write("<id><Const type=%s>%s</Const></id>" % (
                saxutils.quoteattr(rifns+"iri"),
                saxutils.escape(unicode(node))
                ))
        if multiline:
            out.write("\n")
    
    meta = graph.value(node, RIF.meta, any=False)
    if meta is not None:
        if multiline:
            out.write(prefix+indent)
        else:
            out.write("\n" + prefix+indent)
        out.write("<meta>\n")
        to_rif(out, graph, meta, prefix+indent+indent)
        if multiline:
            out.write(prefix+indent)
        out.write("</meta>")
        if multiline:
            out.write("\n")

class Xtr_Error (RuntimeError):
    def __init__(self, node):
        self.node = node

class Xtr_Missing_Varname (Xtr_Error):
    pass
    
def out_Const(out,datatype,lexrep,graph,node,prefix):
    out.write(prefix+"<Const type=%s>" % saxutils.quoteattr(datatype))
    irimeta(out, graph, node, prefix, True)
    out.write(saxutils.escape(lexrep).encode("utf-8"))
    out.write("</Const>\n")

def to_rif(out, graph, node, prefix="", root=False):

    cls = graph.value(node, RDF.type, any=False)

    #
    # Table 1 -- Var and Const
    #

    if cls == RIF.Var:
        varname = graph.value(node, RIF.varname, any=False)
        if varname is None:
            raise Xtr_Missing_Varname(node)
        out.write(prefix+"<Var>")
        irimeta(out, graph, node, prefix, True)
        out.write(saxutils.escape(varname)+"</Var>\n")
        return

    if cls == RIF.Const:
        #print "CONST"
        #for s, p, o in graph:
        #    if s == node:
        #        print "PV:   ",p,o
        #        for ss,pp,oo in graph:
        #            if ss == o:
        #                print "          ",pp, oo
                        
        value = graph.value(node, RIF.constIRI, any=False)
        if value is not None:
            out_Const(out,RIF.iri,unicode(value),graph,node,prefix)
            return

        value = graph.value(node, RIF.constname, any=False)
        if value is not None:
            out_Const(out,RIF.local,unicode(value),graph,node,prefix)
            return

        value = graph.value(node, RIF.value, any=False)
        if value:
            #print "VALUE", `value`, value
            if isinstance(value, Literal):
                if value.datatype is None:
                    if value.language is None:
                        lang=""
                    else:
                        lang = value.language
                    datatype = RIF.PlainLiteral
                    lexrep = unicode(value) + "@" + lang
                else:
                    datatype = value.datatype
                    lexrep = unicode(value)
            elif isinstance(value, URIRef):
                datatype = rifns + "iri"
                lexrep = unicode(value)
            else:
                raise RuntimeError, value
            out_Const(out,datatype,lexrep,graph,node,prefix)
            return

        raise RuntimeError, 'ill-formed Const'

    #
    # Table 2 - Mode 3 - Frame Slots
    #

    if cls == RIF.Frame:
        # a very special case of the General Mapping, so handled here
        out.write(prefix+"<Frame>\n")
        irimeta(out, graph, node, prefix, True)
        obj = graph.value(node, RIF.object, any=False)
        out.write(prefix+indent+"<object>\n")
        to_rif(out, graph, obj, prefix+indent+indent)
        out.write(prefix+indent+"</object>\n")
        for slot in graph.items(graph.value(node, RIF.slots, any=False)):
            out.write(prefix+indent+'<slot ordered="yes">\n')
            for p in (RIF.slotkey, RIF.slotvalue):
                v = graph.value(slot, p, any=False)
                to_rif(out, graph, v, prefix+indent+indent)
            out.write(prefix+indent+'</slot>\n')
        out.write(prefix+"</Frame>\n")
        return

    # all other classes are General Mapping

    if cls in (RIF.BLDDocument, RIF.PRDDocument, RIF.CoreDocument):
        cls = RIF.Document

    attrs = ""
    if root:
        attrs += ' xmlns="http://www.w3.org/2007/rif#"'

    out.write(prefix+"<"+localize(cls)+attrs+">\n")
    irimeta(out, graph, node, prefix, False)

    for p in sorted(set(graph.predicates(node)), key=sortkey):
        if p == RIF.id or p == RIF.meta: 
            continue
        do_property(out, graph, node, p, prefix+indent)

    out.write(prefix+"</"+localize(cls)+">\n")

def sortkey(pred):
    # sort by the xml tag we'll use, not the rdf property
    pred = mode_2_by_rdf.get(pred, pred)

    # where std dialects are non-lexicographic...
    return override_ordering.get(pred, pred)

override_ordering = {
    # these are the elements that are NOT in lex order
    # renamed to go in the right place.
    RIF.id: RIF.a10,      # before everything
    RIF.meta: RIF.a11,    # after id, before everything else
    RIF.op: RIF.a20,      # before "formula" and "args"
    RIF.instance: RIF.a20 # before "class"
}
   
                       
mode_2 = (    
   (RIF.directive, RIF.directives),
   (RIF.sentence, RIF.sentences),
   (RIF.declare, RIF.vars),
   (RIF.formula, RIF.formulas),
)
mode_2_by_rdf = dict([(r,x) for (x,r) in mode_2])

def do_property(out, graph, node, p, prefix):

    if p == RDF.type:
        return

    values = sorted(graph.objects(node, p))
    if len(values) > 1:
        raise RuntimeError, "multiple values for "+str(p)
        
    value = values[0]

    if p == RIF.namedargs:
        raise RuntimeError, "named-arguments not implemented"

    elif (value == RDF.nil or 
          graph.value(value, RDF.first, any=False)):

        if p in mode_2_by_rdf:
            if value == RDF.nil:
                # these we just omit
                return
            p = mode_2_by_rdf[p]
            for i in graph.items(value):
                out.write(prefix+"<"+localize(p)+'>\n')
                to_rif(out, graph, i, prefix+indent)
                out.write(prefix+"</"+localize(p)+">\n")

        else:
            out.write(prefix+"<"+localize(p)+' ordered="yes">\n')
            for i in graph.items(value):
                to_rif(out, graph, i, prefix+indent)
            out.write(prefix+"</"+localize(p)+">\n")

    elif isinstance(value, Literal):
        # needed for location & profile - see the Note on Table 2, Mode 1.
        assert value.datatype == None
        assert value.language == None
        out.write(prefix+"<"+localize(p)+">")
        out.write(saxutils.escape(unicode(value)))
        out.write("</"+localize(p)+">\n")

    else:
        out.write(prefix+"<"+localize(p)+">\n")
        to_rif(out, graph, value, prefix+indent)
        out.write(prefix+"</"+localize(p)+">\n")

if __name__ == "__main__":
    main()
