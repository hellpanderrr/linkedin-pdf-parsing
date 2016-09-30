# -*- coding: utf8 -*-
import os
import re
import sqlite3
import argparse
import sys
import glob
from collections import OrderedDict
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfpage import PDFTextExtractionNotAllowed
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.pdfdevice import PDFDevice
from pdfminer.layout import LAParams
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LAParams, LTTextBox, LTTextLine, LTFigure, LTImage, LTTextLineHorizontal, LTChar, LTLine, \
    LTText


def main(argv):
    def create_database(output_folder):
        if not os.path.exists(os.path.split(output_folder)[0]):
            os.makedirs(os.path.split(output_folder)[0])
        conn = sqlite3.connect(os.path.abspath(output_folder))
        c = conn.cursor()
        c.execute('DROP TABLE IF EXISTS Title')
        c.execute('''CREATE TABLE Title
                     (TitleId INTEGER PRIMARY KEY NOT NULL,Title VARCHAR)''')
        c.execute('DROP TABLE IF EXISTS Person')
        c.execute('''CREATE TABLE Person
                     (PersonId INTEGER PRIMARY KEY NOT NULL,Name VARCHAR,Surname VARCHAR)''')
        c.execute('DROP TABLE IF EXISTS Experience')
        c.execute('''CREATE TABLE Experience
                     (ExperienceID INTEGER PRIMARY KEY NOT NULL,PersonID INTEGER,CompanyID INTEGER,TitleID INTEGER,StartMonth VARCHAR,StartYear VARCHAR,EndMonth VARCHAR,EndYear VARCHAR,Ongoing INTEGER )''')
        c.execute('DROP TABLE IF EXISTS Company')
        c.execute('''CREATE TABLE Company
                     (CompanyId INTEGER PRIMARY KEY NOT NULL,CompanyName VARCHAR)''')
        c.execute('DROP TABLE IF EXISTS Major')
        c.execute('''CREATE TABLE Major
                     (MajorId INTEGER PRIMARY KEY NOT NULL,Major VARCHAR)''')
        c.execute('DROP TABLE IF EXISTS School')
        c.execute('''CREATE TABLE School
                     (SchoolId INTEGER PRIMARY KEY NOT NULL,School VARCHAR)''')
        c.execute('DROP TABLE IF EXISTS Education')
        c.execute('''CREATE TABLE Education
                     (EducationId INTEGER PRIMARY KEY NOT NULL,PersonID INTEGER,DegreeId INTEGER,SchoolId INTEGER,MajorId INTEGER,StartMonth VARCHAR,StartYear VARCHAR,EndMonth VARCHAR,EndYear VARCHAR,Ongoing INTEGER )''')
        c.execute('DROP TABLE IF EXISTS Degree')
        c.execute('''CREATE TABLE Degree
                     (DegreeId INTEGER PRIMARY KEY NOT NULL,Degree VARCHAR)''')
        return conn

    def getfilelist(path, extension=None):
        filenames = []
        for i in os.walk(path.decode('utf-8')).next()[2]:
            if (extension):
                if i.endswith(extension):
                    # print os.path.join(path,i)
                    filenames.append(os.path.join(path, i))
            else:
                filenames.append(os.path.join(path, i))
        return filenames

    def insert(table, column, row_value, c):
        """Checks if a row with 'value' exists in a 'column' of a 'table' using database cursor 'c', if so it returns an Id of 
        first matching row, otherwise it inserts a new row and returns it's id
        """
        data = c.execute("SELECT * FROM {} WHERE {} = ?".format(table, column), [row_value]).fetchone()

        if data is None:
            c.execute("INSERT INTO {} VALUES (NULL,?)".format(table), [row_value])
            dataId = c.lastrowid
        else:
            dataId = data[0]
        return dataId

    def parse_date(dates):
        """Parses a string with the dates in it,
        take string, returns a dictionary: {'from_month':'','from_year':'','to_month':'','to_year':''}
        """
        ret = {'from_month': '', 'from_year': '', 'to_month': '', 'to_year': ''}

        dates = dates.strip().split('-')

        if len(dates) == 2:
            date_from = dates[0].strip().split(' ')
            date_to = dates[1].strip().split(' ')
            if len(date_from) == 1:
                ret['from_month'] = ''
                ret['from_year'] = date_from[0]
            elif len(date_from) == 2:
                ret['from_month'] = date_from[0]
                ret['from_year'] = date_from[1]
            if len(date_to) == 1:
                ret['to_month'] = ''
                ret['to_year'] = date_to[0]
            elif len(date_to) == 2:
                ret['to_month'] = date_to[0]
                ret['to_year'] = date_to[1]

        return ret

    def get_chars(line, with_anno=True):
        # get chars from the LTTextline
        ret = []
        for char in line:
            if with_anno:
                ret.append(char)
            elif not with_anno and type(char) <> pdfminer.layout.LTAnno:
                ret.append(char)
        return ret

    isiterable = lambda obj: isinstance(obj, basestring) or getattr(obj, '__iter__', False)

    def get_objects(layout):
        # collecting all objects from the layout, 1 level depth
        objs = []
        for obj in layout:

            if isiterable(obj):
                for element in obj:
                    objs.append(element)
            else:
                objs.append(obj)
        return objs

    def get_data(objs, name):
        """Collects objects from a header with 'name' in it.
        Takes list of LTObjects, returns list of LTObjects   
        """
        FONTSIZE = 17  # heading's font size is 17.85
        ed_st = ed_en = 0
        for idx, obj in enumerate(objs):
            if isinstance(obj, LTTextLineHorizontal) and name in obj.get_text() and get_chars(obj)[
                0].size > FONTSIZE and not ed_st:
                ed_st = idx
            if isinstance(obj, LTLine) and ed_st and not ed_en:
                ed_en = idx
        return objs[ed_st + 1:ed_en]

    def get_name(objs):
        """Collects persons' names, takes a list of LTObjects, returns a 
        list: [name,surname]
        """
        name = ''
        for obj in objs:
            if isinstance(obj, LTTextLine):
                for char in obj:
                    if isinstance(char, LTChar):
                        if char.size > 23:
                            name = obj.get_text()
                            break
        name = name.encode('utf-8').strip().split(' ')

        return [name[0], len(name) > 1 and ' '.join(name[1:])]

    def get_experience_info(objs):
        """Collects companies' names,titles and dates, takes list of LTObjects, returns a 
        list: [title,company,{'from_month':'','from_year':'','to_month':'','to_year':''}]
        """
        FONTSIZE = 13.4  # fontsize of bold headers
        ret = []
        company = title = ''
        for idx, obj in enumerate(objs):
            company = title = ''
            if idx > 0 and get_chars(objs[idx - 1])[0].size > FONTSIZE:
                brackets = re.search('([(]+(.)*[)]+)', obj.get_text())
                # print brackets
                if brackets:
                    header = objs[idx - 1].get_text().split(' at ')
                    if len(header) == 2:
                        company = header[1].strip()
                        title = header[0].strip()
                    ret.append([title, company, parse_date(obj.get_text()[:brackets.start()])])
        return ret

    def get_education_info(objs):
        """Collects schools,majors,dates, takes a list of LTObjects, returns a 
        list: [school,degree,major,{'from_month':'','from_year':'','to_month':'','to_year':''}]
        """
        # collect schools and dates
        FONTSIZE = 13.4  # fontsize of bold headers
        ret = []
        degree = major = dates = school = ''
        for idx, obj in enumerate(objs):
            if get_chars(obj)[0].size > FONTSIZE:
                try:
                    next_object = objs[idx + 1].get_text()
                except Exception, e:
                    print e
                    next_object = ''
                school = obj.get_text()
                # print next_object
                if next_object:
                    second_line = next_object.split(',')
                    if len(second_line) >= 3:
                        degree = second_line[0].strip()
                        major = ' '.join(second_line[1:-1]).strip()
                        dates = parse_date(second_line[-1])
                    elif len(second_line) == 1:
                        dates = parse_date(second_line[0])
                    elif len(second_line) == 2:
                        major = second_line[0]
                        dates = parse_date(second_line[1])

                else:
                    degree = major = ''
                    dates = {'from_month': '', 'from_year': '', 'to_month': '', 'to_year': ''}

                ret.append([school, degree, major, dates])
        return ret

    output_file = os.path.abspath(argv.output)
    input_folder = os.path.abspath(argv.input)
    print 'Input folder: %s, output file: %s ' % (input_folder, output_file)
    conn = create_database(output_file)
    conn.commit()
    c = conn.cursor()
    filelist = getfilelist(input_folder, '.pdf')
    if not filelist:
        print 'No pdf files found in the provided folder.'
        sys.exit(2)
    for f in filelist:
        # print f
        # if not j.endswith('ReidRubsamen, M.D..pdf'): continue
        fp = open(f, 'rb')
        # Create a PDF parser object associated with the file object.
        parser = PDFParser(fp)
        # Create a PDF document object that stores the document structure.
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
            objs.append(sorted(get_objects(layout), key=lambda x: x.y0, reverse=True))
        objs = sum(objs, [])  # flattening to 1D array
        # getting objects from the corresponding sections
        exp = get_data(objs, 'Experience')
        ed = get_data(objs, 'Education')
        name = get_name(objs)[0].decode('utf8')
        surname = get_name(objs)[1].decode('utf8')

        person = c.execute('SELECT * FROM Person WHERE Name=? AND Surname=?', [name, surname]).fetchone()
        if not person:
            c.execute("INSERT INTO Person VALUES (NULL,?,?)", [name, surname])
            personId = c.lastrowid
        else:
            personId = person[0]

        exp_row = OrderedDict([('personId', personId), ('company', ''), ('title', ''), \
                               ('from_month', ''), ('from_year', ''), ('to_month', ''), ('to_year', ''),
                               ('ongoing', '')])
        ed_row = OrderedDict([('personId', personId), ('Degree', ''), ('School', ''), ('Major', ''), \
                              ('from_month', ''), ('from_year', ''), ('to_month', ''), ('to_year', ''),
                              ('ongoing', '')])
        for place in get_experience_info(exp):
            for key in exp_row:
                if key <> 'personId':
                    exp_row[key] = ''
            exp_row['company'] = place[1].strip() and insert('Company', 'CompanyName', place[1], c)
            exp_row['title'] = place[0].strip() and insert('Title', 'Title', place[0], c)
            exp_row['from_month'] = place[2]['from_month'] if 'from_month' in place[2] else ''
            exp_row['from_year'] = place[2]['from_year'] if 'from_year' in place[2] else ''
            exp_row['to_month'] = place[2]['to_month'] if 'to_month' in place[2] else ''
            exp_row['to_year'] = place[2]['to_year'] if 'to_year' in place[2] else ''
            exp_row['ongoing'] = 1 if exp_row['to_year'] == 'Present' else 0
            c.execute("INSERT INTO Experience VALUES (NULL,?,?,?,?,?,?,?,?)", exp_row.values())
        for place in get_education_info(ed):
            for key in ed_row:
                if key <> 'personId':
                    ed_row[key] = ''
            ed_row['Degree'] = place[1].strip() and insert('Degree', 'Degree', place[1], c)
            ed_row['School'] = place[0].strip() and insert('School', 'School', place[0], c)
            ed_row['Major'] = place[2].strip() and insert('Major', 'Major', place[2], c)
            ed_row['from_month'] = place[3]['from_month'] if 'from_month' in place[3] else ''
            ed_row['from_year'] = place[3]['from_year'] if 'from_year' in place[3] else ''
            ed_row['to_month'] = place[3]['to_month'] if 'to_month' in place[2] else ''
            ed_row['to_year'] = place[3]['to_year'] if 'to_year' in place[3] else ''
            ed_row['ongoing'] = 1 if exp_row['to_year'] == 'Present' else 0
            c.execute("INSERT INTO Education VALUES (NULL,?,?,?,?,?,?,?,?,?)", ed_row.values())
        print get_name(objs)
    conn.commit()
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', required=True, help="Directory with pdf files")
    parser.add_argument('-o', '--output', required=True)
    args = parser.parse_args()
    if not os.path.exists(args.input):
        exit("Please specify an existing direcory using the -i parameter.")
    main(args)
