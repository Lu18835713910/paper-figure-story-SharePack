# PDF dependencies for SharePack v1.0.0

SharePack imports pypdfium2 and pypdf at runtime. The Windows test used pypdfium2 5.15.2 with its bundled PDFium binary and pypdf 6.21.4. The pypdfium2 distribution includes wrapper licenses and PDFium/build dependency notices. These are upstream licenses and remain applicable to those components. The candidate SharePack wheel does not contain those dependencies or their binaries. If creating an offline installer, preserve each upstream wheel and all its notices.

The runtime no longer requires PyMuPDF. Certain legacy developer regression fixtures still use it to create historical comparison PDFs. Those fixtures are separate from runtime dependencies.

SharePack software is licensed separately under LICENSE. PFS assets and code retain their separate terms.
