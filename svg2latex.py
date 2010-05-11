#!/usr/bin/python
'''
Copyright (C) 2008,2009,2010 Richard Henwood, rjhenwood@yahoo.co.uk

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA



------------------------------------------
'''

# We will use inex module with predefined effect base class.
import string

from optparse import OptionParser
from xml.dom.minidom import parse, parseString
from string import Template

import pprint
import re
import sys
import os.path
import math
import subprocess
import tempfile
import shutil
import platform

class svg2latex():
    """ Constructor.
    Defines "--what" option of a script."""

    myHorizontalFudgePX = -8  # we have to knudge text over a bit to get it to align horizontally.
    #flow_x_offset = -3.47433
    #flow_y_offset = 9.4698369
    flow_x_offset = 0.0
    flow_y_offset = 0.0

#####################################################################
    def svgfile_handler(option, opt, value, parser):
        print ("option = %s" % option)
        print ("opt = %s" % opt)
        print ("value = %s" % value)
        print ("parser = %s" % parser)

    def __init__(self):
        # Call base class construtor.
        
        usage = """Convert svg to latex picture format and use 
Inkscape to generate a pdf for all the bits 
which are not text. 

-f [--svgfile]          <filename> svgfilename.
-l [--latexoutfile]     <filename> name for latex output file.
-o                      overwrite the output files automatically.
-e   			create an eps file instead of pdf.

A pdf file is also created. This is given the same name as the 
latex outfile with the extension 'pdf'. This file is generated by 
Inkscape, which must be on the path for this script to work.

"""

        parser = OptionParser(usage)
        parser.add_option("-f", "--svgfile", dest="svgfilename",
                help="svg input file")
        parser.add_option("-l", "--latexoutfile", dest="latexfilename",
                help="latex file to output to")
        parser.add_option("-o", "--overwrite", dest="overwrite",
                action="store_true",
                help="automatically overwrite output")
        parser.add_option("-e", "--epsoutput", dest="epsoutput",
                action="store_true",
                help="make eps instead of pdf")

        (options, args) = parser.parse_args()
    
        if options.latexfilename is None:
            print ("--latexoutfile not specified")
            sys.exit(usage)

        self.latexfilename = options.latexfilename
        latexhead, latextail = os.path.split(self.latexfilename)
        if (latexhead is not None and latexhead is not ""):
            latexhead += os.sep
        latexroot, latexext = os.path.splitext(latextail)

        self.epsfileoutput = None
        if options.epsoutput is None:
            self.lateximagefile = latexhead + latexroot + '.pdf' 
        else:
            self.lateximagefile = latexhead + latexroot + '.eps' 
            self.epsfileoutput = 1

        self.latexsvgtmp = tempfile.NamedTemporaryFile(delete=False)  

        if options.svgfilename is None:
            print ("--svgfile not specified")
            sys.exit(usage)
        if options.overwrite is None:
            self.autooverwrite = 0 
        else:
            self.autooverwrite = options.overwrite
        
        self.svgfilename = options.svgfilename

        print (" svg filename = %s" % self.svgfilename)
        print (" latex image file = " + self.lateximagefile)
        print (" latex input file = " + self.latexfilename)

        self.origsvg = parse(self.svgfilename) 
        self.notextsvg = parse(self.svgfilename) 

        # these namespaces are useful.
        #  xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
        #  xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
        #  xmlns="http://www.w3.org/2000/svg"

#####################################################################

    def tidyup(self):
        os.unlink(self.latexsvgtmp.name)

#####################################################################

    def makePDF(self):

        # first, make a copy of the svg with all the text removed.
        for element in self.notextsvg.getElementsByTagName("flowRoot"):
            element.parentNode.removeChild(element)

        for element in self.notextsvg.getElementsByTagName("text"):
            element.parentNode.removeChild(element)

        # and save it in a temp file
        self.notextsvg.writexml(self.latexsvgtmp)
        self.latexsvgtmp.close()	

        # now call inkscape with this file to produce a
        # pdf version.
        # TODO: this is a hard dependency on inkscape which might 
        # be nice to replace with cairo at some later
        # date...

        temppdffile = tempfile.NamedTemporaryFile(delete=False)  
        temppdffile.close()
        
        exportcmd = "--export-eps"
        if self.epsfileoutput is None:
            exportcmd = "--export-pdf"
            
        inkscapecmd = "inkscape"
        if platform.system() == 'Windows':
            inkscapecmd = "C:\\Program Files\\Inkscape\\inkscape.exe"
        
        subprocess.call([inkscapecmd, exportcmd, temppdffile.name, "--file", self.latexsvgtmp.name])
        #print "copying file to: " + self.lateximagefile
        shutil.copy(temppdffile.name, self.lateximagefile)
        
        os.unlink(temppdffile.name)
        

