"""Original synthetic PDF fixtures built with installed pypdf and Pillow, not fitz.

The test-only writer creates RGB image XObjects and Helvetica captions.
Returned XObject IDs are stable and usable for source-binding regression tests.
"""
from io import BytesIO
from pathlib import Path

from PIL import Image
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject, NumberObject


def make_synthetic_pdf(path, *, images=(), captions=()):
    """Write a PDF; return the image XObject numbers in insertion order.

    images: sequence of (encoded PNG bytes, (x, y, width, height)) in PDF points.
    If supplied, the image page is physical page 1; captions follow.
    """
    writer = PdfWriter()
    xrefs = []
    if images:
        page = writer.add_blank_page(width=612, height=792)
        resources = page["/Resources"].get_object()
        resources[NameObject("/XObject")] = DictionaryObject()
        xobjects = resources["/XObject"]
        operations = []
        for i, (encoded, (x, y, width, height)) in enumerate(images):
            with Image.open(BytesIO(encoded)) as original:
                rgb = original.convert("RGB")
                image_stream = DecodedStreamObject()
                image_stream.set_data(rgb.tobytes())
                image_stream.update({
                    NameObject("/Type"): NameObject("/XObject"),
                    NameObject("/Subtype"): NameObject("/Image"),
                    NameObject("/Width"): NumberObject(rgb.width),
                    NameObject("/Height"): NumberObject(rgb.height),
                    NameObject("/ColorSpace"): NameObject("/DeviceRGB"),
                    NameObject("/BitsPerComponent"): NumberObject(8),
                })
            ref = writer._add_object(image_stream)
            xrefs.append(ref.idnum)
            name = NameObject("/TestImage%d" % i)
            xobjects[name] = ref
            operations.append("q %s 0 0 %s %s %s cm %s Do Q" % (
                width, height, x, y, name))
        contents = DecodedStreamObject()
        contents.set_data(("\n".join(operations) + "\n").encode("ascii"))
        page[NameObject("/Contents")] = writer._add_object(contents)
    if captions:
        font = writer._add_object(DictionaryObject({
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }))
        for caption in captions:
            page = writer.add_blank_page(width=612, height=792)
            page["/Resources"][NameObject("/Font")] = DictionaryObject({
                NameObject("/F1"): font,
            })
            safe = caption.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            contents = DecodedStreamObject()
            contents.set_data(
                ("BT /F1 14 Tf 60 700 Td (%s) Tj ET" % safe).encode("latin-1"))
            page[NameObject("/Contents")] = writer._add_object(contents)
    if not images and not captions:
        writer.add_blank_page(width=612, height=792)
    writer.write(Path(path))
    return xrefs
