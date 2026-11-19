import os

from config import MAX_FILE_MB


def allowed(filename):
    ext = os.path.splitext(filename)[1].lower()
    return ext in {".txt", ".md", ".csv", ".log", ".json", ".pdf", ".docx"}


def extract(path, filename):
    ext = os.path.splitext(filename)[1].lower()
    try:
        if ext == ".pdf":
            from pypdf import PdfReader

            reader = PdfReader(path)
            return "\n".join((p.extract_text() or "") for p in reader.pages[:60])
        if ext == ".docx":
            from docx import Document

            doc = Document(path)
            return "\n".join(p.text for p in doc.paragraphs[:2000])
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read(400000)
    except Exception as exc:
        return f"[Dosya okunamadı: {exc}]"


def check_size(data):
    if len(data) > MAX_FILE_MB * 1024 * 1024:
        raise ValueError(f"Dosya en fazla {MAX_FILE_MB} MB olabilir.")
    return data


def relevant_context(texts, query, max_chunks=2, chunk_size=1600):
    """Basit anahtar kelime skorlamasıyla en ilgili parçaları seçer."""
    words = [w.lower() for w in query.split() if len(w) > 2][:12]
    if not words or not texts:
        return ""
    scored = []
    for rec in texts:
        text = rec.get("text") or ""
        low = text.lower()
        for i in range(0, len(text), chunk_size):
            chunk = text[i : i + chunk_size]
            score = sum(1 for w in words if w in chunk.lower())
            if score:
                scored.append((score, rec["filename"], chunk))
    if not scored:
        return ""
    scored.sort(key=lambda x: x[0], reverse=True)
    parts = [f"[Dosya: {name}]\n{chunk}" for _, name, chunk in scored[:max_chunks]]
    return "\n\n".join(parts)