#####################################################################

    def toLatex(self):
        filename = self.latexfilename
        if os.path.isfile(filename) and not self.autooverwrite:
            sys.stderr.write("File '" + filename + "' already exists. Quitting.\n")
            sys.exit()

        FILE = open(filename,"w")

        # we need to extract the global translation of the whole 
        # page.
        dom1 = parse(self.svgfilename)
        #pprint.pprint(dom1)
        ele_g = dom1.getElementsByTagName("g")[0]
        self.g_trans_x, self.g_trans_y = (0.0, 0.0)

        ele_svg = dom1.getElementsByTagName("svg")[0]
        pgheight = ele_svg.attributes["height"].value
        if pgheight.endswith("mm"):
            pgheight = pgheight.rstrip("mm")
            pgheight = float(pgheight) * 3.5433
        pgwidth = ele_svg.attributes["width"].value
        if pgwidth.endswith("mm"):
            pgwidth = pgwidth.rstrip("mm")
            pgwidth = float(pgwidth) * 3.5433


        latexstr = self.page_info(pgwidth, pgheight)

        # TODO, remove the g_trans var from global scope.
        for node in dom1.getElementsByTagName("flowRoot"):
            if node.parentNode.hasAttribute("transform"):
                self.g_trans_x, self.g_trans_y = self.get_global_trans(node.parentNode.attributes["transform"].value)
            latexstr += "\n"
            latexstr += self.process_flow(node, pgwidth, pgheight, self.g_trans_x, self.g_trans_y)
            latexstr += "\n"
        for node in dom1.getElementsByTagName("text"):
            if node.parentNode.hasAttribute("transform"):
                self.g_trans_x, self.g_trans_y = self.get_global_trans(node.parentNode.attributes["transform"].value)
            latexstr += "\n"
            latexstr += self.process_text(node, pgwidth, pgheight, self.g_trans_x, self.g_trans_y)
            latexstr += "\n"
        latexstr += " \\end{picture}\n"
        latexstr += "\\endgroup\n"
        
        FILE.writelines(str(latexstr))
        FILE.close()

#####################################################################
    
    def get_global_trans(self, trans_str):
        tmp_str = trans_str.lstrip("translate(")
        tmp_str = tmp_str.rstrip(")")
        return map(lambda x: float(x), tmp_str.split(","))

#####################################################################

    def page_info(self, pgwidth, pgheight):

        pagestr = ''
        pagestr += "\\begingroup\n"
        pagestr += " \setlength{\unitlength}{0.8pt}\n" # this is standard SVG units, as PT.
        pagestr += " \\begin{picture}("
        pagestr += str(pgwidth)
        pagestr += ","
        pagestr += str(pgheight)
        pagestr += ")\n"
        pagestr += " \put(0,0){\includegraphics"
        pagestr += "{"
        pagestr += re.sub(r'\\', r'/', self.lateximagefile)
        pagestr += "}}\n"
        return pagestr

#####################################################################

    def process_style(self, stylenode):
        color = "{black}"
        fontSize = ""
        customColors = ""
        colorNum = 1
        mboxcode = ''
        fontSizeInt = 1;
        fontSizeFloat = 10;
        if stylenode is not None:
            for styleElement in string.split(stylenode, ';'):
                directive, value = string.split(styleElement, ':')
                if directive == "text-align":
                    #print "directive found:", directive, value
                    if value == 'center':
                        mboxcode = 'c'
                    elif value == 'end':
                        mboxcode = 'r'
                    else:
                        mboxcode = 'l'
                if directive == "fill":
                    if re.match(r'^#', value) is not None:
                        color = "{inkcol" + `colorNum` + "}"
                        red = '0x' + value[1:3]
                        green = '0x' + value[3:5]
                        blue = '0x' + value[5:7]
                        customColors += "\\definecolor{inkcol" + `colorNum` + "}{rgb}{"
                        customColors += `eval(red)/255.0` + ','
                        customColors += `eval(green)/255.0` + ','
                        customColors += `eval(blue)/255.0` + '}\n'
                        colorNum += 1
                    else:
                        color = "{" + value + "}"
                if directive == "font-size":
                    fontSize,fontSizeFloat = self.fontSizeLookup(value)
        #print "fontsize: " + fontSize
        #print "fontsizefloat: " + fontSizeFloat
        return color, fontSize, customColors, colorNum, mboxcode, fontSizeFloat

#####################################################################

    def process_transform(self, transform):
        rotate = 0
        transX = 0
        transY = 0
        if transform is not None:
            transArrTmp = re.split(r"[,\(\)]", transform)
            transArr = []
            for element in transArrTmp:
                if re.search('^[-+]?\d+\.?\d*', element):
                    transArr.append(element)
            transX = float(transArr[-2])
            transY = float(transArr[-1])
            if re.match(r'^matrix', transform) is not None:
                rotate = self.get_angle(transArr[0], transArr[2], transArr[1], transArr[3])
        return rotate, transX, transY

