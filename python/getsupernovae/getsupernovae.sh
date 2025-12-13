#!/bin/bash
mag="${1}"
days="${2}"
currentdate=$(date  +"%Y-%m-%d")
getsupernovae.py "${mag}" "${days}" | iconv -c -f utf-8 -t ISO-8859-15 |  enscript -f Courier13 -p -  | ps2pdf - "${currentdate}-list.pdf"