#!/usr/bin/env python3
"""Audiobookshelf Sync plugin for calibre"""

import json
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import urllib.parse

from PyQt5.Qt import (
    QDialog,
    QIcon,
    QPushButton,
    QLabel,
    QHBoxLayout,
    QVBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QScrollArea,
    QUrl,
    QTimer,
    QTime,
    QColor,
    QApplication,
    Qt,
)
from PyQt5.QtGui import QPixmap

from calibre.gui2.actions import InterfaceAction
from calibre.gui2.dialogs.message_box import MessageBox
from calibre.db.listeners import EventType
from calibre.utils.config import JSONConfig
from calibre.gui2 import (
    error_dialog,
    warning_dialog,
    info_dialog,
    open_url,
)

from calibre_plugins.audiobookshelf.config import CONFIG, CUSTOM_COLUMN_DEFAULTS as COLUMNS
from calibre_plugins.audiobookshelf import DEBUG

__license__ = 'GNU GPLv3'
__copyright__ = '2025, jbhul'

# Helper functions to show error and info messages using MessageBox
def show_error(gui, title, message):
    MessageBox(MessageBox.ERROR, title, message, parent=gui).exec_()

def show_info(gui, title, message):
    MessageBox(MessageBox.INFO, title, message, parent=gui).exec_()

