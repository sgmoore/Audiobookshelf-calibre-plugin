#!/usr/bin/env python3
"""Config for Audiobookshelf Sync plugin for calibre"""

import os
import json
from functools import partial
from datetime import datetime

from PyQt5.Qt import (
    QComboBox,
    QCheckBox,
    QGroupBox,
    QPushButton,
    QLabel,
    QLineEdit,
    QHBoxLayout,
    QVBoxLayout,
    QFormLayout,
    QWidget,
    QSpinBox,
    QFrame,
    QDialog,
    Qt,
)
from PyQt5.QtGui import QPixmap
from calibre.constants import numeric_version
from calibre.devices.usbms.driver import debug_print as root_debug_print
from calibre.utils.iso8601 import local_tz
from calibre.utils.config import JSONConfig
from calibre.gui2 import show_restart_warning, error_dialog
from calibre.customize.ui import initialized_plugins
from calibre.customize import PluginInstallationType

__license__ = 'GNU GPLv3'
__copyright__ = '2025, jbhul'

'''
Each entry in the below dict has the following keys:
Each entry is keyed by the name of the config item used to store the selected column's lookup name
  column_heading: Default custom column heading
  datatype: Default custom column datatype
  is_multiple (optional): only for text columns, whether to allow multiple values (tags).
  description: Default custom column description
  default_lookup_name: Name of the config item to store the selected column
  config_label: Label for the item in the Config UI
  config_tool_tip: Tooltip for the item in the Config UI
  api_source: Source of the data; "lib_items" for the GET /api/libraries/{ID}/items endpoint,
              "mediaProgress" for values in mediaProgress of GET /api/me (except bookmarks),
              or "me" for bookmarks.
  data_location: Reference (as a list of keys) to the value in the API response.
  transform (optional): lambda expression to be applied in formatting the value.
'''
CUSTOM_COLUMN_DEFAULTS = {
    'column_audiobook_size': {
        'column_heading': _("Audiobook Size"),
        'datatype': 'text',
        'description': _("Size of the audiobook in MB"),
        'default_lookup_name': '#abs_size',
        'config_label': _('Audiobook Size:'),
        'config_tool_tip': _('A "Text" column to store the audiobook size in MB (formatted with commas as thousands separators).'),
        'api_source': "lib_items",
        'data_location': ['size'],
        'transform': lambda value: f"{int(float(value) / (1024*1024)):,} MB"
    },
    'column_audiobook_duration': {
        'column_heading': _("Audiobook Duration"),
        'datatype': 'text',
        'description': _("Duration of the audiobook formatted (Hrs:Min)"),
        'default_lookup_name': '#abs_duration',
        'config_label': _('Audiobook Duration:'),
        'config_tool_tip': _('A "Text" column to store the duration of the audiobook in Hrs:Min format.'),
        'api_source': "lib_items",
        'data_location': ['media', 'duration'],
        'transform': (lambda value: f"{int(float(value)//3600)}:{int((float(value) % 3600)//60):02d}")
    },
    'column_audiobook_subtitle': {
        'column_heading': _("Audiobook Subtitle"),
        'datatype': 'text',
        'description': _("Subtitle of the audio/book"),
        'default_lookup_name': '#abs_subtitle',
        'config_label': _('Audiobook Subtitle:'),
        'config_tool_tip': _('A "Text" column to store the subtitle from the audiobook metadata.'),
        'api_source': "lib_items",
        'data_location': ['media', 'metadata', 'subtitle'],
    },
    'column_audiobook_narrator': {
        'column_heading': _("Audiobook Narrator"),
        'datatype': 'text',
        'description': _("Narrator name(s)"),
        'default_lookup_name': '#abs_narrator',
        'config_label': _('Audiobook Narrator:'),
        'config_tool_tip': _('A "Text" column to store the narrator name from the audiobook metadata.'),
        'api_source': "lib_items",
        'data_location': ['media', 'metadata', 'narratorName'],
    },
    'column_audiobook_publisher': {
        'column_heading': _("Audiobook Publisher"),
        'datatype': 'text',
        'description': _("Publisher of the audiobook"),
        'default_lookup_name': '#abs_publisher',
        'config_label': _('Audiobook Publisher:'),
        'config_tool_tip': _('A "Text" column to store the publisher from the audiobook metadata.'),
        'api_source': "lib_items",
        'data_location': ['media', 'metadata', 'publisher'],
    },
    'column_audiobook_abridged': {
        'column_heading': _("Audiobook Abridged"),
        'datatype': 'bool',
        'description': _("Indicates if the audiobook is abridged"),
        'default_lookup_name': '#abs_abridged',
        'config_label': _('Audiobook Abridged:'),
        'config_tool_tip': _('A "Yes/No" column to indicate if the audiobook is abridged.'),
        'api_source': "lib_items",
        'data_location': ['media', 'metadata', 'abridged'],
        'transform': (lambda value: bool(value)),
    },
    'column_audiobook_numfiles': {
        'column_heading': _("Audiobook File Count"),
        'datatype': 'int',
        'description': _("Number of files that comprise the audiobook"),
        'default_lookup_name': '#abs_numfiles',
        'config_label': _('Audiobook File Count:'),
        'config_tool_tip': _('An "Integer" column to store the number of files in the audiobook.'),
        'api_source': "lib_items",
        'data_location': ['numFiles'],
    },
    'column_audiobook_numchapters': {
        'column_heading': _("Audiobook Chapters"),
        'datatype': 'int',
        'description': _("Number of chapters in the audiobook"),
        'default_lookup_name': '#abs_numchapters',
        'config_label': _('Audiobook Chapter Count:'),
        'config_tool_tip': _('An "Integer" column to store the number of chapters in the audiobook.'),
        'api_source': "lib_items",
        'data_location': ['media', 'numChapters'],
    },
    'column_audiobook_progress_float': {
        'column_heading': _("Audiobook Precise Progress"),
        'datatype': 'float',
        'description': _("Progress percentage with decimal precision"),
        'default_lookup_name': '#abs_progfloat',
        'config_label': _('Audiobook Precise Progress (#.##%):'),
        'config_tool_tip': _('A "Float" column to store the precise reading progress with decimal places.'),
        'api_source': "mediaProgress",
        'data_location': ['progress'],
        'transform': (lambda value: float(value) * 100),
    },
    'column_audiobook_progress_int': {
        'column_heading': _("Audiobook Progress"),
        'datatype': 'int',
        'description': _("Progress percentage as a whole number"),
        'default_lookup_name': '#abs_progint',
        'config_label': _('Audiobook Progress (#%):'),
        'config_tool_tip': _('An "Integer" column to store the reading progress (0-100).'),
        'api_source': "mediaProgress",
        'data_location': ['progress'],
        'transform': (lambda value: round(float(value) * 100)),
    },
    'column_audiobook_progress_time': {
        'column_heading': _("Audiobook Progress Time"),
        'datatype': 'text',
        'description': _("Current audiobook progress time formatted as Hrs:Min"),
        'default_lookup_name': '#abs_progresstime',
        'config_label': _('Audiobook Progress Time:'),
        'config_tool_tip': _('A "Text" column to store the progress time formatted as Hrs:Min.'),
        'api_source': "mediaProgress",
        'data_location': ['currentTime'],
        'transform': (lambda value: f"{int(float(value)//3600)}:{int((float(value)%3600)//60):02d}"),
    },
    'column_audiobook_started': {
        'column_heading': _("Audiobook Started?"),
        'datatype': 'bool',
        'description': _("Indicates if the audiobook has been started"),
        'default_lookup_name': '#abs_started',
        'config_label': _('Audiobook Started?:'),
        'config_tool_tip': _('A "Yes/No" column to indicate if the audiobook has been started.'),
        'api_source': "mediaProgress",
        'data_location': [],  # No direct key; will be computed if mediaProgress is missing
        'transform': (lambda value: bool(value)),
    },
    'column_audiobook_finished': {
        'column_heading': _("Audiobook Finished?"),
        'datatype': 'bool',
        'description': _("Indicates if the audiobook has been finished"),
        'default_lookup_name': '#abs_finished',
        'config_label': _('Audiobook Finished?:'),
        'config_tool_tip': _('A "Yes/No" column to indicate if the audiobook has been finished.'),
        'api_source': "mediaProgress",
        'data_location': ['isFinished'],
        'transform': (lambda value: bool(value)),
    },
    'column_audiobook_lastread': {
        'column_heading': _("Audiobook Last Read Date"),
        'datatype': 'datetime',
        'description': _("The last date the audiobook was read"),
        'default_lookup_name': '#abs_lastread',
        'config_label': _('Audiobook Last Read Date:'),
        'config_tool_tip': _('A "Date" column to store the last date the audiobook was read.'),
        'api_source': "mediaProgress",
        'data_location': ['lastUpdate'],
        'transform': lambda value: datetime.fromtimestamp(int(value/1000)).replace(tzinfo=local_tz), 
    },
    'column_audiobook_begindate': {
        'column_heading': _("Audiobook Begin Date"),
        'datatype': 'datetime',
        'description': _("The date when the audiobook reading began"),
        'default_lookup_name': '#abs_begindate',
        'config_label': _('Audiobook Begin Date:'),
        'config_tool_tip': _('A "Date" column to store when the audiobook reading began.'),
        'api_source': "mediaProgress",
        'data_location': ['startedAt'],
        'transform': lambda value: datetime.fromtimestamp(int(value/1000)).replace(tzinfo=local_tz), 
    },
    'column_audiobook_finishdate': {
        'column_heading': _("Audiobook Finish Date"),
        'datatype': 'datetime',
        'description': _("The date when the audiobook was finished"),
        'default_lookup_name': '#abs_finishdate',
        'config_label': _('Audiobook Finish Date:'),
        'config_tool_tip': _('A "Date" column to store when the audiobook was finished.'),
        'api_source': "mediaProgress",
        'data_location': ['finishedAt'],
        'transform': lambda value: datetime.fromtimestamp(int(value/1000)).replace(tzinfo=local_tz), 
    },
    'column_audiobook_bookmarks': {
        'column_heading': _("Audiobook Bookmarks"),
        'datatype': 'comments',
        'description': _("Bookmarks in the format 'title at time' (time as hh:mm:ss)"),
        'default_lookup_name': '#abs_bookmarks',
        'config_label': _('Audiobook Bookmarks:'),
        'config_tool_tip': _('A "Long text" column to store the audiobook bookmarks with timestamps'),
        'api_source': "me",  # Bookmarks come directly from the GET /api/me bookmarks list.
        'data_location': ['bookmarks'],
        'transform': (lambda bookmarks: "\n".join(f"{b.get('title', 'No Title')} at {b.get('time', '00:00:00')}" for b in bookmarks) if isinstance(bookmarks, list) and len(bookmarks) > 0 else 'No Bookmarks'),
    },
}

