# Credits and data provenance

VAIS analyzes public-domain source material assembled and transcribed by
others. This project exists because of their work, and redistributes it
here solely for research reproducibility, with attribution. If you are a
rights holder or maintainer of any item below and want a correction,
additional credit, or removal, please open an issue on
[the repository](https://github.com/Vineyardcode/vais) — it will be
honored promptly.

## Manuscript transliterations

All transliteration files are used and redistributed courtesy of
**René Zandbergen** ([voynich.nu](https://www.voynich.nu)), who maintains
them in the IVTFF format, and of the transcribers who created them:

| file(s) | transliteration | transcriber(s) |
|---|---|---|
| `folios/*.txt` | ZL (IVTFF) | René Zandbergen & Gabriel Landini |
| `data/translit/CD2a-n.txt` | C-D | Prescott Currier, Mary D'Imperio et al. |
| `data/translit/FG2a-n.txt` | FSG | Friedman First Study Group (1940s) |
| `data/translit/GC2a-n.txt` | v101 | Glen Claston (Tim Rayhel) |
| `data/translit/IT2a-n.txt` | IT | Takeshi Takahashi |

The underlying manuscript text (Beinecke MS 408, 15th century) is in the
public domain.

## Folio images

`folios/*.png` derive from the digitization of Beinecke MS 408 by the
**Beinecke Rare Book & Manuscript Library, Yale University**, which makes
images of its public-domain materials freely available. The images are
not included in the website's data pack.

## Reference texts

Latin, Italian, Occitan, and Gascon reference corpora come from
**Project Gutenberg** (public-domain texts; cached copies in
`data/gutenberg_cache/` retain the Project Gutenberg headers and are
redistributed free of charge in accordance with the Project Gutenberg
License) and other public-domain sources. Notable items: Dante's
Commedia (PG 1012), Mistral's *Lou Pouèmo dóu Rose* (PG 37854), Ader's
*Lou catounet gascoun* (PG 17544), Caesar's *De Bello Gallico*.

## Research context

The research program engages published work by (among others) Prescott
Currier, Jorge Stolfi, Gordon Rugg, Torsten Timm & Andreas Schinner,
Stephen Bax, Nick Pelling, Massimiliano Zattera, Christophe Parisel,
Lisa Fagin Davis, and the [voynich.ninja](https://www.voynich.ninja)
community. Citations and discussion are in [RESEARCH.md](RESEARCH.md);
critiques there concern published claims and methods, in the ordinary
course of scholarly discourse.

## Software

The in-browser runner uses **Pyodide** (Mozilla Public License 2.0,
loaded from its public CDN, not redistributed here), **NumPy**, and
**Flask**. The code in this repository is MIT-licensed — see
[LICENSE](LICENSE), including its scope note for the data listed above.