#####################################################################
    def process_tspan_transform(self, transform, tmpx, tmpy):
        rotate = 0
        transX = 0
        transY = 0
        if transform is not None:
            transArrTmp = re.split(r"[,\(\)]", transform)
            transArr = []
            for element in transArrTmp:
                if re.search('^[-+]?\d+\.?\d*', element):
                    transArr.append(element)
            transX = tmpx #float(transArr[-2])
            transY = tmpy #float(transArr[-1])
            if re.match(r'^matrix', transform) is not None:
                rotate = self.get_angle(transArr[0], transArr[1], transArr[2], transArr[3])
        #        print "determinant= ", self.get_determinant(transArr[0], transArr[1], transArr[2], transArr[3])
                transX, transY = self.do_transform(transArr[0], transArr[2], transArr[1], transArr[3], tmpx, tmpy)
        return rotate, transX, transY

#####################################################################
# this processes <text> dom elements.
# it is as ugly as it looks.
# TODO: add code to deal with 'align-centre' style.

    def process_text(self, flowNode, imgWidth, imgHeight, g_x_trans, g_y_trans):
        #tmpstr = ''
        style = flowNode.attributes["style"]
        color, fontSize, customColors, colorNum, mboxcode, fontSizeInt = self.process_style(style.value)
        put = Template('   \put($x,$y)')

        rotate, transX, transY = (0.0, 0.0, 0.0)

        tmpx = float(flowNode.attributes["x"].value)
        tmpy = float(flowNode.attributes["y"].value)

        if flowNode.hasAttribute("transform"):
            transform = flowNode.attributes["transform"].value
            # this is a hack for the cases where inkscape optimises
            # a 180o rotation into a scale(-1,-1)
            if transform.startswith("scale("):
                transform = "matrix(-1,0,0,-1)"

            rotate, transX, transY = self.process_tspan_transform(transform, 0.0, 0.0)


        alltext = '' 
        (x2, y2) = (None, None)
        for element in flowNode.getElementsByTagName("tspan"):
            #x1 = (float(element.attributes["x"].value))
            #y1 = (float(element.attributes["y"].value))
            x1 = tmpx
            y1 = tmpy
            x2 = transX + x1*math.cos(rotate) - y1*math.sin(rotate)
            y2 = transY + x1*math.sin(rotate) + y1*math.cos(rotate)
            x2 += g_x_trans 
            y2 += g_y_trans

            y2 = float(imgHeight) - y2
            myWidth = float(imgWidth)

            if mboxcode == 'c':
                # this block adjusts x coord for 
                # cases where we wish to centre the text.
                x2 -= myWidth/2.0

            if element.hasAttribute("style"):
                fontSize = self.get_fontsize(element.attributes["style"].value, fontSize)
            if element.firstChild is not None:
                alltext += "\\textcolor" + color + "{" + fontSize + "{" + element.firstChild.data + "}}\\\\\n"

# vskip -1cm
        txt = Template('{\\rotatebox{' + `self.toDEG(rotate)` + '}{\makebox(0,0)[tl]{\strut{}{$text}}}}%\n')
        miniPg = '\n   \\begin{minipage}[h]{' + str(myWidth * 0.8) + 'pt}\\vspace{-2ex}\n'
        if mboxcode == 'c':
            miniPg += '\\begin{center}\n'
            miniPg += alltext
            miniPg += '\\end{center}\n'
        elif mboxcode == 'r':
            miniPg += '\\begin{flushright}\n'
            miniPg += alltext
            miniPg += '\\end{flushright}\n'
        else:
            miniPg += alltext

        miniPg += '\end{minipage}'
        return customColors + put.substitute(x=x2, y=y2) + txt.substitute(text=miniPg)

