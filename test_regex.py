import re
from urllib.parse import unquote

cds = [
    'attachment; filename="29 MEI 24 UCOK.pdf"; filename*=UTF-8\'\'29%20MEI%2024%20UCOK.pdf',
    'attachment; filename="document.pdf"',
    'inline; filename=test.pdf',
    'attachment; filename*=UTF-8\'\'surat%20keputusan.pdf'
]

for cd in cds:
    fname_star = re.findall(r"filename\*=UTF-8''([^;]+)", cd, flags=re.IGNORECASE)
    fname_quoted = re.findall(r'filename="([^"]+)"', cd, flags=re.IGNORECASE)
    fname_unquoted = re.findall(r'filename=([^;]+)', cd, flags=re.IGNORECASE)
    
    filename = ""
    if fname_star:
        filename = unquote(fname_star[0])
    elif fname_quoted:
        filename = fname_quoted[0]
    elif fname_unquoted:
        filename = fname_unquoted[0].strip("'\" \t")
    print(f"Header: {cd} \n-> Parsed: {filename}\n")
