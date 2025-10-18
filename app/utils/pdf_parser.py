import PyPDF2

def extract_text_from_pdf(pdf_path):
    """
    Extracts text from a given PDF file.
    """
    text = ""
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                text += page.extract_text() or "" # Handle potential None for empty pages
    except Exception as e:
        print(f"Error reading PDF {pdf_path}: {e}")
        return None
    return text