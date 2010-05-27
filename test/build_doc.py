#!/usr/bin/python

from string import Template
import subprocess
import os

svg2latexCMD = "../svg2latex.py"
inkscapeCMD = "inkscape"
svgDIR = "./svg"
outDIR = "./out"
outTEX = "./test.tex"

latexPre = '''
\documentclass[11pt,a4paper,landscape]{report}      %% LaTeX2e document.
\usepackage{graphicx}                %% Preamble.
\usepackage{color}

\\begin{document}

'''

latexFigure = Template('''
\\begin{figure}
\\begin{center}
\scalebox{1.0}{\hskip -4cm \includegraphics{$pngFilename}\input{$texFilename}}

\caption{SVG test file: $$$testName$$}

\label{fig:latexexport}
\end{center}
\end{figure}
''')

latexPost = '''
\end{document}
'''

convertedFiles = []

# render the contents of svgDIR as tex files.
for filename in os.listdir(svgDIR):
    #print  filename
    name = filename.rstrip(".svg")
    svgName = svgDIR+"/"+filename
    latexoutName = outDIR+"/"+filename.rstrip(".svg") + ".tex"
    pngoutName = outDIR+"/"+filename.rstrip(".svg") + ".png"
    #outfile = outDIR+"/"+outName

    subprocess.call([svg2latexCMD, "-f", svgName, "-l", latexoutName])
    subprocess.call([inkscapeCMD, "-f", svgName, "-e", pngoutName])
    convertedFiles.append([name, pngoutName, latexoutName])

    "-f ./svgtest.svg "
    "-l ./output.tex -o"

# write a tex file with the includes all the files.

f = open(outTEX, 'w')
f.write(latexPre)
for name, pngfile, texfile in convertedFiles:
    f.write(latexFigure.substitute(testName=name, pngFilename=pngfile, texFilename=texfile))
f.write(latexPost)
f.close()

print "written:\n"
print outTEX
print "\nfinished."