class AudiobookshelfAction(InterfaceAction):
    name = "Audiobookshelf"
    action_spec = (name, 'diff.png', 'Get metadata from Audiobookshelf', None)
    action_add_menu = True
    action_menu_clone_qaction = 'Sync from Audiobookshelf'
    dont_add_to = frozenset([
        'context-menu', 'context-menu-device', 'toolbar-child',
        'menubar', 'menubar-device', 'context-menu-cover-browser', 
        'context-menu-split'
    ])
    dont_remove_from = InterfaceAction.all_locations - dont_add_to
    action_type = 'current'
    Syncing = False

    def genesis(self):
        base = self.interface_action_base_plugin
        self.version = f'{base.name} (v{".".join(map(str, base.version))})'
        # Set up toolbar button icon and left-click action
        icon = get_icons('images/abs_icon.png')
        self.qaction.setIcon(icon)
        self.qaction.triggered.connect(self.sync_from_audiobookshelf)
        # Right-click menu (already includes left-click action)
        menu = self.qaction.menu()
        menu.addSeparator()
        self.create_menu_action(
            menu,
            'Link Audiobookshelf Book',
            'Link Audiobookshelf Book',
            icon='insert-link.png',
            triggered=self.link_audiobookshelf_book,
            description=''
        )
        self.create_menu_action(
            menu,
            'Quick Link Books',
            'Quick Link Books',
            icon='wizard.png',
            triggered=self.quick_link_books,
            description=''
        )
        menu.addSeparator()
        self.create_menu_action(
            menu,
            'Audiobooks Not In Calibre',
            'Audiobooks Not In Calibre',
            icon='format-list-ordered.png',
            triggered=self.show_not_in_calibre,
            description='List of Audiobooks Not In Calibre'
        )
        menu.addSeparator()
        self.create_menu_action(
            menu,
            'Configure',
            'Configure',
            icon='config.png',
            triggered=self.show_config,
            description=''
        )
        menu.addSeparator()
        self.create_menu_action(
            menu,
            'Readme',
            'Readme',
            icon='dialog_question.png',
            triggered=self.show_readme,
            description=''
        )
        self.create_menu_action(
            menu,
            'About',
            'About',
            icon='dialog_information.png',
            triggered=self.show_about,
            description=''
        )
        
        # Start scheduled sync if enabled
        if CONFIG.get('checkbox_enable_scheduled_sync', False):
            self.scheduled_sync()
        
        # Start writeback watcher if enabled
        if CONFIG.get('checkbox_enable_writeback', False):
            watched_columns = {}
            for config_name, col_meta in COLUMNS.items():
                if '*' in col_meta['config_label'] and CONFIG.get(config_name):
                    watched_columns[CONFIG.get(config_name)] = col_meta['data_location'][-1]
            self.watcher(watched_columns)

    def show_config(self):
        self.interface_action_base_plugin.do_user_config(self.gui)

    def show_readme(self):
        open_url(QUrl('https://github.com/jbhul/Audiobookshelf-calibre-plugin#readme'))

    def show_about(self):
        text = get_resources('about.txt').decode('utf-8')
        if DEBUG:
            text += '\n\nRunning in debug mode'
        icon = get_icons('images/abs_icon.png')
        about_dialog = MessageBox(
            MessageBox.INFO,
            f'About {self.version}',
            text,
            det_msg='',
            q_icon=icon,
            show_copy_button=False,
            parent=None,
        )
        return about_dialog.exec_()

    def show_not_in_calibre(self):
        abs_items = self.get_abs_library_items()
        if abs_items is None:
            return

        # Get all linked ABS IDs from Calibre
        db = self.gui.current_db.new_api
        all_book_ids = db.search('identifiers:"=audiobookshelf_id:"')
        linked_abs_ids = set()
        
        for book_id in all_book_ids:
            metadata = db.get_metadata(book_id)
            identifiers = metadata.get('identifiers', {})
            linked_abs_ids.add(identifiers['audiobookshelf_id'])

        # Filter and sort unlinked items
        unlinked_items = []
        for item in abs_items:
            if item.get('id') not in linked_abs_ids:
                metadata = item.get('media', {}).get('metadata', {})
                title = metadata.get('title', '')
                author = metadata.get('authorName', '')
                if title:  # Only include items with titles
                    unlinked_items.append({
                        'title': title,
                        'author': author
                    })

        # Sort by title
        unlinked_items.sort(key=lambda x: x['title'].lower())

        # Show results
        message = f"Found {len(unlinked_items)} unlinked books in Audiobookshelf library"
        SyncCompletionDialog(self.gui, "Unlinked Audiobookshelf Books", message, unlinked_items, type="info").exec_()

    def scheduled_sync(self):
        def scheduledTask():
            QTimer.singleShot(24 * 3600 * 1000, scheduledTask)
            self.sync_from_audiobookshelf(silent = True if not DEBUG else False)
        def main():
            currentTime = QTime.currentTime()
            targetTime = QTime(CONFIG.get('scheduleSyncHour', 4), CONFIG.get('scheduleSyncMinute', 0))
            timeDiff = currentTime.msecsTo(targetTime)
            if timeDiff < 0:
                timeDiff += 86400000
            QTimer.singleShot(timeDiff, scheduledTask)
        main()

    def watcher(self, watched_columns):
        """Watch specified columns for changes and sync back to Audiobookshelf"""
        if not hasattr(self.gui, 'current_db'):
            print("Database not yet initialized, delaying watcher setup")
            QTimer.singleShot(1000, lambda: self.watcher(watched_columns))
            return

        def event_listener(db, event_type, event_data):
            if not self.Syncing and event_type == EventType.metadata_changed:
                print(event_data)
                field, book_ids = event_data
                if field.endswith('_index'):
                    field = field[:-6]
                # Only process if the changed field is one we're watching
                if field in watched_columns:
                    for book_id in book_ids:
                        metadata = db.get_metadata(book_id, index_is_id=True)
                        abs_id = metadata.get('identifiers', '').get('audiobookshelf_id', '')
                        if not abs_id:
                            continue
                        new_value = metadata.get(field)
                        if watched_columns[field] == 'collections':
                            collections_dict, collections_map = self.get_abs_collections(server_url, api_key)
                            server_collections = collections_dict.get(abs_id, [])
                            for collection in server_collections:
                                if collection not in new_value: # Item in Server but not local, therefore remove from server
                                    collection_id = collections_map.get(collection, None)
                                    if collection_id:
                                        if collection[0:3] == "PL ": # Playlist
                                            self.api_request(f"{server_url}/api/playlists/{collection_id}/batch/remove", api_key, ('POST', {"items": [abs_id]}))
                                        else: # Collection
                                            self.api_request(f"{server_url}/api/collections/{collection_id}/batch/remove", api_key, ('POST', {"books": [abs_id]}))
                            for collection in new_value:
                                if collection not in server_collections: # Item not in server but in local, therefore add to server
                                    collection_id = collections_map.get(collection, None)
                                    if collection_id:
                                        if collection[0:3] == 'PL ': # Playlist
                                            self.api_request(f"{server_url}/api/playlists/{collection_id}/batch/add", api_key, ('POST', {"items": [{"libraryItemId": abs_id}]}))
                                        else: # Collection
                                            self.api_request(f"{server_url}/api/collections/{collection_id}/batch/add", api_key, ('POST', {"books": [abs_id]}))
                        else:
                            if watched_columns[field].startswith('series'):
                                body = {"metadata": {'series': [{
                                    "name": new_value,
                                    "sequence": str(int(metadata.get(f'{field}_index', 1)))
                                    }]
                                }}
                            elif watched_columns[field] == 'authorName':
                                body = {"metadata": {'authors': [{"name": author} for author in new_value]}}
                            elif watched_columns[field] == 'narratorName':
                                body = {"metadata": {'narrators': new_value}}
                            elif watched_columns[field] == 'tags':
                                body = {"tags": new_value}
                            else:
                                body = {"metadata": {watched_columns[field]: new_value}}
                            self.api_request(f"{server_url}/api/items/{abs_id}/media", api_key, ('PATCH', body))

        server_url = CONFIG.get('abs_url', 'http://localhost:13378')
        api_key = CONFIG.get('abs_key', '')
        self.gui.add_db_listener(event_listener)

    def update_metadata(self, book_uuid, keys_values_to_update):
        db = self.gui.current_db.new_api
        try:
            book_id = db.lookup_by_uuid(book_uuid)
        except Exception:
            return False, {'error': f"Book not found: {book_uuid}"}
        if not book_id:
            return False, {'error': f"Book not found: {book_uuid}"}
        metadata = db.get_metadata(book_id)
        updates = []
        for key, new_value in keys_values_to_update.items():
            if isinstance(new_value, tuple):
                metadata.set(key, new_value[0], extra=new_value[1])
            else:
                metadata.set(key, new_value)
            updates.append(key)
        if updates:
            db.set_metadata(book_id, metadata, set_title=False, set_authors=False)
        return True, {'updated': updates, 'book_id': book_id}

    def get_nested_value(self, data, path):
        for key in path:
            if data is None:
                return None
            if isinstance(data, dict):
                data = data.get(key)
            else:
                return None
        return data

    def api_request(self, url, api_key, body=None):
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }
        req = Request(url, headers=headers)
        if body is not None:
            req.method = body[0]
            req.data = json.dumps(body[1]).encode("utf-8")
        try:
            with urlopen(req, timeout=20) as response:
                resp_data = response.read()
                return json.loads(resp_data.decode('utf-8'))
        except (HTTPError, URLError):
            print("API request failed")
            return None

    def sync_from_audiobookshelf(self, silent=False):
        self.Syncing = True
        server_url = CONFIG.get('abs_url', 'http://localhost:13378')
        api_key = CONFIG.get('abs_key', '')
        
        items_list = self.get_abs_library_items()
        if items_list is None:
            return
        # Build dictionary mapping item id to item data (from lib_items)
        items_dict = {}
        for item in items_list:
            item_id = item.get('id')
            if item_id:
                items_dict[item_id] = item

        # Get me data
        me_url = f"{server_url}/api/me"
        me_data = self.api_request(me_url, api_key)
        if me_data is None:
            show_error(self.gui, "API Error", "Failed to retrieve Audiobookshelf user data.")
            return
        # Build dictionary mapping libraryItemId to media progress data (from mediaProgress)
        media_progress_dict = {}
        for prog in me_data.get('mediaProgress', []):
            media_progress_dict[prog.get('libraryItemId')] = {**prog, 'bookmarks': []}
        for bookmark in me_data.get('bookmarks'):
            media_progress_dict[bookmark["libraryItemId"]]['bookmarks'].append({
                "title": bookmark["title"],
                "time": bookmark["time"],
            })

        # Get collection/playlist data
        if CONFIG.get('column_audiobook_collections'):
            collections_dict = self.get_abs_collections(server_url, api_key)[0]

        db = self.gui.current_db.new_api
        all_book_ids = db.search('identifiers:"=audiobookshelf_id:"')
        num_success = 0
        num_fail = 0
        num_skip = 0
        results = []

        for book_id in all_book_ids:
            metadata = db.get_metadata(book_id)
            book_uuid = metadata.get('uuid')
            identifiers = metadata.get('identifiers', {})
            abs_id = identifiers.get('audiobookshelf_id')
            item_data = items_dict.get(abs_id)
            if not item_data:
                results.append({'title': metadata.get('title', f'Book {book_id}'), 'error': 'Audiobookshelf item not found'})
                num_skip += 1
                continue
            progress_data = media_progress_dict.get(abs_id, {})

            result = {'title': metadata.get('title', f'Book {book_id}')}
            keys_values_to_update = {}

            # Update identifiers if Audible ASIN sync is enabled
            if CONFIG.get('checkbox_enable_Audible_ASIN_sync', False):
                current_Audible_ASIN = identifiers.get('audible')
                Audible_ASIN = item_data.get('media').get('metadata').get('asin')
                if Audible_ASIN != current_Audible_ASIN:
                    identifiers['audible'] = Audible_ASIN
                    keys_values_to_update['identifiers'] = identifiers
            
            # For each custom column, use api_source and data_location for lookup
            for config_name, col_meta in COLUMNS.items():
                column_name = CONFIG.get(config_name, '')
                if not column_name:  # Skip if column not configured
                    continue
                
                data_location = col_meta.get('data_location', [])
                api_source = col_meta.get('api_source', '')
                value = None
                
                if api_source == "mediaProgress":
                    value = self.get_nested_value(progress_data, data_location)
                    if col_meta['column_heading'] == "Audiobook Started" and value is None:
                        value = True
                elif api_source == "lib_items":
                    value = self.get_nested_value(item_data, data_location)
                elif api_source == "collections":
                    value = collections_dict.get(abs_id, [])
                
                if value is not None:
                    if 'transform' in col_meta and callable(col_meta['transform']):
                        value = col_meta['transform'](value)
                    if value is not None:
                        old_value = metadata.get(column_name)
                        if type(old_value) != type(value):
                            # Convert value to the same type as old_value
                            if isinstance(old_value, str) and isinstance(value, list):
                                value = ', '.join(value)
                            elif col_meta['datatype'] == 'series':
                                if old_value == value[0] and metadata.get(f'{column_name}_index') == value[1]:
                                    value = old_value
                            elif isinstance(old_value, bool):
                                value = bool(value)
                            elif isinstance(old_value, int):
                                value = int(value)
                            elif isinstance(old_value, float):
                                value = float(value)
                            else: # Default to string
                                value = str(value)
                        if old_value != value:
                            keys_values_to_update[column_name] = value
                            # Only add to result if there's an actual change
                            result[col_meta['column_heading']] = f"{old_value if old_value is not None else '-'} >> {value}"

            if keys_values_to_update:
                status, detail = self.update_metadata(book_uuid, keys_values_to_update)
                if status:
                    num_success += 1
                else:
                    num_fail += 1
                    result['error'] = detail.get('error', 'Unknown error')
            else:
                num_skip += 1
            results.append(result)

        if not silent:
            message = (f"Total books processed: {len(results)}\n"
                       f"Updated: {num_success}\nSkipped: {num_skip}\nFailed: {num_fail}\n")
            SyncCompletionDialog(self.gui, "Sync Completed", message, results, type="info").exec_()
        
        self.Syncing = False

    def quick_link_books(self):
        def audible_search(params):
            headers = {
                'Accept': 'application/json',
                'User-Agent': f'CalibreAudiobookshelfSync/{self.version}',
            }
            req = Request(f"https://api.audible{CONFIG['audibleRegion']}/1.0/catalog/products?{urllib.parse.urlencode(params)}", headers=headers)
            with urlopen(req, timeout=20) as response:
                resp_data = response.read()
                return json.loads(resp_data.decode('utf-8'))

        abs_items = self.get_abs_library_items()
        if abs_items is None:
            return

        abs_asin_index = {} # key of ASIN and value of list of dict with keys abs_id and abs_title
        for item in abs_items:
            abs_asin = item.get('media', {}).get('metadata', {}).get('asin')
            abs_title = item.get('media', {}).get('metadata', {}).get('title', 'Unknown Title')
            if abs_asin:
                abs_asin_index.setdefault(abs_asin, []).append({'abs_id': item.get('id'), 'abs_title': abs_title})
        abs_asin_set = set(abs_asin_index.keys())

        db = self.gui.current_db.new_api
        all_book_ids = list(db.search('not identifiers:"=audiobookshelf_id:"'))
        num_linked = 0
        num_failed = 0
        results = []
        for book_id in all_book_ids:
            metadata = db.get_metadata(book_id)
            title = metadata.get('title', 'None')
            authors = metadata.get('authors', [])
            if title and authors and authors[0] != 'Unknown':
                try:
                    response = audible_search({
                        'title': title,
                        'author': authors[0],
                        'num_results': 25,
                    })

                    asin_overlap = {item['asin'] for item in response['products']}.intersection(abs_asin_set)
                    if asin_overlap:
                        if len(asin_overlap) == 1:
                            matched_asin = next(iter(asin_overlap))
                            abs_id_list = abs_asin_index.get(matched_asin)
                            if len(abs_id_list) == 1:
                                identifiers = metadata.get('identifiers', {})
                                identifiers['audiobookshelf_id'] = abs_id_list[0]['abs_id']
                                metadata.set('identifiers', identifiers)
                                db.set_metadata(book_id, metadata, set_title=False, set_authors=False)
                                num_linked += 1
                                results.append({
                                    'title': metadata.get('title', f'Book {book_id}'),
                                    'linked': f"Linked to {abs_id_list[0]['abs_title']}"
                                })
                            else:
                                num_failed += 1
                                results.append({
                                    'title': metadata.get('title', f'Book {book_id}'),
                                    'error': f"{len(abs_id_list)} Audiobookshelf books with same ASIN, you must manually match"
                                })
                        else:
                            num_failed += 1
                            results.append({
                                'title': metadata.get('title', f'Book {book_id}'),
                                'error': f"{len(asin_overlap)} possible matches found, you must manually match"
                            })
                    else:
                        num_failed += 1
                        results.append({
                            'title': metadata.get('title', f'Book {book_id}'),
                            'error': f"Audible search found {response['total_results']} books and I checked {len(response['products'])} of them but none of them matched"
                        })
                except Exception:
                    num_failed += 1
                    results.append({
                        'title': metadata.get('title', f'Book {book_id}'),
                        'error': "Couldn't find any Audible audiobooks matching the title and author"
                    })
            else:
                num_failed += 1
                results.append({
                    'title': metadata.get('title', f'Book {book_id}'),
                    'error': "Book is missing title and/or author which are required for quick link"
                })
        message = (f"Quick Link Books completed.\nBooks linked: {num_linked}\nBooks failed: {num_failed}")
        if num_linked+num_failed == 0:
            message += '\n\nNo Books Needing To Be Linked'
        SyncCompletionDialog(self.gui, "Quick Link Results", message, results, type="info").exec_()

    def link_audiobookshelf_book(self):
        items_data = self.get_abs_library_items()
        if items_data is None:
            return

        # Get me data
        server_url = CONFIG.get('abs_url', 'http://localhost:13378')
        api_key = CONFIG.get('abs_key', '')
        me_url = f"{server_url}/api/me"
        me_data = self.api_request(me_url, api_key)

        if me_data is None:
            show_error(self.gui, "API Error", "Failed to retrieve Audiobookshelf user data.")
            return

        if isinstance(items_data, dict) and "results" in items_data:
            items_list = items_data["results"]
        elif isinstance(items_data, list):
            items_list = items_data
        else:
            items_list = []

        filtered_items = [item for item in items_list if isinstance(item, dict)]
        sorted_items = sorted(filtered_items, key=lambda x: x.get('media', {}).get('metadata', {}).get('title', '').lower())

        selected_ids = self.gui.library_view.get_selected_ids()
        if not selected_ids:
            show_info(self.gui, "No Selection", "No books selected.")
            return
        summary = {'linked': 0, 'skipped': 0, 'failed': 0, 'details': []}
        for book_id in selected_ids:
            metadata = self.gui.current_db.new_api.get_metadata(book_id)
            book_title = metadata.get('title', f'Book {book_id}')
            book_uuid = metadata.get('uuid')
            
            dlg = LinkDialog(self.gui, sorted_items, calibre_metadata=metadata, me_data=me_data)
            if dlg.exec_():
                selected_item = dlg.get_selected_item()
                if selected_item:
                    abs_id = selected_item.get('id')
                    abs_title = selected_item.get('media', {}).get('metadata', {}).get('title', 'Unknown Title')
                    identifiers = metadata.get('identifiers', {})
                    identifiers['audiobookshelf_id'] = abs_id
                    if CONFIG.get('checkbox_enable_Audible_ASIN_sync', False):
                        Audible_ASIN = selected_item.get('media').get('metadata').get('asin')
                        identifiers['audible'] = Audible_ASIN
                    metadata.set('identifiers', identifiers)
                    self.gui.current_db.new_api.set_metadata(book_id, metadata, set_title=False, set_authors=False)
                    summary['linked'] += 1
                    summary['details'].append({
                        'title': book_title,
                        'mapped_title': abs_title,
                        'linked': 'Linked successfully'
                    })
                else:
                    summary['skipped'] += 1
                    summary['details'].append({
                        'title': book_title,
                        'mapped_title': '',
                        'skipped': 'Skipped by user'
                    })
            else:
                summary['skipped'] += 1
                summary['details'].append({
                    'title': book_title,
                    'mapped_title': '',
                    'skipped': 'Dialog cancelled'
                })
        message = (f"Link Audiobookshelf Book completed.\nBooks linked: {summary['linked']}\nBooks skipped: {summary['skipped']}")
        SyncCompletionDialog(self.gui, "Link Results", message, summary['details'], type="info").exec_()

    def get_abs_library_items(self):
        """Get all items from all Audiobookshelf libraries."""
        server_url = CONFIG.get('abs_url', 'http://localhost:13378')
        api_key = CONFIG.get('abs_key', '')
        
        if not api_key:
            show_error(self.gui, "Configuration Error", "API Key not set in configuration.")
            return None

        # Get list of libraries
        libraries_url = f"{server_url}/api/libraries"
        libraries_response = self.api_request(libraries_url, api_key)
        
        if libraries_response is None:
            show_error(self.gui, "API Error", "Failed to retrieve Audiobookshelf libraries.")
            return None

        # Extract libraries list from response
        libraries_data = libraries_response.get('libraries', [])
        
        # Build complete items list from all libraries
        all_items = []
        for library in libraries_data:
            library_id = library.get('id')
            library_name = library.get('name')
            if not library_id:
                continue
            if library.get('mediaType') != 'book':
                continue  # Skip non-audiobook libraries
                
            items_url = f"{server_url}/api/libraries/{library_id}/items"
            items_data = self.api_request(items_url, api_key)
            
            if items_data is None:
                continue
                
            # Extract items from response and add library name
            items_list = items_data["results"]
            items_list = [{**item, 'libraryName': library_name} for item in items_list]
                
            all_items.extend(items_list)
        
        return all_items if all_items else None

    def get_abs_collections(self, server_url, api_key):
        collections_dict = {}
        collections_map = {}
        collections_data = self.api_request(f"{server_url}/api/collections", api_key)
        if collections_data is None:
            show_error(self.gui, "API Error", "Failed to retrieve Audiobookshelf collections.")
            return
        for collection in collections_data.get("collections", []):
            collection_name = collection.get("name")
            collections_map[collection_name] = collection.get("id")
            for book in collection.get("books", []):
                collections_dict.setdefault(book.get("id"), []).append(collection_name)
        
        playlists_data = self.api_request(f"{server_url}/api/playlists", api_key)
        if playlists_data is None:
            show_error(self.gui, "API Error", "Failed to retrieve Audiobookshelf playlists.")
            return
        for playlist in playlists_data.get("playlists", []):
            playlist_label = "PL " + playlist.get("name", "")
            collections_map[playlist_label] = playlist.get("id")
            for item in playlist.get("items", []):
                collections_dict.setdefault(item.get("libraryItemId"), []).append(playlist_label)

        return collections_dict, collections_map