#####################################################################

    def process_flow(self, flowNode, imgWidth, imgHeight, g_x_trans, g_y_trans):
        tmpstr = ''
        style = flowNode.attributes["style"]
        color, fontSize, customColors, colorNum, mboxcode, fontSizeInt = self.process_style(style.value)
        put = Template('   \put($x,$y)')
        #print "flow processing"

        rotate, transX, transY = (0.0, 0.0, 0.0)
        if flowNode.hasAttribute("transform"):
            transform = flowNode.attributes["transform"]
            rotate, transX, transY = self.process_transform(transform.value)

        for element in flowNode.getElementsByTagName("rect"):
            x1 =  (float(element.attributes["x"].value))# + g_x_trans + self.flow_x_offset 
            y1 =  (float(element.attributes["y"].value))# + g_y_trans + self.flow_y_offset 
            x2 = transX + x1*math.cos(rotate) - y1*math.sin(rotate)
            y2 = transY + x1*math.sin(rotate) + y1*math.cos(rotate)
            x2 = x2 + g_x_trans
            y2 = y2 + g_y_trans
            #print "x2: ", (float(element.attributes["x"].value)), g_x_trans, transX, x1, x2
            #print "y2: ", (float(element.attributes["y"].value)), g_y_trans, transY, y1, y2
            y2 = float(imgHeight) - y2


            tmpstr += put.substitute(x=x2, y=y2)
            myWidth = float(element.attributes["width"].value)

        alltext = '' 
        for element in flowNode.getElementsByTagName("flowPara"):
            if element.hasAttribute("style"):
                fontSize = self.get_fontsize(element.attributes["style"].value, fontSize)
            if element.firstChild is not None:
                alltext += "\\textcolor" + color + "{" + fontSize + "{" + element.firstChild.data + "}}\\\\\n"

        txt = Template('{\\rotatebox{' + `self.toDEG(rotate)` + '}{\makebox(0,0)[tl]{\strut{}{$text}}}}%\n')
        miniPg = '\n    \\begin{minipage}[h]{' + str(myWidth * 0.8) + 'pt}\n'
        if mboxcode == 'c':
            miniPg += '\\begin{center}\n'
            miniPg += alltext
            miniPg += '\\end{center}\n'
        elif mboxcode == 'r':
            miniPg += '\\begin{flushright}\n'
            miniPg += alltext
            miniPg += '\\end{flushright}\n'
        else:
            miniPg += alltext

        miniPg += '\end{minipage}'
        tmpstr += txt.substitute(text=miniPg)
        return customColors + tmpstr
#####################################################################

    def get_fontsize (self, att, fontSize):
        size = att.partition("font-size:")[2]
        size = size.partition(";")[0]
        if size is None:
            return fontSize
        return self.fontSizeLookup(size)[0]

    def do_transform(self, a,b,c,d,x,y):
        x2 = float(a)*float(x) + float(b)*float(y)
        y2 = float(c)*float(x) - float(d)*float(y)
        return (x2, y2)

    def undo_transform(self, a,b,c,d,x,y):
        x2 = float(a)*float(x) + float(b)*float(y)
        y2 = -float(c)*float(x) + float(d)*float(y)
        return (x2, y2)

    def get_determinant(self, a,b,c,d):
        return float(a)*float(d) - float(b)*float(c)

    def get_angle(self, x1, x2, y1, y2):
        #sys.stderr.write("angle  '" + x1 + "'." + x2 + "'." + y1 + "'." + y2 + "'.")
        acosA = math.acos(float(x1))
        if (math.asin(float(x2)) >= 0):
            return float(acosA)
        else:
            return 2*math.pi - float(acosA)


    def toDEG(self, rad):
        return 360-180.0*rad/math.pi


    def fontSizeLookup (self, pxSize):
        sizeStr = "\\normalsize"
        if not re.search('px$', pxSize):
            try: 
                float(pxSize)
            except ValueError:
                sys.stderr.write("found unusual font size: " + pxSize + " assuming '\\normalsize' missing.\n")
                return "\\normalsize", 10
                
            sys.stderr.write("found unusual font size: " + pxSize + " assuming 'px' missing.\n")
            pxSize += "px"

        #print "Pxsize = " + pxSize
        size = re.split(r"px$", pxSize)
        #print "size = " + size
        size[0] = float(size[0])
        if size[0] < 7:
            return "\\tiny", size[0]
        if size[0] < 8:
            return "\\scriptsize", size[0]
        if size[0] < 9:
            return "\\footnotesize", size[0]
        if size[0] < 10:
            return "\\small", size[0]
        if size[0] < 12:
            return "\\normalsize", size[0]
        if size[0] < 14:
            return "\\large", size[0]
        if size[0] < 18:
            return "\\Large", size[0]
        if size[0] < 20:
            return "\\LARGE", size[0]
        if size[0] < 24: 
            return "\\huge", size[0]
        if size[0] >= 24:
            return "\\Huge", size[0]

        sys.stderr.write("found unusual font size: " + pxSize + " assuming normalsize.")
        return "\\normalsize", 10
        #\tiny	5	5
        #\scriptsize	7	7
        #\footnotesize	8	8
        #\small	9	9
        #\normalsize	10	10
        #\large	12	12
        #\Large	14	14.40
        #\LARGE	18	17.28
        #\huge	20	20.74
        #\Huge	24	24.88
        #else: 
        #    sys.stderr.write("found unusual font size: " + pxSize + " assuming normalsize.")
        #    return "\\normalsize", 10




svgfile = svg2latex()
svgfile.toLatex()
svgfile.makePDF()
svgfile.tidyup()
print ("completed")
