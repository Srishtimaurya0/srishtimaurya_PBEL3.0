import fitz

def extract_text_from_pdf(pdf_file):
    text = ""
    pdf_document = fitz.open(stream=pdf_file.read(), filetype="pdf")
    for page in pdf_document:
        text += page.get_text("text", sort=True)
    pdf_document.close()
    return text


def extract_largest_text(pdf_file):
    """Resume ke pehle page se sabse bade font size wala text dhoondta hai (usually candidate ka naam)."""
    pdf_file.seek(0)  # file pointer ko wapas shuru me le jao
    pdf_document = fitz.open(stream=pdf_file.read(), filetype="pdf")
    page = pdf_document[0]
    blocks = page.get_text("dict")["blocks"]

    max_size = 0
    candidate_text = ""

    for block in blocks:
        if "lines" not in block:
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                text = span["text"].strip()
                if not text:
                    continue
                if span["size"] > max_size and len(text.split()) <= 5:
                    max_size = span["size"]
                    candidate_text = text

    pdf_document.close()
    return candidate_text.strip()