class SyncCompletionDialog(QDialog):
    def __init__(self, parent=None, title="", msg="", results=None, type=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(800)
        self.setMinimumHeight(800)
        layout = QVBoxLayout(self)
        # Main Message Area
        mainMessageLayout = QHBoxLayout()
        type_icon = {
            'info': 'dialog_information',
            'error': 'dialog_error',
            'warn': 'dialog_warning',
        }.get(type)
        if type_icon is not None:
            icon = QIcon.ic(f'{type_icon}.png')
            mainMessageLayout.setSpacing(10)
            self.setWindowIcon(icon)
            icon_widget = QLabel(self)
            icon_widget.setPixmap(icon.pixmap(64, 64))
            mainMessageLayout.addWidget(icon_widget)
        message_label = QLabel(msg)
        message_label.setWordWrap(True)
        mainMessageLayout.addWidget(message_label)
        layout.addLayout(mainMessageLayout)
        # Scrollable area for the table
        self.table_area = QScrollArea(self)
        self.table_area.setWidgetResizable(True)
        if results:
            table = self.create_results_table(results)
            self.table_area.setWidget(table)
            layout.addWidget(self.table_area)
        # Bottom Buttons
        bottomButtonLayout = QHBoxLayout()
        if results:
            copy_button = QPushButton("COPY", self)
            copy_button.setFixedWidth(200)
            copy_button.setIcon(QIcon.ic('edit-copy.png'))
            copy_button.clicked.connect(lambda: (
                QApplication.clipboard().setText(str(results)), 
                copy_button.setText('Copied')
            ))
            bottomButtonLayout.addWidget(copy_button)
        bottomButtonLayout.addStretch() # Right align the rest of this layout
        ok_button = QPushButton("OK", self)
        ok_button.setFixedWidth(200)
        ok_button.setIcon(QIcon.ic('ok.png'))
        ok_button.clicked.connect(self.accept)
        ok_button.setDefault(True)
        bottomButtonLayout.addWidget(ok_button)
        layout.addLayout(bottomButtonLayout)
    
    def create_results_table(self, results):
        # Get all possible headers from results
        all_headers = set()
        for result in results:
            all_headers.update(result.keys())
        
        # Organize headers: title first, custom columns in middle, error last
        headers = ['title']
        custom_columns = sorted(h for h in all_headers 
                               if h not in ('title', 'error', 'linked', 'skipped'))
        if custom_columns:
            headers.extend(custom_columns)
        if 'linked' in all_headers:
            headers.append('linked')
        if 'skipped' in all_headers:
            headers.append('skipped')
        if 'error' in all_headers:
            headers.append('error')

        table = QTableWidget()
        table.setRowCount(len(results))
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)

        # Set minimum width for each column
        for i in range(len(headers)):
            table.setColumnWidth(i, 150)

        for row, result in enumerate(results):
            for col, key in enumerate(headers):
                value = result.get(key, "")
                item = QTableWidgetItem(str(value))
                table.setItem(row, col, item)
                item.setToolTip(str(value))
        
        return table

