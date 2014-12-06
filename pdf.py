import os
import re
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfpage import PDFTextExtractionNotAllowed
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.pdfdevice import PDFDevice
from pdfminer.layout import LAParams
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LAParams, LTTextBox, LTTextLine, LTFigure, LTImage,LTTextLineHorizontal,LTChar,LTLine,LTText

isiterable = lambda obj: isinstance(obj, basestring) or getattr(obj, '__iter__', False)
def getfilelist(path, extension=None):
    filenames=[]
    for i in os.walk(path.decode('utf-8')).next()[2]:
            if (extension):
                if os.path.splitext(i)[1] == extension :
                    filenames.append(path+'\\'+i)
            else:            
                filenames.append(path+'\\'+i)
    return filenames
def get_chars(line,with_anno=True):
    #get chars from the LTTextline
    ret = []
    for char in line:
        if with_anno:
            ret.append(char)
        elif not with_anno and type(char) <> pdfminer.layout.LTAnno:
            ret.append(char)
    return ret

def get_objects(layout):
    #collecting all objects from the layout
    objs = []
    for obj in layout:

        if isiterable(obj):
            for element in obj:
                objs.append(element)
        else:
            objs.append(obj)
            #print (i)
    return objs

def get_data(objs,name):
    #get objects from 'name' section
    ed_st = ed_en = 0

    for idx,obj in enumerate(objs):
        if isinstance(obj,LTTextLineHorizontal) and name in obj.get_text():
            ed_st = idx
        if isinstance(obj,LTLine) and ed_st and not ed_en:
            ed_en = idx
    return ed_st,ed_en
def get_name(objs):
    #person's name
    name = ''
    for obj in objs:
        if isinstance(obj, LTTextLine):
            for char in obj:
                if isinstance(char, LTChar):
                    if char.size>23:
                        name = obj.get_text()
                        break
    return name.encode('utf-8')
def get_info(objs):
    #collect company name and dates
    ret = []
    for idx,obj in enumerate(objs):
         if idx>0 and get_chars(objs[idx-1])[0].size>13.4:
                brackets = re.search('([(]+(.)*[)]+)',obj.get_text())
                if brackets:
                    ret.append([objs[idx-1].get_text(),obj.get_text()[:brackets.start()]]) 
    return ret
for j in getfilelist('G:\\yc_founder_bios','.pdf'):
    fp = open(j, 'rb')
    # Create a PDF parser object associated with the file object.
    parser = PDFParser(fp)
    # Create a PDF document object that stores the document structure.
    # Supply the password for initialization.
    document = PDFDocument(parser)
    # Check if the document allows text extraction. If not, abort.
    if not document.is_extractable:
        raise PDFTextExtractionNotAllowed
    # Create a PDF resource manager object that stores shared resources.
    rsrcmgr = PDFResourceManager()
    # Create a PDF device object
    laparams = LAParams()
    # Create a PDF page aggregator object.
    device = PDFPageAggregator(rsrcmgr, laparams=laparams)
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    objs = []
    for page in PDFPage.create_pages(document):
        interpreter.process_page(page)
        # receive the LTPage object for the page.
        layout = device.get_result()
        # collecting objects from the all pages, sorting them by their Y coordinate
        objs.append( sorted( get_objects(layout),key=lambda x:x.y0,reverse=True)     )
    objs = sum(objs,[]) #flattening to 1D array
    exp = get_data(objs,'Experience')
    ed  = get_data(objs,'Education')
    with open(''.join(j.split('.')[:-1])+'.txt','wb') as f:
        f.write(get_name(objs)+'\n')
        f.write('******EXPERIENCE******'+'\n')
        f.write( ''.join(sum(get_info(objs[exp[0]:exp[1]]),[])).encode('utf-8')  )
        f.write('******EDUCATION******'+'\n')
        f.write( ''.join([i.get_text() for i in objs[ed[0]:ed[1]]]).encode('utf-8')  )
        
    print j,len(objs),get_name(objs),get_info(objs[ret[0]:ret[1]])
