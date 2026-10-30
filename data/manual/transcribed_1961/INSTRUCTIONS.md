# Transcription instructions for the 1961 commentary edition

Book: தொல்காப்பியம் with a Tamil commentary (தெளிவுரை), 1961, scan TVA_BOK_0044874.
Images: data/work/scan_1961/png/p-NNN-s1.png, -s2.png, -s3.png (three horizontal strips
of page NNN, top to bottom, overlapping by about 80 px; a line at the bottom of one
strip may reappear at the top of the next: transcribe it once). The whole page is
p-NNN.png if layout is unclear, but read the text from the strips.
Output: data/manual/transcribed_1961/p-NNN.txt, one file per page.

## Page layout
A sutra starts with a title line (italic, sometimes with a number prefix), then the
indented poem lines, with the sutra number printed at the right end of the poem's
last line, then the commentary in italic justified text. Some sutras have no title.
Larger centred headings (e.g. "பொருள் அதிகாரம்", "5. மயக்கம்") are chapter/section
headings, not titles.

## Markers (one per line)
  @heading <text>     chapter/section heading
  @title <text>       sutra title exactly as printed, including any number prefix
  @poem               poem lines follow, one printed line per output line, without the number
  @num <n>            the sutra number at the right of the poem's last line (Western digits)
  @commentary         commentary follows, one paragraph per output line: join a paragraph's
                      printed lines with one space; join a word broken across lines without a space
  @cont               first marker on a page that starts in the middle of a commentary or poem
                      continued from the previous page; the continued text follows directly
                      (if the previous page ended right after a poem's number, start the page
                      with @commentary instead)
                      If a word is split by the page break, end the earlier page with the
                      fragment followed by a hyphen, e.g. "அவற்-"; the next page's @cont
                      text starts with the rest ("றிற்கு").
  @blank              the page has no book text (blank, plate, or only a heading-free ornament)
Skip running headers ("தொல்காப்பியம் தெளிவுரை", "பொருள் அதிகாரம்   255" and the like),
page numbers and signature marks at the foot ("தொ—2").

## Transcription rules
- Transcribe exactly what is printed: the 1961 spellings, word spacing and sandhi
  splits as printed (e.g. "எழுத்தெனப் படுப", "முப்பஃ தென்ப;"), all punctuation.
- Old letter forms become modern Unicode. In particular the pre-1978 ligatures for
  ணா, னா, றா look like ணு/னு/று with a loop; decide from the word (பனம்பாரனார்,
  மூன்றாகும், என்மனார், கூறினான்), and keep ணு/னு/று where that is the real letter.
  Old ணை, லை, னை, ளை glyphs become ணை, லை, னை, ளை.
- Do not correct, modernise or complete anything from your own knowledge of
  Tholkappiyam or Tamil; this edition's readings differ from others in places.
- Keep obvious misprints too (e.g. "வருதல" for வருதல், "மெலலெழுத்து"): transcribe
  them as printed and add ⟨sic⟩ right after the word. Never fix them silently.
- Genuinely illegible letters or words: best reading followed by ⟨?⟩. Never invent text.
- Unicode NFC, nothing but transcription inside the files.
