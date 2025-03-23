# Audiobookshelf Calibre Plugin

A calibre plugin to synchronize metadata from Audiobookshelf to calibre.

## Features

- Sync metadata from Audiobookshelf to Calibre
- View reading progress from Audiobookshelf
- Schedule automatic syncs
- Quick link multiple books based on ISBN/ASIN matching

## Installation

1. Go to your calibre's _Preferences_ > _Plugins_ > _Get new plugins_ and search
   for _Audiobookshelf Sync_
2. Click _Install_
3. Restart calibre

### Manual Installation

1. Download the latest release from the releases page
2. In Calibre, go to Preferences -> Plugins
3. Click "Load plugin from file" and select the downloaded zip file
4. Restart Calibre

## Setup

Pick and choose the metadata you would like to sync and create the
appropriate columns in calibre. The plugin makes this easy, simply select
the **create new columns** option in the config dropdowns.

1. Right click the Audiobookshelf icon and click configure
2. Click "Add Audiobookshelf Account" and enter your Audiobookshelf server details:
   - Server URL (default: http://localhost:13378)
   - API Key
   - Optionally set up scheduled sync
3. Configure columns and scheduled sync settings

### Available Columns

| Column | Description | Type |
|--------|-------------|------|
| Audiobook Size | Size of the audiobook in MB (formatted with commas as thousands separators) | Text |
| Audiobook Duration | Duration of the audiobook formatted as Hrs:Min | Text |
| Audiobook Subtitle | Subtitle of the audio/book | Text |
| Audiobook Narrator | Narrator name(s) | Text |
| Audiobook Publisher | Publisher of the audiobook | Text |
| Audiobook Abridged | Indicates if the audiobook is abridged | Yes/No |
| Audiobook File Count | Number of files that comprise the audiobook | Number |
| Audiobook Chapters | Number of chapters in the audiobook | Number |
| Audiobook Precise Progress | Progress percentage with decimal precision | Number |
| Audiobook Progress | Progress percentage as a whole number | Number |
| Audiobook Progress Time | Current audiobook progress time formatted as Hrs:Min | Text |
| Audiobook Started? | Indicates if the audiobook has been started | Yes/No |
| Audiobook Finished? | Indicates if the audiobook has been finished | Yes/No |
| Audiobook Last Read Date | The last date the audiobook was read | Date |
| Audiobook Begin Date | The date when the audiobook reading began | Date |
| Audiobook Finish Date | The date when the audiobook was finished | Date |
| Audiobook Bookmarks | Bookmarks in the format 'title at time' (time as hh:mm:ss) | Text |

## Usage

### Sync

1. Click the Audiobookshelf icon or right-click and select "Sync from Audiobookshelf"

### Quick Link Books

1. Right-click the Audiobookshelf icon and select "Quick Link Books"
2. Books will be automatically linked based on ISBN/ASIN matches

### Manual Linking

1. Select books in your Calibre library
2. Right-click the Audiobookshelf icon and select "Link Audiobookshelf Book"
3. Select the matching book from your Audiobookshelf library
   Matched titles/authors will be highlighted and shown at the top for easier identification, a reading progress indicator will show which books you've started.

### Scheduled Sync

Enable scheduled sync in the plugin configuration to automatically sync metadata at a specified time once a day.

## Support

For issues, questions, or contributions, please visit the [GitHub repository](https://github.com/jbhul/Audiobookshelf-calibre-plugin/issues).

## Acknowledgements

- The wonderful dev of [Audiobookshelf](https://github.com/advplyr/audiobookshelf)
  for making a wonderful program with an amazing API.
- Some code borrowed from--and heavily inspired by--the
  great [KOReader Sync](https://github.com/harmtemolder/koreader-calibre-plugin)
  calibre plugin.
- Some code borrowed from--and heavily inspired by--the
  great [Goodreads Sync](https://www.mobileread.com/forums/showthread.php?t=123281)
  calibre plugin.
