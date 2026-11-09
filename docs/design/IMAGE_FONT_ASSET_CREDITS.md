# PWA image and font asset credits

This manifest records the visual assets referenced by the PWA. The destination photographs are documentary photographs from Wikimedia Commons; they are not AI-generated destination depictions.

## Destination photography

| Usage | Subject / source file | Author | License | Source page |
|---|---|---|---|---|
| Home hero | Naqsh-e Jahan Square, Isfahan 02 | Bernard Gagnon | CC BY-SA 4.0 | https://commons.wikimedia.org/wiki/File:Naqsh-e_Jahan_Square,_Isfahan_02.jpg |
| Kashan card | Fin Garden, Kashan, Iran | Amirpashaei | CC BY-SA 4.0 | https://commons.wikimedia.org/wiki/File:Fin_Garden,_Kashan,_Iran.jpg |
| Yazd card | Windcatchers in Yazd | Ms96 | CC BY-SA 4.0 | https://commons.wikimedia.org/wiki/File:Windcatchers_in_Yazd.jpg |
| Qeshm card | Hara forests of Qeshm - 1 | ImanFakhri | CC BY-SA 4.0 | https://commons.wikimedia.org/wiki/File:Hara_forests_of_Qeshm_-_1.jpg |

License: https://creativecommons.org/licenses/by-sa/4.0/

The interface links each visible credit to the relevant Commons file page and shows the author plus CC BY-SA 4.0 license. The source thumbnail was downloaded from the canonical upload.wikimedia.org thumbnail URL and is self-hosted in `frontend/public/images/` as responsive 640px, 960px, and 1280px WebP and AVIF variants. Visible attribution and source links remain attached to each use.

## Typeface

- Family: Estedad Variable
- Fontsource package release: @fontsource-variable/estedad 5.3.0
- Scripts: Arabic/Persian and Latin
- Variable weights: 100–900
- License: SIL Open Font License 1.1
- Typeface project: https://github.com/aminabedi68/Estedad
- Package: https://www.npmjs.com/package/@fontsource-variable/estedad
- Font details: https://fontsource.org/fonts/estedad/about
- License: https://openfontlicense.org/

Estedad Variable 5.3.0's Arabic and Latin WOFF2 subsets and SIL OFL 1.1 license are vendored under `frontend/public/fonts/`; the local subset CSS is `estedad.css`. The runtime jsDelivr dependency has been removed. The font CSS and subsets are included in the service-worker offline asset list.
