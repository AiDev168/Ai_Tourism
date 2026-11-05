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

The interface links each visible credit to the relevant Commons file page and shows the author plus license. Images currently load from the canonical upload.wikimedia.org thumbnail host at 1280px. Before public production deployment, vendor optimized same-origin WebP/AVIF versions and preserve all compatible attribution/license metadata.

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

The current refresh loads the version-pinned variable-weight stylesheet from jsDelivr. Before production sign-off, add the package to frontend/package.json, regenerate package-lock.json, import its CSS through the Vite entry point and serve WOFF2 files from the app origin. This removes third-party runtime font dependence and makes offline caching explicit.