CHECKBOXES = { # Each entry in the below dict is keyed with config_name
    'checkbox_enable_scheduled_sync': {
        'config_label': 'Enable Daily Sync',
        'config_tool_tip': 'Enable daily sync of metadata using Audiobookshelf\'s API.',
    },
}

CONFIG = JSONConfig(os.path.join('plugins', 'Audiobookshelf Sync.json'))
# Set defaults for all custom columns
for config_name in CUSTOM_COLUMN_DEFAULTS:
    CONFIG.defaults[config_name] = ''
# Set defaults for checkboxes
for config_name in CHECKBOXES:
    CONFIG.defaults[config_name] = False
# Set other defaults
CONFIG.defaults['abs_url'] = 'http://localhost:13378'
CONFIG.defaults['abs_key'] = ''
CONFIG.defaults['abs_library_id'] = ''
CONFIG.defaults['scheduleSyncHour'] = 4
CONFIG.defaults['scheduleSyncMinute'] = 0

if numeric_version >= (5, 5, 0):
    module_debug_print = partial(root_debug_print, ' audiobookshelf:config:', sep='')
else:
    module_debug_print = partial(root_debug_print, ' audiobookshelf:config:')


class ConfigWidget(QWidget):
    def __init__(self, plugin_action):
        QWidget.__init__(self)
        debug_print = partial(module_debug_print, 'ConfigWidget:__init__:')
        debug_print('start')
        self.action = plugin_action
        self.must_restart = False

        # Set up main layout
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Add icon and title
        title_layout = TitleLayout(
            self,
            'images/abs_icon.png',
            f'Configure {self.action.version}',
        )
        layout.addLayout(title_layout)

        # Sync Section
        ps_header_label = QLabel(
            "This plugin allows calibre to pull metadata from Audiobookshelfs built-in API.\n"
            "You must link the audiobook using either Quick Link (automatic by ASIN or ISBN) "
            "or by selecting the correct book using the link feature.\n"
            "This functionality can optionally be scheduled as a daily sync from within calibre. "
            "Enter scheduled time in military time (default is 4 AM local time)."
        )
        ps_header_label.setWordWrap(True)
        layout.addWidget(ps_header_label)

        audiobookshelf_account_button = QPushButton('Add Audiobookshelf Account', self)
        audiobookshelf_account_button.clicked.connect(self.show_abs_account_popup)
        layout.addWidget(audiobookshelf_account_button)

        scheduled_sync_layout = QHBoxLayout()
        scheduled_sync_layout.setAlignment(Qt.AlignLeft)
        scheduled_sync_layout.addLayout(self.add_checkbox('checkbox_enable_scheduled_sync'))
        scheduled_sync_layout.addWidget(QLabel('Scheduled Time:'))
        self.schedule_hour_input = QSpinBox()
        self.schedule_hour_input.setRange(0, 23)
        self.schedule_hour_input.setValue(CONFIG['scheduleSyncHour'])
        self.schedule_hour_input.setSuffix('h')
        scheduled_sync_layout.addWidget(self.schedule_hour_input)
        scheduled_sync_layout.addWidget(QLabel(':'))
        self.schedule_minute_input = QSpinBox()
        self.schedule_minute_input.setRange(0, 59)
        self.schedule_minute_input.setValue(CONFIG['scheduleSyncMinute'])
        self.schedule_minute_input.setSuffix('m')
        scheduled_sync_layout.addWidget(self.schedule_minute_input)
        layout.addLayout(scheduled_sync_layout)

        # Add custom column dropdowns
        layout.addWidget(self.create_separator())
        self._get_create_new_custom_column_instance = None
        self.sync_custom_columns = {}
        bottom_options_layout = QHBoxLayout()
        layout.addLayout(bottom_options_layout)
        columns_group_box = QGroupBox(_('Synchronisable Custom Columns:'), self)
        bottom_options_layout.addWidget(columns_group_box)
        columns_group_box_layout = QHBoxLayout()
        columns_group_box.setLayout(columns_group_box_layout)
        columns_group_box_layout2 = QFormLayout()
        columns_group_box_layout.addLayout(columns_group_box_layout2)
        columns_group_box_layout.addStretch()

        for config_name, metadata in CUSTOM_COLUMN_DEFAULTS.items():
            self.sync_custom_columns[config_name] = {
                'current_columns': self.get_custom_columns(metadata['datatype'])
            }
            self._column_combo = self.create_custom_column_controls(
                columns_group_box_layout2, 
                config_name
            )
            metadata['comboBox'] = self._column_combo
            self._column_combo.populate_combo(
                self.sync_custom_columns[config_name]['current_columns'],
                CONFIG[config_name]
            )

    def show_abs_account_popup(self):
        self.abs_account_popup = ABSAccountPopup(self)
        self.abs_account_popup.show()

    def save_settings(self):
        debug_print = partial(module_debug_print, ' ConfigWidget:save_settings:')
        debug_print('old CONFIG = ', CONFIG)

        needRestart = (self.must_restart or
            CONFIG['checkbox_enable_scheduled_sync'] != (CHECKBOXES['checkbox_enable_scheduled_sync']['checkbox'].checkState() == Qt.Checked) or
            CONFIG['scheduleSyncHour'] != self.schedule_hour_input.value() or
            CONFIG['scheduleSyncMinute'] != self.schedule_minute_input.value()
        )

        for config_name, metadata in CUSTOM_COLUMN_DEFAULTS.items():
            CONFIG[config_name] = metadata['comboBox'].get_selected_column()

        for config_name in CHECKBOXES:
            CONFIG[config_name] = CHECKBOXES[config_name]['checkbox'].checkState() == Qt.Checked

        CONFIG['scheduleSyncHour'] = self.schedule_hour_input.value()
        CONFIG['scheduleSyncMinute'] = self.schedule_minute_input.value()

        debug_print('new CONFIG = ', CONFIG)
        if needRestart and show_restart_warning('Changes have been made that require a restart to take effect.\nRestart now?'):
            self.action.gui.quit(restart=True)

    def add_checkbox(self, checkboxKey):
        layout = QHBoxLayout()
        checkboxMeta = CHECKBOXES[checkboxKey]
        checkbox = QCheckBox()
        checkbox.setCheckState(Qt.Checked if CONFIG[checkboxKey] else Qt.Unchecked)
        label = QLabel(checkboxMeta['config_label'])
        label.setToolTip(checkboxMeta['config_tool_tip'])
        label.setBuddy(checkbox)
        layout.addWidget(checkbox)
        layout.addWidget(label)
        layout.addStretch()
        CHECKBOXES[checkboxKey]['checkbox'] = checkbox
        return layout

    def create_custom_column_controls(self, columns_group_box_layout, custom_col_name, min_width=300):
        current_Location_label = QLabel(CUSTOM_COLUMN_DEFAULTS[custom_col_name]['config_label'], self)
        current_Location_label.setToolTip(CUSTOM_COLUMN_DEFAULTS[custom_col_name]['config_tool_tip'])
        create_column_callback = partial(self.create_custom_column, custom_col_name) if SUPPORTS_CREATE_CUSTOM_COLUMN else None
        avail_columns = self.sync_custom_columns[custom_col_name]['current_columns']
        custom_column_combo = CustomColumnComboBox(self, avail_columns, create_column_callback=create_column_callback)
        custom_column_combo.setMinimumWidth(min_width)
        current_Location_label.setBuddy(custom_column_combo)
        form_layout = columns_group_box_layout
        form_layout.addRow(current_Location_label, custom_column_combo)
        self.sync_custom_columns[custom_col_name]['combo_box'] = custom_column_combo
        return custom_column_combo

    def create_custom_column(self, lookup_name=None):
        if not lookup_name or lookup_name not in CUSTOM_COLUMN_DEFAULTS:
            return False
            
        column_meta = CUSTOM_COLUMN_DEFAULTS[lookup_name]
        display_params = {
            'description': column_meta['description']
        }
        datatype = column_meta['datatype']
        column_heading = column_meta['column_heading']
        is_multiple = column_meta.get('is_multiple', False)
        
        # Get the create column instance
        create_new_custom_column_instance = self.get_create_new_custom_column_instance
        if not create_new_custom_column_instance:
            return False

        # Use default_lookup_name as base for new column
        new_lookup_name = column_meta['default_lookup_name']
        
        try:
            result = create_new_custom_column_instance.create_column(
                new_lookup_name, 
                column_heading, 
                datatype, 
                is_multiple, 
                display=display_params,
                generate_unused_lookup_name=True,
                freeze_lookup_name=False
            )
            
            if result and result[0] == CreateNewCustomColumn.Result.COLUMN_ADDED:
                self.sync_custom_columns[lookup_name]['current_columns'][result[1]] = {
                    'name': column_heading
                }
                self.sync_custom_columns[lookup_name]['combo_box'].populate_combo(
                    self.sync_custom_columns[lookup_name]['current_columns'],
                    result[1]
                )
                self.must_restart = True
                return True
        except Exception:
            pass
            
        return False

    @property
    def get_create_new_custom_column_instance(self):
        if self._get_create_new_custom_column_instance is None and SUPPORTS_CREATE_CUSTOM_COLUMN:
            self._get_create_new_custom_column_instance = CreateNewCustomColumn(self.action.gui)
        return self._get_create_new_custom_column_instance

    def get_custom_columns(self, datatype):
        if SUPPORTS_CREATE_CUSTOM_COLUMN:
            custom_columns = self.get_create_new_custom_column_instance.current_columns()
        else:
            custom_columns = self.action.gui.library_view.model().custom_columns
        available_columns = {}
        for key, column in custom_columns.items():
            typ = column['datatype']
            if typ == datatype:
                available_columns[key] = column
        if datatype == 'rating':  # Add rating column if requested
            ratings_column_name = self.action.gui.library_view.model().orig_headers['rating']
            available_columns['rating'] = {'name': ratings_column_name}
        return available_columns

    def create_separator(self):
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        return separator