class LinkDialog(QDialog):
    def __init__(self, parent, items, calibre_metadata=None, me_data=None):
        super().__init__(parent)
        self.setWindowTitle("Link Audiobookshelf Book")
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)
        self.selected_item = None
        self.items = items
        self.calibre_metadata = calibre_metadata

        layout = QVBoxLayout(self)
        top_label = QLabel("Select the Audiobookshelf book to link:")
        layout.addWidget(top_label)
        if self.calibre_metadata is not None:
            # Assume calibre metadata provides 'title' and 'authors'
            calibre_title = self.calibre_metadata.get('title', 'Unknown Title')
            # For authors, attempt to join if it's a list, else use the string.
            calibre_authors = self.calibre_metadata.get('authors')
            if isinstance(calibre_authors, list):
                calibre_authors = ", ".join(calibre_authors)
            else:
                calibre_authors = calibre_authors or "Unknown Author"
            book_label_text = f'<b>{calibre_title}</b> by <i><b>{calibre_authors}</b></i>'
        else:
            book_label_text = ''
        book_label = QLabel(book_label_text)
        book_label.setWordWrap(True)
        layout.addWidget(book_label)
        if calibre_metadata.get('identifiers', {}).get('audiobookshelf_id') is not None:
            already_linked_label = QLabel(f'<span style="color:red">This book is already linked to an Audiobookshelf item.</span>')
            layout.addWidget(already_linked_label)

        self.table = QTableWidget(len(items), 3)
        self.table.setHorizontalHeaderLabels(["Title", "Author", "Reading/Read"])
        
        # Get calibre book details for comparison
        calibre_title = self.calibre_metadata.get('title', '').lower() if self.calibre_metadata else ''
        calibre_authors = self.calibre_metadata.get('authors', []) if self.calibre_metadata else []
        if isinstance(calibre_authors, str):
            calibre_authors = [calibre_authors]
        calibre_authors = [author.lower() for author in calibre_authors]

        # Sort items - matched items first, then alphabetically by title
        def sort_key(item):
            metadata = item.get('media', {}).get('metadata', {})
            abs_title = metadata.get('title', '').lower()
            abs_author = metadata.get('authorName', '').lower()
            
            # Calculate match score: 2 for title+author match, 1 for either match, 0 for no match
            score = 0
            if abs_title == calibre_title:
                score += 1
            if abs_author in calibre_authors:
                score += 1
                
            # Return tuple: (negative score for reverse sort, title for alphabetical)
            return (-score, abs_title)
            
        sorted_items = sorted(items, key=sort_key)
        self.items = sorted_items  # Update items list with sorted version
        
        # Create a light blue color for highlighting
        highlight_color = QColor(173, 216, 230)  # Light blue RGB values
        
        # Create checkmark icon for reading/read status
        checkmark_icon = QIcon.ic('ok.png')
        
        # Get list of library item IDs from me_data
        reading_ids = set()
        if me_data and 'mediaProgress' in me_data:
            reading_ids = {prog.get('libraryItemId') for prog in me_data['mediaProgress'] if prog.get('libraryItemId')}

        for i, item in enumerate(sorted_items):
            metadata = item.get('media', {}).get('metadata', {})
            abs_title = metadata.get('title', '')
            abs_author = metadata.get('authorName', '')

            # Create title item
            title_item = QTableWidgetItem(abs_title)
            title_item.setFlags(title_item.flags() & ~Qt.ItemIsEditable)
            if abs_title.lower() == calibre_title:
                title_item.setBackground(highlight_color)
                title_item.setForeground(QColor(0, 0, 0))  # Force black text
            self.table.setItem(i, 0, title_item)

            # Create author item  
            author_item = QTableWidgetItem(abs_author)
            author_item.setFlags(author_item.flags() & ~Qt.ItemIsEditable)
            if abs_author.lower() in calibre_authors:
                author_item.setBackground(highlight_color)
                author_item.setForeground(QColor(0, 0, 0))  # Force black text
            self.table.setItem(i, 1, author_item)

            # Create reading status item
            status_item = QTableWidgetItem()
            status_item.setFlags(status_item.flags() & ~Qt.ItemIsEditable)
            if item.get('id') in reading_ids:
                status_item.setIcon(checkmark_icon)
            self.table.setItem(i, 2, status_item)

        self.table.resizeColumnsToContents()
        self.table.setColumnWidth(0, 300)
        self.table.setColumnWidth(1, 300)
        self.table.setColumnWidth(2, 100)
        # Allow double-clicking a row to link
        self.table.cellDoubleClicked.connect(self.link)
        layout.addWidget(self.table)

        bottomButtonLayout = QHBoxLayout()
        skip_btn = QPushButton("Skip", self)
        skip_btn.setFixedWidth(200)
        skip_btn.setIcon(QIcon.ic('edit-redo.png'))
        skip_btn.clicked.connect(self.skip)
        bottomButtonLayout.addWidget(skip_btn)
        bottomButtonLayout.addStretch() # Right align the rest of this layout
        link_btn = QPushButton("Link", self)
        link_btn.setFixedWidth(200)
        link_btn.setIcon(QIcon.ic('insert-link.png'))
        link_btn.clicked.connect(self.link)
        link_btn.setDefault(True)
        bottomButtonLayout.addWidget(link_btn)
        layout.addLayout(bottomButtonLayout)

    def keyPressEvent(self, event):
        # Type a letter to jump to the row with a title starting with that letter.
        key = event.text().lower()
        if key:
            for i in range(self.table.rowCount()):
                item = self.table.item(i, 0)
                if item and item.text().lower().startswith(key):
                    self.table.selectRow(i)
                    break
        super().keyPressEvent(event)

    def link(self, *args):
        row = self.table.currentRow()
        self.selected_item = self.items[row] if 0 <= row < len(self.items) else None
        self.accept()

    def skip(self):
        self.selected_item = None
        self.accept()

    def get_selected_item(self):
        return self.selected_item
