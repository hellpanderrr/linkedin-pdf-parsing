import os
import re
import sqlite3
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

conn = sqlite3.connect('ex2.db')
c = conn.cursor()

c.execute('''CREATE TABLE Title
             (TitleId integer primary key not null,Title varchar)''')
c.execute('''CREATE TABLE Person
             (PersonId integer primary key not null,Name varchar)''')
c.execute('''CREATE TABLE Experience
             (ExperienceID integer primary key not null,PersonID integer,CompanyID integer,TitleID integer,EndYear varchar,StartYear varchar,Ongoing integer )''')
c.execute('''CREATE TABLE Company
             (CompanyId integer primary key not null,CompanyName varchar)''')
c.execute('''CREATE TABLE Major
             (MajorId integer primary key not null,Major varchar)''')
c.execute('''CREATE TABLE School
             (SchoolId integer primary key not null,School varchar)''')
c.execute('''CREATE TABLE Education
             (EducationId integer primary key not null,PersonID integer,DegreeId integer,SchoolId integer,MajorId integer,EndYear varchar,StartYear varchar,Ongoing integer )''')
c.execute('''CREATE TABLE Degree
             (DegreeId integer primary key not null,Degree varchar)''')

conn.commit()

conn = sqlite3.connect('ex5.db')
c = conn.cursor()
def check_exists(table,column,row_value,c):
        print (table,column,row_value)
        data = c.execute("SELECT * FROM ? WHERE ? = ?", (table,column,row_value)).fetchone()
        if data is None:
            c.execute("INSERT INTO ? VALUES (NULL,?)" , [table,row_value])
            dataId = c.lastrowid
        else:
            dataId = data[0]
        return dataId
def parse_date(dates):
    ret = {'from_month':'','from_year':'','to_month':'','to_year':''}
   
    dates = dates.strip().split('-')
    #print dates
    if len(dates) == 1:
         date = dates.strip().split(' ')
         if len(date) == 1:
                ret =  ['','','',date]
         elif len(date) == 2:
                ret =  [date[0],date[1]]
    elif len(dates) == 2:
       
        date_from = dates[0].strip().split(' ')
        
        date_to   = dates[1].strip().split(' ')
        if len(date_from) == 1:
             ret['from_month'] = ''
             ret['from_year']  = date_from[0]
        elif len(date_from) == 2:
             ret['from_month'] = date_from[0]
             ret['from_year']  = date_from[1]
        if len(date_to) == 1:
             ret['to_month'] = ''
             ret['to_year']  = date_to[0]
        elif len(date_to) == 2:
             ret['to_month'] = date_to[0]
             ret['to_year']  = date_to[1]
        
    return ret
def get_chars(line,with_anno=True):
    #get chars from the LTTextline
    ret=[]
    for char in line:
        if with_anno:
            ret.append(char)
        elif not with_anno and type(char)<> pdfminer.layout.LTAnno:
            ret.append(char)
    return ret
isiterable = lambda obj: isinstance(obj, basestring) or getattr(obj, '__iter__', False)
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
    """Collects objects from a header with 'name' in it.
    Takes list of LTObjects, returns list of LTObjects   
    """    
    ed_st = ed_en = 0
    for idx,obj in enumerate(objs):
        if isinstance(obj,LTTextLineHorizontal) and name in obj.get_text() and not ed_st:
            ed_st = idx
        if isinstance(obj,LTLine) and ed_st and not ed_en:
            ed_en = idx           
    return objs[ed_st+1:ed_en]


def get_name(objs):
    #get person's name
    name =''
    for obj in objs:
        if isinstance(obj, LTTextLine):
            for char in obj:
                if isinstance(char, LTChar):
                    if char.size>23:
                        name = obj.get_text()
                        break
    return name.encode('utf-8')
def get_experience_info(objs):
    """Collects companies' names and dates, takes list of LTObjects, returns a 
    list: [title,company,{'from_month':'','from_year':'','to_month':'','to_year':''}]
    """
    ret= []
    company = title = ''
    for idx,obj in enumerate(objs):
         if idx>0 and get_chars(objs[idx-1])[0].size > 13.4:
                brackets = re.search('([(]+(.)*[)]+)',obj.get_text())
                if brackets:
                    header = objs[idx-1].get_text().split('at')
                    if len(header) == 2:
                        company = header[1].strip()
                        title   = header[0].strip()
                    ret.append([title,company,parse_date(obj.get_text()[:brackets.start()])]) 
    return ret
def get_education_info(objs):
    #collect schools and dates
    ret= []
    degree = major = dates = school = ''
    for idx,obj in enumerate(objs):
         if  get_chars(obj)[0].size > 13.4:
                try:
                    next_object = objs[idx+1].get_text()
                except Exception,e:
                    print e
                    next_object = ''
                school = obj.get_text()
                if next_object:
                    second_line = next_object.split(',')
                    if len(second_line) == 3:
                        degree = second_line[0].strip()
                        major  = ' '.join(second_line[1:-1]).strip()
                        dates  = parse_date(second_line[-1])
                else:
                    degree = major = ''
                    dates = {'from_month':'','from_year':'','to_month':'','to_year':''}
                    
                ret.append([school,degree,major,dates])            
    return ret


for j in getfilelist('G:\\yc_founder_bios','.pdf'):
    if not j.endswith('Siegel.pdf'): continue
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
    # Create a PDF device object.
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
    person = c.execute('SELECT * FROM Person WHERE Name=?', [get_name(objs).decode('utf8')]).fetchone()
    if not person:
        c.execute("INSERT INTO Person VALUES (NULL,?)" , [get_name(objs).decode('utf8')])
        personId = c.lastrowid
    else:
        personId = person[0]
    exp_row = [personId,'company','title','start','end','ongoing']
    ed_row = [personId,'Degree','School','Major','start','end','ongoing']
    for place in get_experience_info(exp):
        exp_row[1] = check_exists('Company','CompanyName',place[1],c)       
        exp_row[2] = check_exists('Title','Title',place[0],c)
        exp_row[3] = place[2]['from_year']
        exp_row[4] = place[2]['to_year']
        exp_row[5] = 1 if exp_row[4] == 'Present' else 0
        c.execute("INSERT INTO Experience VALUES (NULL,?,?,?,?,?,?)" , exp_row) 
        #cursor.lastrowid
    for place in get_education_info(ed):
        ed_row[1:] = ['']*6
        if place[1]:
            c.execute("INSERT INTO Degree VALUES (NULL,?)" , [place[1]]) 
            ed_row[1] = c.lastrowid                    
        if place[0]:
            c.execute("INSERT INTO School VALUES (NULL,?)" , [place[0]]) 
            ed_row[2] = c.lastrowid        
        if place[2]:
            c.execute("INSERT INTO Major VALUES (NULL,?)" , [place[2]])
            ed_row[3] = c.lastrowid
        ed_row[4] = place[3]['from_year']
        ed_row[5] = place[3]['to_year']
        ed_row[6] = 1 if exp_row[5] == 'Present' else 0
        c.execute("INSERT INTO Education VALUES (NULL,?,?,?,?,?,?,?)" , ed_row) 
        #cursor.lastrowid
    print j ,len(objs),get_name(objs),exp,ed
conn.commit()
conn.close()
