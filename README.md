linkedin pdf parsing
====================

Parsing resumes in a PDF format from linkedIn.
The script takes a folder with PDF files, goes through every one of them looking for Experience and Education sections, extracts all data that is found there and creates a database with following structure:

![alt tag](https://cloud.githubusercontent.com/assets/2708297/5460886/97e635dc-8577-11e4-869c-fe1e3ea08a85.png)
            
Requirements
============
Python 2.7

PDFMiner

Usage
============
<pre> script.py -i inputfolder -o outputfile
</pre>
Script will search 'inputfolder' for PDF files and will create a database with 'outputfile' path.

Example usage:
<pre>
python path/to/script.py -i home/mypdfs -o home/mydb.db
</pre>
