# -*- coding: utf-8 -*-
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
from docx import Document

desktop = os.path.join(os.environ['USERPROFILE'], 'Desktop')
files = {
    'ANA SÖZLEŞME': os.path.join(desktop, 'Ana Sözleşme (1) (1).docx'),
    'BİYOMETRİK SÖZLEŞME': os.path.join(desktop, 'Biyometrik veri ile ilgili olan (1) (1).docx'),
}

for label, path in files.items():
    print(f'\n{"="*60}')
    print(f'  {label}')
    print(f'{"="*60}')
    try:
        doc = Document(path)
        for para in doc.paragraphs:
            if para.text.strip():
                print(para.text)
    except Exception as e:
        print(f'Hata: {e}')