try:
    from calibre.gui2.preferences.create_custom_column import CreateNewCustomColumn
    SUPPORTS_CREATE_CUSTOM_COLUMN = True
except ImportError:
    SUPPORTS_CREATE_CUSTOM_COLUMN = False


class ABSAccountPopup(QDialog):
    def __init__(self, parent):
        QDialog.__init__(self, parent)
        self.setWindowTitle('Add Audiobookshelf Account')
        self.setGeometry(100, 100, 400, 200)

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.note_label = QLabel(
            'Enter your Audiobookshelf server URL, if it''s the same device as '
            'calibre you can leave the default filled in.\n'
            'Enter your API Key and Library ID. Then click Save Account.',
            self
        )
        self.note_label.setWordWrap(True)
        layout.addWidget(self.note_label)

        self.url_label = QLabel('Audiobookshelf Server URL:', self)
        self.url_input = QLineEdit(self)
        self.url_input.setText(CONFIG['abs_url'])
        layout.addWidget(self.url_label)
        layout.addWidget(self.url_input)

        self.key_label = QLabel('API Key:', self)
        self.key_input = QLineEdit(self)
        self.key_input.setText(CONFIG['abs_key'])
        layout.addWidget(self.key_label)
        layout.addWidget(self.key_input)

        self.lib_id_label = QLabel('Library ID:', self)
        self.lib_id_input = QLineEdit(self)
        self.lib_id_input.setText(CONFIG['abs_library_id'])
        layout.addWidget(self.lib_id_label)
        layout.addWidget(self.lib_id_input)

        self.login_button = QPushButton('Save Account', self)
        self.login_button.clicked.connect(self.save_audiobookshelf_account_settings)
        layout.addWidget(self.login_button)

    def save_audiobookshelf_account_settings(self):
        CONFIG['abs_url'] = self.url_input.text()
        CONFIG['abs_key'] = self.key_input.text()
        CONFIG['abs_library_id'] = self.lib_id_input.text()
        try:
            from calibre.ebooks.metadata.sources.prefs import msprefs
            id_link_rules = msprefs['id_link_rules']
            id_link_rules['audiobookshelf_id'] = [['Audiobookshelf', f'{self.url_input.text()}/audiobookshelf/item/{{id}}']]
            msprefs['id_link_rules'] = id_link_rules
        except ImportError:
            print('Could not add identifer link rule')        
        
        self.accept()


