'''
Created on Jan 05, 2016

@author: Ankai
'''
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
from bs4 import UnicodeDammit
from urllib.request import Request, urlopen
import requests
import lxml
import PyPDF2
from _io import BytesIO, BufferedWriter


class Paper:
    def __init__ (self, link):
        self.__url = link
        self.__pdfUrl= None
        self.__pap_info = {}
        self.__citersUrl = None
        
        session = requests.session()
        response = session.get(self.__url)
        soup = BeautifulSoup(response.content, 'lxml')

        self.__pap_info['Title'] = soup.find('a', attrs={'class': 'gsc_title_link'}).text
        
        div_info_table = soup.find('div', attrs={'id':'gsc_table'})
        div_fields = div_info_table.find_all('div', attrs={'class':'gs_scl'})

        for field in div_fields:
            fieldName = field.find('div', attrs={'class':'gsc_field'}).text
            #don't need the description
            if (fieldName == "Description"):
                continue
            #stores both number of citations and link to citers page as a field
            if (fieldName == "Total citations"):
                citedBy = field.find('div', attrs={'style':'margin-bottom:1em'}).find('a')
                self.__pap_info['Citations'] = citedBy.text.replace("Cited by ", "")
                self.__citersUrl = citedBy['href']
                break

            self.__pap_info[fieldName] = field.find('div', attrs={'class':'gsc_value'}).text


        self.__pdfUrl = self.findPdfUrlOnPage()

    def getUrl(self):
        return self.__url
    
    def getCitersUrl(self):
        return self.__citersUrl 
        
    def getInfo (self):
        return self.__pap_info

    def getPdfUrl(self):
        return self.__pdfUrl

    def findPdfUrlOnPage(self):
        extractor = GscPdfExtractor()
        return extractor.findPdfUrlFromInfo(self.__url)

    '''#returns number of citations this paper makes to the specified author
    def getCitesToAuthor(self, last_name):
        p = PaperReferenceProcessor()
        p.getCitesToAuthor(last_name, p.getPdfContent(self.__pdfUrl))'''
    
        
class AcademicPublisher:

    def __init__ (self, mainUrl, numPapers):
        
        self.first_name = None
        self.last_name = None
        self.url = mainUrl        
        self.__paper_list = []
        
        session = requests.Session()
        response = session.get(self.url + '&cstart=0&pagesize=' + str(numPapers))
        soup = BeautifulSoup(response.content, "lxml")
        print(soup)
       
        full_name = soup.find('div', attrs={'id': 'gsc_prf_in'}).text.lower().split()
        print(full_name)
        
        #stores the lowercase first and last names
        self.first_name=full_name[0]
        self.last_name=full_name[1]
        print(self.last_name)


       #appends all papers to paperlist
        for one_url in soup.findAll('a', attrs={'class':'gsc_a_at'}, href=True):
            #one_url['href'] finds the link to the paper page
            self.__paper_list.append(Paper('https://scholar.google.ca' + one_url['href']))
       
       
    def getPapers(self):
        #returns a list of Papers
        return self.__paper_list
    
    # returns number of times a paper that cited a paper from this author cited the author in total
    # takes the index of the paper in papers list and index of a citer in that paper object
    def getNumCitesByPaper(self, indexPaper, indexCiter):
        pdfExtractor = GscPdfExtractor()
        paper = self.__paper_list[indexPaper]
        pdfUrls = pdfExtractor.findPapersFromCitations(paper.getCitersUrl())

        analyzer = PaperReferenceProcessor()
        content = analyzer.getPdfContent(pdfUrls[indexCiter])
        numCites = analyzer.getCitesToAuthor(self.getLastName(), content)

        return numCites

    def getFirstName(self):
        return self.first_name

    def getLastName(self):
        return self.last_name
    
