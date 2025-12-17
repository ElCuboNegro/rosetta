import sys
from pypdf import PdfReader

try:
    reader = PdfReader(
        r"c:\Users\jalba\OneDrive\Desktop\rosetta\Creación de Diccionario Polisemico_ Metodología Lingüística.pdf"
    )
    print(f"Number of pages: {len(reader.pages)}")

    content = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text:
            content.append(f"--- Page {i + 1} ---\n{text}\n")
        else:
            content.append(f"--- Page {i + 1} ---\n[No text extracted]\n")

    full_text = "\n".join(content)

    with open("methodology_content.txt", "w", encoding="utf-8") as f:
        f.write(full_text)

    print("Extraction complete. Saved to methodology_content.txt")

except Exception as e:
    print(f"Error: {e}")
