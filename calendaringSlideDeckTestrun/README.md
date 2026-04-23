# LinkedIn Calendaring Carousel

Test-run carousel about calendaring for software teams: using calendars as visible boundaries for focus, collaboration, and stakeholder access.

## Output

- `dist/calendaring-linkedin-carousel.pdf` - upload this to LinkedIn as a document post.
- `dist/previews/` - PNG previews generated from the PDF.
- `linkedin-post.txt` - suggested post copy.

## Format Choice

LinkedIn supports document uploads including PDF, PPT/PPTX, DOC/DOCX, ODT, PPSX, and ODS. Documents can be up to 100 MB and 300 pages. For a swipeable carousel, PDF is the safest upload format.

This deck uses a 4:5 portrait layout at `1080 x 1350`, because it takes more vertical space in the mobile feed than square while staying within common LinkedIn carousel guidance.

## Regenerate

```bash
python3 scripts/build_deck.py
magick -density 144 dist/calendaring-linkedin-carousel.pdf -quality 90 dist/previews/slide-%02d.png
```

## Sources Checked

- LinkedIn Help, "Media file types supported on LinkedIn": https://www.linkedin.com/help/linkedin/answer/a564109/media-file-types-supported-on-linkedin
- CarouselMaker, "LinkedIn Carousel Size & Dimensions Guide (2026)": https://carouselmaker.co/en/blog/linkedin-carousel-size-dimensions-guide
