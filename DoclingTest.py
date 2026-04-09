from docling.document_converter import DocumentConverter

source = "./test_split/test_1.pdf"  # file path or URL
converter = DocumentConverter()
doc = converter.convert(source).document

print(doc.export_to_markdown())  # output: "### Docling Technical Report[...]"