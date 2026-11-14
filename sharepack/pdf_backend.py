"""PDFium rendering and pypdf object identity for SharePack.

Reviewed region coordinates are top-left relative to the displayed page,
after PDF rotation and CropBox clipping.
"""
from contextlib import closing
from io import BytesIO
from math import isfinite
from pathlib import Path
from functools import cached_property

import pypdfium2 as pdfium
from pypdf import PdfReader

from .common import ContractError


def valid_clip(box, width, height):
    return (len(box) == 4 and all(type(v) in (int, float) and isfinite(v) for v in box)
            and 0 <= box[0] < box[2] <= width and 0 <= box[1] < box[3] <= height)


class Document:
    def __init__(self, path):
        self.reader = PdfReader(Path(path))
        if self.reader.is_encrypted:
            self.reader.close()
            raise ContractError('PDF_ENCRYPTED')
        try:
            self.document = pdfium.PdfDocument(Path(path))
        except Exception:
            self.reader.close()
            raise

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def close(self):
        self.document.close()
        self.reader.close()

    def __len__(self):
        return len(self.document)

    def __getitem__(self, index):
        if not 0 <= index < len(self):
            raise IndexError(index)
        parsed = self.reader.pages[index]
        if parsed.user_unit != 1:
            raise ContractError('PDF_USER_UNIT_UNSUPPORTED')
        return Page(self.document[index], parsed)


class Page:
    def __init__(self, page, parsed):
        self.page = page
        self.parsed = parsed
        self.width, self.height = page.get_size()

    @cached_property
    def text(self):
        with closing(self.page.get_textpage()) as text:
            return text.get_text_range().replace('\r\n', '\n').replace('\ufffe', '-')

    @cached_property
    def displayed_images(self):
        images = self.parsed.images
        displayed = {}
        for key in images.keys():
            if not isinstance(key, str):
                continue
            image = images[key]
            if image.indirect_reference is not None and image.is_displayed:
                displayed[image.indirect_reference.idnum] = image
        return displayed

    def png(self, scale, clip=None, width=None):
        crop = (0, 0, 0, 0)
        if clip is not None:
            if not valid_clip(clip, self.width, self.height):
                raise ContractError('CROP_OUTSIDE_PDF')
            x0, y0, x1, y1 = clip
            crop = (x0, self.height-y1, self.width-x1, y0)
        with closing(self.page.render(scale=scale, crop=crop)) as bitmap:
            image = bitmap.to_pil()
            with BytesIO() as output:
                if width is not None and image.width != width:
                    from PIL import Image
                    image = image.resize((width, round(image.height*width/image.width)), Image.Resampling.LANCZOS)
                image.save(output, format='PNG')
                return output.getvalue()
