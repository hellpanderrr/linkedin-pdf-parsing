from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import HTMLConverter
from pdfminer.converter import TextConverter
from cStringIO import StringIO


def convert_pdf_to_html(path):
    rsrcmgr = PDFResourceManager()
    retstr = StringIO()
    codec = 'utf-8'
    laparams = LAParams()
    device = HTMLConverter(rsrcmgr, retstr, codec=codec, laparams=laparams)
    fp = file(path, 'rb')
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    caching = True
    pagenos=set()
    for page in PDFPage.get_pages(fp, pagenos, caching=caching, check_extractable=True):
        interpreter.process_page(page)
    fp.close()
    device.close()
    ret = retstr.getvalue()
    retstr.close()
    return ret
output = convert_pdf_to_html('G:\\1.pdf')