class GscPdfExtractor:

    def findPapersFromCitations(self, citationsUrl):
        session = requests.session()
        response = session.get(citationsUrl)
        soup = BeautifulSoup(response.content, 'lxml')
        
        linkExtracts = soup.findAll('div', attrs={'class':'gs_md_wp gs_ttss'})
        pdfUrls = []
        
        for extract in linkExtracts:
            #this code will skip links with [HTML] tag and throw error for links that are only "Get it at UWaterloo"
            try:
                if extract.find('span', attrs={'class':'gs_ctg2'}).text == "[PDF]":
                    pdfUrls.append(extract.find('a')['href'])
                else:
                    print(extract.find('span', attrs={'class':'gs_ctg2'}).text+" tag process will be coded later")
            except:
                print('No tag, "Get it at waterloo" part.. to be coded later')
            
        return pdfUrls

    #getting PDF url from paper info page, different from citation list page
    def findPdfUrlFromInfo(self, infoPageUrl):

        session = requests.session()
        response = session.get(infoPageUrl)
        soup = BeautifulSoup(response.content, 'lxml')

        linkExtracts = soup.findAll('div', attrs={'class':'gsc_title_ggi'})

        for extract in linkExtracts:
            #this code will skip links with [HTML] tag and throw error for links that are only "Get it at UWaterloo"
            try:
                if extract.find('span', attrs={'class':'gsc_title_ggt'}).text == "[PDF]":
                    return extract.find('a')['href']
                else:
                    print("html tag, will figure out later")
                    return None
            except:
                print ("get it at waterloo link, will figure out later")
                return None


class PaperReferenceProcessor:
    
    #assuming type is PDF
    def __init__ (self):
        self.references = []
        
    def getPdfContent (self, pdfUrl):
        
        content =""
        remoteFile = urlopen(Request(pdfUrl)).read()
        localFile = BytesIO(remoteFile)

        pdf = PyPDF2.PdfFileReader(localFile)
        
        for pageNum in range(pdf.getNumPages()):
            content+= pdf.getPage(pageNum).extractText()
            
        return self.standardize(content)
    
    def getCitesToAuthor (self, last_name, pdfContent):

        index = pdfContent.find("references")
        if (index==-1):
            print("can't find reference sections")
            return -1
        
        refContent = pdfContent[index:]
        
        counter = 0
        while (refContent.find(last_name)!=-1):
            refIndex = refContent.find(last_name)
            counter+=1
            refContent = refContent[refIndex+len(last_name):]
        
        return counter

    #removes line breaks, white space, and puts it to lower case
    def standardize(self, str):
        return str.replace("\n", "").replace(" ", "").lower()



vas = AcademicPublisher('https://scholar.google.ca/citations?user=_yWPQWoAAAAJ&hl=en&oi=ao', 2)
#print(vas.getPaperCitationsByIndex(1))
print (vas.getPapers())
print (vas.getNumCitesByPaper(0, 0))


'''extractor = GscPdfExtractor('https://scholar.google.ca/scholar?oi=bibs&hl=en&oe=ASCII&cites=2412871699215781213&as_sdt=5')
print(extractor.findPaperUrls())'''


#p = PaperReferenceProcessor()
#print(p.getCitesToAuthor(vas, p.getPdfContent('http://www.diva-portal.org/smash/get/diva2:517321/FULLTEXT02')))

#g = GscPdfExtractor()
#print(g.findPdfUrlFromInfo('https://scholar.google.ca/citations?view_op=view_citation&hl=en&user=_yWPQWoAAAAJ&citation_for_view=_yWPQWoAAAAJ:_xSYboBqXhAC'))

#test_paper = Paper('https://scholar.google.ca/citations?view_op=view_citation&hl=en&user=_yWPQWoAAAAJ&citation_for_view=_yWPQWoAAAAJ:_xSYboBqXhAC')
#print(test_paper.getPdfUrl())
#print(test_paper.getCitersUrl())
#print(test_paper.getInfo())


    
        
