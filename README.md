# Audiobookshelf Calibre Plugin

A calibre plugin to synchronize metadata from Audiobookshelf to calibre.

## Features

- Sync metadata from Audiobookshelf to Calibre
- Sync back changes from Calibre to Audiobookshelf
- View reading progress from Audiobookshelf
- Schedule automatic syncs
- Quick link multiple books based on ASIN matching

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
   - [API Key](https://api.audiobookshelf.org/#introduction:~:text=You%20can%20find%20your%20API%20token%20by%20logging%20into%20the%20Audiobookshelf%20web%20app%20as%20an%20admin%2C%20go%20to%20the%20config%20%E2%86%92%20users%20page%2C%20and%20click%20on%20your%20account.)
   - Optionally set up scheduled sync
3. Configure columns and other settings
4. Link Books and Sync

### Available Columns
<details>
<summary>See Columns</summary>

| Column                       | Description                                                   | Type         |
|------------------------------|---------------------------------------------------------------|--------------|
| Audiobook Title*             | Title of the audiobook                                        | Text         |
| Audiobook Subtitle*          | Subtitle of the audiobook                                     | Text         |
| Audiobook Description*       | Description of the audiobook                                  | Comments     |
| Audiobook Author*            | Author name(s)                                                | Text (Names) |
| Audiobook Narrator*          | Narrator name(s)                                              | Text (Names) |
| Audiobook Series*            | Series of the audiobook                                       | Series       |
| Audiobook Language*          | Language of the audiobook                                     | Text         |
| Audiobook Genres*            | Genres tagged for the audiobook                               | Text (Tags)  |
| Audiobook Tags*              | Tags associated with the audiobook                            | Text (Tags)  |
| Audiobook Publisher*         | Publisher of the audiobook                                    | Text         |
| Audiobook Publish Year*      | Year the audiobook was published                              | Integer      |
| Audiobook Abridged*          | Indicates if the audiobook is abridged                        | Yes/No       |
| Audiobook Explicit*          | Indicates if the audiobook is explicit                        | Yes/No       |
||||
| Audiobook Size               | Size of the audiobook in MB                                   | Text         |
| Audiobook File Count         | Number of files that comprise the audiobook                   | Integer      |
| Audiobook Chapters           | Number of chapters in the audiobook                           | Integer      |
||||
| Audiobookshelf Library       | Audiobookshelf Library the audiobook is located in            | Text         |
| Audiobookshelf Date Added    | The date the audiobook was added to Audiobookshelf            | Date         |
| Audiobookshelf Full Path     | Full path to the audiobook                                    | Text         |
| Audiobookshelf Relative Path | Relative Path of the audiobook                                | Text         |
||||
| Audiobook Last Read Date     | The last date the audiobook was read                          | Date         |
| Audiobook Precise Progress   | Progress percentage with decimal precision                    | Float        |
| Audiobook Progress           | Progress percentage as a whole number                         | Integer      |
| Audiobook Progress Time      | Current audiobook progress time formatted as Hrs:Min          | Text         |
| Audiobook Duration           | Duration of the audiobook formatted as Hrs:Min                | Text         |
||||
| Audiobook Started?           | Indicates if the audiobook has been started                   | Yes/No       |
| Audiobook Begin Date         | The date when the audiobook reading began                     | Date         |
||||
| Audiobook Finished?          | Indicates if the audiobook has been finished                  | Yes/No       |
| Audiobook Finish Date        | The date when the audiobook was finished                      | Date         |
||||
| Audiobook Bookmarks          | Bookmarks in the format 'title at time' (time as hh:mm:ss)    | Comments     |
| Audiobook Collections*       | Collections and Playlists associated with the audiobook       | Text (Tags)  |
||||
| Audible Average Rating       | Average Overall Rating from Audible with Half Stars           | Rating       |
| Audible Average Performance Rating | Average Performance Rating from Audible with Half Stars | Rating       |
| Audible Average Story Rating | Average Story Rating from Audible with Half Stars             | Rating       |
| Audible Rating Count         | Number of (star) ratings on Audible (overall ratings)         | Integer      |
| Audible Review Count         | Number of (text) reviews on Audible                           | Integer      |
</details>

## Usage

### Sync

Click the Audiobookshelf icon in the toolbar or right-click and select "Sync from Audiobookshelf"

#### Scheduled Sync

Set and Forget!  
Enable scheduled sync in the plugin configuration to automatically sync metadata at a specified time once a day.

### Linking Books

1. Select books in your Calibre library
2. Right-click the Audiobookshelf icon and select "Link Audiobookshelf Book"
3. Select the matching book from your Audiobookshelf library
   Matched titles/authors will be highlighted and shown at the top for easier identification, a reading progress indicator will show which books you've started.

#### Quick Link Books

Quick Linking attempts to link books that haven't been linked by matching up Audiobookshelf ASIN (Audible ASIN).  
It searches Audible for a list of Audible ASINs that may match the title and author of the calibre book, and then
checks if any Audiobookshelf book matches.  
By default QuickLink saves a list of calibre books it failed to match (due to no ASIN match) which is more time and API efficient.

1. Right-click the Audiobookshelf icon and select "Quick Link Books"
2. Books will be automatically linked based on Audible ASIN matches

### Audiobooks Not in Calibre

Builds a table of audiobooks in Audiobookshelf that aren't linked to a book in calibre.  
Double click the title to open the book in Audiobookshelf.

### Audible ASIN Sync

Sync over the Audible ASIN from Audiobookshelf which adds a link to the Audible page straight from calibre.

### Writeback

This plugin allows calibre to push metadata back to Audiobookshelf when changed inside of calibre.  
Any of the columns with a * are able to be easily sync'd back to Audiobookshelf.  
This feature is offered with the disclaimer that this will edit your Audiobooshelf database.
Make sure you have Audiobookshelf backups enabled in case this borks anything up, which it shouldn't but you never know.  
For Collections/Playlists, this plugin will not create new ones, only update existing.

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
