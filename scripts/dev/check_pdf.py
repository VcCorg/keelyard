#!/usr/bin/env python3
import PyPDF2
from pathlib import Path

pdf_path = Path.home() / 'Downloads' / 'CWOW-279647 Manage HDF Treatment Standards USA_1.0.pdf'

try:
    with open(pdf_path, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        print(f'Total pages: {len(reader.pages)}')
        
        # Try to extract text from first few pages
        for i in range(min(3, len(reader.pages))):
            page = reader.pages[i]
            text = page.extract_text()
            print(f'\n--- Page {i+1} ---')
            print(f'Text length: {len(text)}')
            print(f'First 500 chars: {text[:500] if text else "(no text)"}')
            
        # Check for images in the PDF
        print(f'\n--- Checking for images ---')
        for i in range(min(3, len(reader.pages))):
            page = reader.pages[i]
            if '/Resources' in page:
                resources = page['/Resources']
                if '/XObject' in resources:
                    xobjects = resources['/XObject']
                    image_count = 0
                    for obj in xobjects.values():
                        if '/Subtype' in obj and obj['/Subtype'] == '/Image':
                            image_count += 1
                    if image_count > 0:
                        print(f'Page {i+1}: {image_count} image(s) found')
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