class TitleLayout(QHBoxLayout):
    def __init__(self, parent, icon, title):
        QHBoxLayout.__init__(self)
        icon_label = QLabel(parent)
        pixmap = QPixmap()
        pixmap.loadFromData(get_resources(icon))
        icon_label.setPixmap(pixmap)
        icon_label.setMaximumSize(64, 64)
        icon_label.setScaledContents(True)
        self.addWidget(icon_label)
        title_label = QLabel(f'<h2>{title}</h2>', parent)
        title_label.setContentsMargins(10, 0, 10, 0)
        self.addWidget(title_label)
        self.addStretch()
        readme_label = QLabel('<a href="#">Readme</a>', parent)
        readme_label.setTextInteractionFlags(Qt.LinksAccessibleByMouse | Qt.LinksAccessibleByKeyboard)
        readme_label.linkActivated.connect(parent.action.show_readme)
        self.addWidget(readme_label)
        about_label = QLabel('<a href="#">About</a>', parent)
        about_label.setTextInteractionFlags(Qt.LinksAccessibleByMouse | Qt.LinksAccessibleByKeyboard)
        about_label.linkActivated.connect(parent.action.show_about)
        self.addWidget(about_label)

class CustomColumnComboBox(QComboBox):
    CREATE_NEW_COLUMN_ITEM = _("Create new column")
    def __init__(self, parent, custom_columns={}, selected_column='', create_column_callback=None):
        super(CustomColumnComboBox, self).__init__(parent)
        self.create_column_callback = create_column_callback
        self.current_index = 0
        self.initial_items = ['do not sync']
        if create_column_callback is not None:
            self.currentTextChanged.connect(self.current_text_changed)
        self.populate_combo(custom_columns, selected_column)

    def populate_combo(self, custom_columns, selected_column, show_lookup_name=True):
        self.clear()
        self.column_names = []
        selected_idx = 0
        if isinstance(self.initial_items, dict):
            for key in sorted(self.initial_items.keys()):
                self.column_names.append(key)
                display_name = self.initial_items[key]
                self.addItem(display_name)
                if key == selected_column:
                    selected_idx = len(self.column_names) - 1
        else:
            for item in self.initial_items:
                self.column_names.append(item)
                self.addItem(item)
                if item == selected_column:
                    selected_idx = len(self.column_names) - 1

        for key in sorted(custom_columns.keys()):
            self.column_names.append(key)
            display_name = '%s (%s)'%(key, custom_columns[key]['name']) if show_lookup_name else custom_columns[key]['name']
            self.addItem(display_name)
            if key == selected_column:
                selected_idx = len(self.column_names) - 1
        
        if self.create_column_callback is not None:
            self.addItem(self.CREATE_NEW_COLUMN_ITEM)
            self.column_names.append(self.CREATE_NEW_COLUMN_ITEM)

        self.setCurrentIndex(selected_idx)

    def get_selected_column(self):
        selected_column = self.column_names[self.currentIndex()]
        if selected_column == self.CREATE_NEW_COLUMN_ITEM:
            selected_column = ''
        if selected_column == 'do not sync':
            selected_column = ''
        return selected_column

    def current_text_changed(self, new_text):
        if new_text == self.CREATE_NEW_COLUMN_ITEM:
            result = self.create_column_callback()
            if not result:
                self.setCurrentIndex(self.current_index)
        else:
            self.current_index = self.currentIndex()
    
    def wheelEvent(self, event): # Prevents the mouse wheel from changing the selected item
        event.ignore()