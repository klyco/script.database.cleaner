#!/usr/bin/python
# -*- coding: utf-8 -*-

#  script.video.cleaner
#  Written by black_eagle and BatterPudding
#  Updated to work with Kodi 19 Matrix by kenmills
# Version 27b/7 - Batter Pudding Fix added
# Version 27b/9 - Batter Pudding tweaks the debug logging
# Version 28b/1 - New GUI, several code fixes
# Version 28b/2 - Fix the WINDOWS KODI temp path
# Version 28b/3 - Tidy up temp path code, remove some unused code
# Version 29b/1 - Add ability to rename paths inside the db
# Version 29b/2 - Fix incorrectly altered SQL
# Version 30b/1 - UI improvements - only allow one instance

#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#

import datetime
import json as jsoninterface
import sqlite3
import xml.etree.ElementTree as ET
import mysql.connector
import xbmc
import xbmcvfs
import xbmcaddon
import xbmcgui

# database versions to scan for

MIN_VIDEODB_VERSION = 116
MAX_VIDEODB_VERSION = 119  # i.e. Matrix, aka Kodi 19

ACTION_PREVIOUS_MENU = 10
ACTION_SELECT_ITEM = 7
ACTION_NAV_BACK = 92
ACTION_MOUSE_LEFT_CLICK = 100
flag = 0
WINDOW = xbmcgui.Window(10000)


class MyClass(xbmcgui.WindowXMLDialog):

    def __init__(self, *args, **kwargs):
        pass

    def onInit(self):
        self.container = self.getControl(6)
        self.container2 = self.getControl(8)
        self.container3 = self.getControl(10)
        self.listitems = []
        self.excludesitems = []
        self.addonsettings = []

    #       List paths from sources.xml

        if not specificpath and not replacepath:
            self.display_list = display_list
            for i in range(len(self.display_list)):
                self.listitems.append('[COLOR yellow]'
                        + self.display_list[i] + '[/COLOR]')
            if no_sources:
                self.listitems.append('[COLOR red][B]No sources are in use[/B][/COLOR]'
                        )
                self.listitems.append('[COLOR red][B]All streaming paths will be removed[/B][/COLOR]'
                        )
                if excluding:
                    self.listitems.append('')
                    self.listitems.append('[COLOR red][B]Paths from excludes.xml will be kept[/B][/COLOR]'
                            )
        if replacepath:
            self.listitems.append('[COLOR yellow]Replacing a path[/COLOR]'
                                  )
            self.listitems.append('[COLOR yellow]in your database[/COLOR]'
                                  )
            self.listitems.append('[COLOR yellow]Confirm details below[/COLOR]'
                                  )
        if specificpath:
            self.listitems.append('[COLOR yellow]Removing a path[/COLOR]'
                                  )
            self.listitems.append('[COLOR yellow]in your database[/COLOR]'
                                  )
            self.listitems.append('[COLOR yellow]Confirm details below[/COLOR]'
                                  )
        self.container.addItems(self.listitems)

    #       List paths in excludes.xml (if it exists)

        self.excludes_list = excludes_list

        if excluding:
            for i in range(len(self.excludes_list)):
                self.excludesitems.append('[COLOR yellow]'
                        + self.excludes_list[i] + '[/COLOR]')
        else:
            self.excludesitems.append('Not Present')
        self.container2.addItems(self.excludesitems)

    #       List the relevant addon settings

        if deepclean and not replacepath and not specificpath and not is_mysql and not no_sources and not remote_file:
            self.addonsettings.append('Deep clean is on')
        if is_pvr and not specificpath and not replacepath:
            self.addonsettings.append('Keep PVR information')
        if bookmarks and not specificpath and not replacepath:
            self.addonsettings.append('Keep bookmark information')
        if autoclean:
            self.addonsettings.append('Auto call Clean Library')
        if autoclean_multiple_times:
            self.addonsettings.append('Run Clean Library multiple times')
        if promptdelete:
            self.addonsettings.append('Show summary window (This window !!)'
                    )
        if autobackup == 'true' and not is_mysql:
            self.addonsettings.append('Auto backing up local database')
        if no_sources or specificpath or replacepath:
            self.addonsettings.append('[COLOR red]Not[/COLOR] using info from sources.xml'
                    )
        if specificpath:
            self.addonsettings.append('[COLOR red]Cleaning a specific path[/COLOR]'
                    )
        if replacepath:
            self.addonsettings.append('[COLOR red]Replacing a path[/COLOR]'
                    )
        if enable_logging:
            self.addonsettings.append('Writing a logfile to Kodi TEMP directory'
                    )
        if debugging:
            debug_string = 'Debugging [COLOR red]enabled[/COLOR]'
        else:
            debug_string = 'Debugging [COLOR green]disabled[/COLOR]'
        self.addonsettings.append(debug_string)
        self.addonsettings.append('')  # blank line

        #   Display the name of the database we are connected to

        self.addonsettings.append('Database is - [COLOR green][B]%s[/B][/COLOR]'
                                   % our_dbname)
        wrapped_execute(cursor, our_select, my_command_list, window=self, suppress_notification=True)
        data_list = cursor.fetchall()
        data_list_size = len(data_list)
        if replacepath:
            self.addonsettings.append('[COLOR red][B]There are %d paths to be changed[/B][/COLOR]'
                     % data_list_size)
        else:
            # Get an additional count for files that will be deleted
            temp_start_string = 'SELECT strPath '
            if not our_select.startswith(temp_start_string):
                dbglog('Error: expected SQL statement to start with "%s". Actual statement: %s' % (temp_start_string, our_select))
                xbmcgui.Dialog().ok(addonname,
                        'Error: expected SQL statement to start with "%s". Actual statement: %s' % (temp_start_string, our_select)
                                    )
                self.close()
                exit_on_error()
            temp_bookmark_string = 'idPath NOT IN (SELECT DISTINCT idPath FROM files INNER JOIN bookmark ON bookmark.idFile = files.idFile UNION SELECT DISTINCT idParentPath FROM path INNER JOIN files ON files.idPath = path.idPath INNER JOIN bookmark ON bookmark.idFile = files.idFile INNER JOIN episode ON episode.idFile = bookmark.idFile)'
            if bookmarks and our_select.find(temp_bookmark_string) == -1:
                dbglog('Error: expected SQL statement with bookmarks to have the string "%s". Actual statement: %s' % (temp_bookmark_string, our_select))
                xbmcgui.Dialog().ok(addonname,
                        'Error: expected SQL statement with bookmarks to have the string "%s". Actual statement: %s' % (temp_bookmark_string, our_select)
                                    )
                self.close()
                exit_on_error()
            count_files_statement = our_select
            if bookmarks:
                count_files_statement = count_files_statement.replace(temp_start_string, 'SELECT count(*) FROM files WHERE NOT EXISTS (SELECT 1 FROM path WHERE path.idPath = files.idPath) OR (NOT EXISTS (SELECT 1 FROM bookmark WHERE bookmark.idFile = files.idFile) AND idPath IN (SELECT DISTINCT idPath ', 1)
                count_files_statement = count_files_statement.replace(temp_bookmark_string, 'TRUE', 1)
                count_files_statement = count_files_statement[:-1] + '))' + count_files_statement[-1:]
            else:
                count_files_statement = count_files_statement.replace(temp_start_string, 'SELECT count(*) FROM files WHERE NOT EXISTS (SELECT 1 FROM path WHERE path.idPath = files.idPath) OR idPath IN (SELECT DISTINCT idPath ', 1)
                count_files_statement = count_files_statement[:-1] + ')' + count_files_statement[-1:]
            wrapped_execute(cursor, count_files_statement, my_command_list, window=self, suppress_notification=True)
            # Show the number of records to be removed on the screen
            temp_number_of_files_to_delete = cursor.fetchall()[0][0]
            dbglog('There are %d entries to be removed from the path table and %d entries to be removed from the files table'
                     % (data_list_size, temp_number_of_files_to_delete))
            self.addonsettings.append('[COLOR red][B]There are %d entries to be removed from the path table and %d entries to be removed from the files table[/B][/COLOR]'
                     % (data_list_size, temp_number_of_files_to_delete))
            if global_prepared_list is not None:
                self.addonsettings.append('[COLOR red][B]There are %d entries to be removed in total from "deep clean".[/B][/COLOR]' % (len(global_prepared_list)))
            del temp_start_string
            del temp_bookmark_string
            del temp_number_of_files_to_delete
            del count_files_statement

        self.container3.addItems(self.addonsettings)

        #   Show warning about backup if using MySQL

        if is_mysql:
            self.getControl(20).setLabel('WARNING - MySQL database [COLOR red][B]not[/B][/COLOR] backed up automatically, please do this [B]manually[/B]'
                    )
        if specificpath:
            self.getControl(20).setLabel('WARNING - Removing specific path [COLOR yellow]%s[/COLOR] '
                     % specific_path_to_remove)
        if replacepath:
            self.getControl(20).setLabel('WARNING - Renaming specific path from [COLOR yellow]%s[/COLOR] '
                     % old_path)
            self.getControl(21).setLabel('TO  [COLOR yellow]%s[/COLOR] '
                     % new_path)

    def onAction(self, action):
        global flag
        dbglog('Got an action %s' % action.getId())
        if action == ACTION_PREVIOUS_MENU or action == ACTION_NAV_BACK:
            self.close()
        if action == ACTION_SELECT_ITEM or action \
            == ACTION_MOUSE_LEFT_CLICK:
            try:
                btn = self.getFocus()
                btn_id = btn.getId()
            except:

                btn_id = None
            if btn_id == 1:
                dbglog('you pressed abort')
                flag = 0
                self.close()
            elif btn_id == 2:
                dbglog('you pressed clean')
                flag = 1
                self.close()


#  Set some variables ###

addon = xbmcaddon.Addon()
addonname = addon.getAddonInfo('name')
addonversion = addon.getAddonInfo('version')
addonpath = addon.getAddonInfo('path')

advanced_file = \
    xbmcvfs.translatePath('special://profile/advancedsettings.xml')
sources_file = xbmcvfs.translatePath('special://profile/sources.xml')
excludes_file = \
    xbmcvfs.translatePath('special://profile/addon_data/script.database.cleaner/excludes.xml'
                          )
db_path = xbmcvfs.translatePath('special://database')
userdata_path = xbmcvfs.translatePath('special://userdata')
bp_logfile_path = xbmcvfs.translatePath('special://temp/bp-debuglog.log'
        )
type_of_log = ''
is_pvr = addon.getSetting('pvr')
autoclean = addon.getSetting('autoclean')
autoclean_multiple_times = addon.getSetting('autoclean_multiple_times')
bookmarks = addon.getSetting('bookmark')
promptdelete = addon.getSetting('promptdelete')
source_file_path = addon.getSetting('sourcefilepath')
debugging = addon.getSetting('debugging')
no_sources = addon.getSetting('usesources')
autobackup = addon.getSetting('autobackup')
specificpath = addon.getSetting('specificpath')
backup_filename = addon.getSetting('backupname')
forcedbname = addon.getSetting('overridedb')
replacepath = addon.getSetting('replacepath')
enable_logging = addon.getSetting('logtolog')
deletesetswithlessthantwo = addon.getSetting('deletesetswithlessthantwo')
show_notification_for_each_sql_statement = addon.getSetting('show_notification_for_each_sql_statement')
runtexturecache = addon.getSetting('runtexturecache')
debugtexturecache = addon.getSetting('debugtexturecache')
deepclean = addon.getSetting('deepclean')
deepcleanonlyonedirectory = addon.getSetting('deepcleanonlyonedirectory')
deepcleanonlyonedirectory_path = addon.getSetting('deepcleanonlyonedirectory_path')
tc_option_list = []
for tc_option in 'c, C, lc, p, P, Xd, r, R, qa, qax, duplicates'.replace(' ', '').split(','):
    if tc_option.lower() != tc_option and tc_option != "Xd":
        tc_option_s = tc_option + 'cap'
    else:
        tc_option_s = tc_option
    if addon.getSetting('texturecache_' + tc_option_s) == 'true':
        tc_option_list.append(tc_option)
if deletesetswithlessthantwo == 'true':
    deletesetswithlessthantwo = True
else:
    deletesetswithlessthantwo = False
if show_notification_for_each_sql_statement == 'true':
    show_notification_for_each_sql_statement = True
else:
    show_notification_for_each_sql_statement = False
if runtexturecache == 'true':
    runtexturecache = True
else:
    runtexturecache = False
if debugtexturecache == 'true':
    debugtexturecache = True
else:
    debugtexturecache = False
if deepclean == 'true':
    deepclean = True
else:
    deepclean = False
if deepcleanonlyonedirectory == 'true':
    deepcleanonlyonedirectory = True
else:
    deepcleanonlyonedirectory = False
if enable_logging == 'true':
    enable_logging = True
    type_of_log = addon.getSetting('typeoflog')
else:
    enable_logging = False
if replacepath == 'true':
    replacepath = True
else:
    replacepath = False
old_path = addon.getSetting('oldpath')
new_path = addon.getSetting('newpath')
if forcedbname == 'true':
    forcedbname = True
else:
    forcedbname = False
forcedname = addon.getSetting('forceddbname')
if specificpath == 'true':
    specificpath = True
else:
    specificpath = False
specific_path_to_remove = addon.getSetting('spcpathstr')
display_list = []
excludes_list = []
renamepath_list = []
excluding = False
found = False
is_mysql = False
remote_file = False
cleaning = False
path_name = ''
the_path = ''
success = 0
our_source_list = ''
if debugging == 'true':
    debugging = True
else:
    debugging = False
running_dialog = None
global_source_list = []
global_prepared_list = None


def log(txt):

    if isinstance(txt, str):
        txt = txt
        message = u'%s: %s' % (addonname, txt)
        xbmc.log(msg=message, level=xbmc.LOGDEBUG)


def dbglog(txt):
    if debugging:
        log(txt)

def texturecache_dbglog(txt):
    if isinstance(txt, str):
        message = u'%s: %s' % (addonname + ': From texturecache.py', txt)
        xbmc.log(msg=message, level=xbmc.LOGDEBUG)

def exit_on_error():
    # Try to make sure we fail gracefully.
    try:
        cursor.close()
    except Exception:
        pass
    try:
        db.rollback()
    except Exception:
        pass
    try:
        db.close()
    except Exception:
        pass
    try:
        running_dialog.close()
    except Exception:
        pass
    WINDOW.setProperty('database-cleaner-running', 'false')
    exit(1)

def wrapped_execute(cursor, sql, params=None, error_message=None, window=None, suppress_notification=False, progress=1):
    if not params:
        params = []
    if not error_message:
        error_message = 'Error executing SQL statement. The SQL statement was: %s, called with parameters %s.' % (sql, str(params))
    try:
        unwrapped_execute(cursor, sql, params, suppress_notification, progress)
    except Exception as e:
        error_message = error_message + ' Error: %s' % (str(e))
        dbglog(error_message)
        xbmcgui.Dialog().ok(addonname, error_message)
        if window:
            try:
                window.close()
            except Exception:
                pass
        exit_on_error()

def unwrapped_execute(cursor, sql, params=None, suppress_notification=False, progress=1):
    global replacepath
    global show_notification_for_each_sql_statement
    global running_dialog
    if not params:
        params = []
    dbglog('Executing SQL command - %s - params: %s' % (sql, str(params)))
    if not replacepath and show_notification_for_each_sql_statement and not suppress_notification:
        running_dialog = xbmcgui.DialogProgressBG()
        running_dialog.create('Executing SQL statement - %s - params: %s' % (sql, str(params)))
        running_dialog.update(min(int(progress),100))
    cursor.execute(sql, params)
    if not replacepath and show_notification_for_each_sql_statement and not suppress_notification:
        try:
            running_dialog.close()
        except Exception:
            pass

def cleaner_log_file(our_select, my_command_list, cleaning):
    cleaner_log = \
        xbmcvfs.translatePath('special://temp/database-cleaner.log')
    old_cleaner_log = \
        xbmcvfs.translatePath('special://temp/database-cleaner.old.log')
    old_log_contents = ''
    do_progress = False
    if not enable_logging:
        return
    if type_of_log == '0':
        dbglog('Writing to new log file')
        if cleaning:
            if xbmcvfs.exists(cleaner_log):
                dbglog('database-cleaner.log exists - renaming to old.log'
                       )
                xbmcvfs.delete(old_cleaner_log)
                xbmcvfs.copy(cleaner_log, old_cleaner_log)
                xbmcvfs.delete(cleaner_log)
        else:
            xbmcvfs.delete(cleaner_log)
    else:
        dbglog('Appending to existing log file')
        if cleaning:
            if xbmcvfs.exists(cleaner_log):
                dbglog('database-cleaner.log exists - backing up to old.log'
                       )
                xbmcvfs.delete(old_cleaner_log)
                xbmcvfs.copy(cleaner_log, old_cleaner_log)
        with xbmcvfs.File(cleaner_log) as old_log:
            old_log_contents = old_log.read()

    now = datetime.datetime.now()
    with xbmcvfs.File(cleaner_log, 'w') as logfile:
        if old_log_contents:
            logfile.write(old_log_contents)
        date_long_format = xbmc.getRegion('datelong')
        time_format = xbmc.getRegion('time')
        date_long_format = date_long_format + ' ' + time_format
        logfile_header = 'Video Database Cleaner V' + addonversion \
            + ' - Running at ' + now.strftime(date_long_format) + '''

'''
        logfile.write(logfile_header)

        if deepclean and not replacepath and not specificpath and not no_sources:
            global global_prepared_list
            global global_source_list
            if global_prepared_list is None:
                temp_params = []
                temp_like_str = ''
                temp_atleastonesource = False
                if deepcleanonlyonedirectory:
                    if deepcleanonlyonedirectory_path == '':
                        xbmcgui.Dialog().ok(addonname, 'Deep clean is set to clean only one directory, but the directory path is empty. Not doing deep clean.')
                        global_source_list = []
                    elif not (deepcleanonlyonedirectory_path.endswith('/') or deepcleanonlyonedirectory_path.endswith('\\')):
                        xbmcgui.Dialog().ok(addonname, 'Deep clean is set to clean only one directory, but the corresponding directory path does not end with a valid path separator. Not doing deep clean.')
                        global_source_list = []

                for s in global_source_list:
                    if not (s.endswith('/') or s.endswith('\\')):
                        dbglog('Ignoring source %s because it doesn\'t end with a valid path separator' % (s))
                    elif not deepcleanonlyonedirectory or s.startswith(deepcleanonlyonedirectory_path):
                        temp_params.append(s + '_%')
                        temp_atleastonesource = True
                    else:
                        dbglog('Ignoring source %s because it doesn\'t match parameters: deepcleanonlyonedirectory: %r, s.startswith(deepcleanonlyonedirectory_path): %r' % (s, deepcleanonlyonedirectory, s.startswith(deepcleanonlyonedirectory_path)))
                temp_like_str = ' OR strPath LIKE '.join('?'*len(temp_params))
                temp_like_str += ')'
                if excluding:
                    temp_params.extend([e + '%' for e in excludes_list])
                    temp_like_str += ' AND (strPath NOT LIKE '
                    temp_like_str += ' AND strPath NOT LIKE '.join(replstr*len(excludes_list))
                    temp_like_str += ')'
                concat_string = "(path.strPath || files.strFilename)" if not is_mysql else "CONCAT(path.strPath, files.strFilename)"
                temp_sql = "SELECT strPath, idPath as id FROM path WHERE (strPath LIKE " + temp_like_str + " UNION SELECT " + concat_string + " as strPath, idFile as id FROM files INNER JOIN path ON files.idPath = path.idPath WHERE (strPath LIKE " + temp_like_str + " ORDER BY strPath"
                del concat_string
                if temp_atleastonesource:
                    temp_sql_count = "SELECT count(*) FROM (%s)" % (temp_sql)
                    wrapped_execute(cursor, temp_sql_count, temp_params*2)
                    temp_sql_count = cursor.fetchall()[0][0]
                    temp_files_to_delete_list = []
                    wrapped_execute(cursor, temp_sql, temp_params*2)
                    temp_res = cursor.fetchone()
                    running_dialog = xbmcgui.DialogProgressBG()
                    running_dialog.create('Please wait. Deep clean is verifying files')
                    temp_i = -1
                    while temp_res is not None:
                        temp_i += 1
                        if temp_sql_count < 100 or (temp_i % 100) == 0:
                            running_dialog.update(min(int(100*temp_i/temp_sql_count),100))
                        if not xbmcvfs.exists(temp_res[0]):
                            temp_files_to_delete_list.append(temp_res)
                        temp_res = cursor.fetchone()
                    running_dialog.close()
                    del temp_i
                    del temp_sql_count
                else:
                    dbglog('The "deep clean" option found no valid sources to check.')
                if not temp_atleastonesource or len(temp_files_to_delete_list) == 0:
                    global_prepared_list = []
                else:
                    global_prepared_list = temp_files_to_delete_list
                del temp_params
                del temp_like_str
                del temp_atleastonesource
                del temp_sql
            if not len(global_prepared_list) == 0:
                dbglog('Listsize from "deep clean" is %d' % (len(global_prepared_list)))
                if not cleaning:
                    logfile.write('The following files and paths would be removed from "deep clean" alone (total %d) (check the remainder of the file for additional paths related to the general cleaning option):\n' % (len(global_prepared_list)))
                else:
                    logfile.write('The following files and paths were removed from "deep clean" alone (total %d) (check the remainder of the file for additional paths related to the general cleaning option):\n' % (len(global_prepared_list)))
                for s, _ in global_prepared_list:
                    logfile.write('%s\n' % (s))
            else:
                logfile.write('No files or paths to be removed by the "deep clean" option')
            logfile.write('\n\n\n')

        wrapped_execute(cursor, our_select, my_command_list, window=logfile, suppress_notification=True)
        counting = 0
        my_data = cursor.fetchall()
        listsize = len(my_data)
        dbglog('Listsize is %d' % listsize)
        logfile.write('''There are %d paths in the database that meet your criteria

'''
                    % listsize)
        if listsize > 600:
            do_progress = True
            dialog = xbmcgui.DialogProgressBG()
            dbglog('Creating progress dialog for logfile')
            dialog.create('Getting required data.  Please wait')
            dialog.update(1)

        if not cleaning and not replacepath:
            logfile.write('The following file paths would be removed from your database'
                        )
            logfile.write('''

''')
        elif cleaning and not replacepath:
            logfile.write('The following paths were removed from the database'
                        )
            logfile.write('''

''')
        elif not cleaning and replacepath:
            logfile.write('The following paths will be changed in your database'
                        )
            logfile.write('''

''')
        else:
            logfile.write('The following paths were changed in your database'
                        )
            logfile.write('''

''')
        if not specificpath and not replacepath:
            for strPath in my_data:
                counting += 1
                mystring = u''.join(strPath) + '\n'
                outdata = mystring
                if do_progress:
                    dialog.update(percent=int(counting / float(listsize)
                                * 100))
                if cleaning:
                    dbglog('Removing %s' % strPath)
                logfile.write(outdata)
        elif specificpath and not replacepath:
            dbglog('Removing specific path %s' % specific_path_to_remove)
            for strPath in my_data:
                counting += 1
                mystring = u''.join(strPath) + '\n'
                outdata = mystring
                if do_progress:
                    dialog.update(percent=int(counting / float(listsize)
                                * 100))
                if cleaning:
                    dbglog('Removing unwanted path %s' % strPath)
                logfile.write(outdata)
        else:
            for strPath in my_data:
                counting += 1
                mystring = u''.join(strPath) + '\n'
                outdata = mystring
                if do_progress:
                    dialog.update(percent=int(counting / float(listsize)
                                * 100))
                if cleaning:
                    dbglog('Changing path %s' % strPath)
                logfile.write(outdata)
            our_data = cursor
        if counting == 0:  # nothing to remove
            logfile.write('No paths have been found to remove\n')
        if do_progress:
            dialog.close()
        logfile.write('''

''')

def get_texturecache_duplicates_logfile():
    texturecache_log = \
        xbmcvfs.translatePath('special://temp/database-cleaner-duplicates.log')
    old_texturecache_log = \
        xbmcvfs.translatePath('special://temp/database-cleaner-duplicates.old.log')
    old_log_contents = ''
    if type_of_log == '0':
        dbglog('Writing to new log file')
        if xbmcvfs.exists(texturecache_log):
            dbglog('database-cleaner-duplicates.log exists - renaming to old.log'
                   )
            xbmcvfs.delete(old_texturecache_log)
            xbmcvfs.copy(texturecache_log, old_texturecache_log)
            xbmcvfs.delete(texturecache_log)
    else:
        dbglog('Appending to existing log file')
        if xbmcvfs.exists(texturecache_log):
            dbglog('database-cleaner-duplicates.log exists - backing up to old.log'
                   )
            xbmcvfs.delete(old_texturecache_log)
            xbmcvfs.copy(texturecache_log, old_texturecache_log)
        old_log = xbmcvfs.File(texturecache_log)
        old_log_contents = old_log.read()
        old_log.close()

    now = datetime.datetime.now()
    logfile = xbmcvfs.File(texturecache_log, 'w')
    if old_log_contents:
        logfile.write(old_log_contents)
    date_long_format = xbmc.getRegion('datelong')
    time_format = xbmc.getRegion('time')
    date_long_format = date_long_format + ' ' + time_format
    logfile_header = 'Video Database Cleaner V' + addonversion \
        + ' - Running at ' + now.strftime(date_long_format) + ' - "texturecache.py duplicates" invocation' + '''

'''
    logfile.write(logfile_header)
    return logfile

####    Start Here !!   ####

dbglog('script version %s started' % addonversion)

# if WINDOW.getProperty('database-cleaner-running') == 'true':
    # log('Video Database Cleaner already running')
    # exit(0)
# else:
    # WINDOW.setProperty('database-cleaner-running', 'true')

if runtexturecache:
    tccfg_option_dict = {}
    for tccfg_option in ('userdata', 'dbfile', 'thumbnails', 'xbmc.host', 'webserver.port', 'rpc.port', 'download.threads', 'orphan.limit.check', 'extrajson.albums', 'extrajson.artists', 'extrajson.songs', 'extrajson.movies', 'extrajson.sets', 'extrajson.tvshows.tvshow', 'extrajson.tvshows.season', 'extrajson.tvshows.episode', 'qaperiod', 'qa.file', 'cache.castthumb', 'logfile', 'logfile.verbose', 'network.mac', 'allow.recacheall'):
        temp_tccfg_opt_bool = 'false'
        temp_tccfg_opt_bool = addon.getSetting('tc_opt_' + tccfg_option + '_bool')
        temp_tccfg_opt_bool = True if temp_tccfg_opt_bool == 'true' else False
        tccfg_option_dict[tccfg_option] = (temp_tccfg_opt_bool, addon.getSetting('tc_opt_' + tccfg_option + '_value'))
    del temp_tccfg_opt_bool
    tccfg_from_file_dict = {}
    tccfg_from_bfile_dict = {}
    tccfg_file_path = xbmcvfs.translatePath('special://home/addons/script.database.cleaner/resources/texturecache.cfg')
    tccfg_bfile_path = xbmcvfs.translatePath('special://home/addons/script.database.cleaner/resources/donotedit.tccfg.bak')
    tccfg_overwrite_existing = False
    temp_filecontents = ''
    if not xbmcvfs.exists(tccfg_bfile_path) and not xbmcvfs.exists(tccfg_file_path):
        tccfg_overwrite_existing = True
    else:
        if not xbmcvfs.exists(tccfg_file_path):
            tccfg_overwrite_existing = True
        else:
            if xbmcvfs.exists(tccfg_bfile_path):
                with xbmcvfs.File(tccfg_bfile_path) as temp_f:
                    temp_all_lines = temp_f.read().split('\n')
                    for temp_line in temp_all_lines:
                        temp_line += '\n'
                        if len(temp_line.split('=')) < 2:
                            continue
                        if temp_line.startswith('#'):
                            temp_line = temp_line[1:]
                            temp_line_active = False
                        else:
                            temp_line_active = True
                        temp_optname = temp_line.split('=')[0].strip()
                        temp_optvalue = temp_line.split('=')[1].strip()
                        if temp_optname in tccfg_option_dict:
                            tccfg_from_bfile_dict[temp_optname] = (temp_line_active, temp_optvalue)
                    del temp_all_lines
            else:
                tccfg_from_bfile_dict = tccfg_option_dict
            with xbmcvfs.File(tccfg_file_path) as temp_f:
                temp_atleastonedifferent = False
                temp_all_lines = temp_f.read().split('\n')
                temp_filecontents_list = []
                for temp_line in temp_all_lines:
                    temp_line += '\n'
                    if len(temp_line.split('=')) < 2 or temp_line.startswith('='):
                        temp_filecontents_list.append(temp_line)
                        continue
                    if temp_line.startswith('#'):
                        temp_line_active = False
                        temp_optname = temp_line[1:].split('=')[0].strip()
                    else:
                        temp_line_active = True
                        temp_optname = temp_line.split('=')[0].strip()
                    temp_optvalue = temp_line.split('=')[1].strip()
                    if temp_optname in tccfg_from_bfile_dict:
                        if temp_line_active != tccfg_from_bfile_dict[temp_optname][0] or temp_optvalue != tccfg_from_bfile_dict[temp_optname][1]:
                            temp_atleastonedifferent = True
                        temp_line = '#' if not tccfg_option_dict[temp_optname][0] else ''
                        temp_line += temp_optname + ' = '
                        temp_line += tccfg_option_dict[temp_optname][1]
                        temp_line += '\n'
                        tccfg_from_file_dict[temp_optname] = (temp_line_active, temp_optvalue)
                    if temp_line not in temp_filecontents_list:
                        temp_filecontents_list.append(temp_line)
                temp_filecontents = ''.join(temp_filecontents_list)
                if temp_filecontents.endswith('\n'):
                    temp_filecontents = temp_filecontents[:-1]
                del temp_filecontents_list
                del temp_all_lines
                if len(tccfg_from_file_dict) == len(tccfg_from_bfile_dict) and not temp_atleastonedifferent:
                    tccfg_overwrite_existing = True
            del temp_atleastonedifferent
            del temp_line
            del temp_line_active
            del temp_optname
            del temp_optvalue
    if not tccfg_overwrite_existing:
        temp_overwritevalue = xbmcgui.Dialog().yesnocustom(addonname, 'The texturecache.cfg does not match what the add-on expected to see. Click "Add-on" to continue with the add-on settings (which will be saved to the file), "File" to continue with the file settings (which will be saved to the add-on) or "Abort" to cancel the add-on run.', 'Abort', 'File', 'Add-on')
        if temp_overwritevalue == 0:
            tccfg_overwrite_existing = False
        elif temp_overwritevalue == 1:
            tccfg_overwrite_existing = True
        else:
            dbglog('Aborting add-on run')
            exit_on_error()
        del temp_overwritevalue
    if tccfg_overwrite_existing:
        xbmcvfs.delete(tccfg_file_path)
        with xbmcvfs.File(tccfg_file_path, 'w') as temp_f:
            if temp_filecontents != '':
                temp_f.write(temp_filecontents)
            else:
                for temp_optname in tccfg_option_dict:
                    temp_line = '#' if not tccfg_option_dict[temp_optname][0] else ''
                    temp_line += temp_optname + ' = '
                    temp_line += tccfg_option_dict[temp_optname][1]
                    temp_line += '\n'
                    temp_f.write(temp_line)
                del temp_optname
                del temp_line
    else:
        for temp_optname in tccfg_option_dict:
            if temp_optname not in tccfg_from_file_dict:
                addon.setSettingBool('tc_opt_' + temp_optname + '_bool', False)
            else:
                addon.setSettingBool('tc_opt_' + temp_optname + '_bool', tccfg_from_file_dict[temp_optname][0])
                addon.setSetting('tc_opt_' + temp_optname + '_value', tccfg_from_file_dict[temp_optname][1])
        del temp_optname
    xbmcvfs.copy(tccfg_file_path, tccfg_bfile_path)
    del temp_filecontents
    del tccfg_option_dict
    del tccfg_from_file_dict
    del tccfg_from_bfile_dict


xbmcgui.Dialog().notification(addonname, 'Scanning library...',
                              xbmcgui.NOTIFICATION_INFO, 2000)
xbmc.sleep(2000)

if xbmcvfs.exists(advanced_file):
    dbglog('Found advancedsettings.xml')
    found = True

if found:
    msg = advanced_file
    dbglog('looking in advancedsettings for videodatabase info')
    try:
        advancedsettings = ET.parse(advanced_file)
    except ET.ParseError:
        dbglog('Error parsing advancedsettings.xml file')
        xbmcgui.Dialog().ok(addonname,
                            'Error parsing advancedsettings.xml file[CR] Possibly a mal-formed comment or missing closing tag - script aborted'
                            )
        exit_on_error()
    root = advancedsettings.getroot()
    try:
        for videodb in root.findall('videodatabase'):
            try:
                our_host = videodb.find('host').text
            except:
                log('Unable to find MySQL host address')
            try:
                our_username = videodb.find('user').text
            except:
                log('Unable to determine MySQL username')
            try:
                our_password = videodb.find('pass').text
            except:
                log('Unable to determine MySQL password')
            try:
                our_port = videodb.find('port').text
            except:
                log('Unable to find MySQL port')
            try:
                our_dbname = videodb.find('name').text
            except:
                our_dbname = 'MyVideos'
            dbglog('MySQL details - %s, %s, %s, %s' % (our_host,
                   our_port, our_username, our_dbname))
            is_mysql = True
    except Exception as e:
        e = str(e)
        dbglog('Error parsing advancedsettings file - %s' % e)
        is_mysql = False

if not is_mysql:
    our_dbname = 'MyVideos'

    for num in range(MAX_VIDEODB_VERSION, MIN_VIDEODB_VERSION, -1):
        testname = our_dbname + str(num)
        our_test = db_path + testname + '.db'

        dbglog('Checking for local database %s' % testname)
        if xbmcvfs.exists(our_test):
            break
    if num != MIN_VIDEODB_VERSION:
        our_dbname = testname

    if our_dbname == 'MyVideos':
        dbglog('No video database found - assuming MySQL database')
    dbglog('Database name is %s' % our_dbname)

if is_pvr == 'true':
    is_pvr = True
else:
    is_pvr = False

if autoclean == 'true':
    autoclean = True
else:
    autoclean = False
if autoclean_multiple_times == 'true':
    autoclean_multiple_times = True
else:
    autoclean_multiple_times = False
if bookmarks == 'true':
    bookmarks = True
else:
    bookmarks = False
if promptdelete == 'true':
    promptdelete = True
else:
    promptdelete = False
if no_sources == 'true':
    no_sources = False
else:
    no_sources = True

dbglog('Settings for file cleaning are as follows')
if is_pvr:
    dbglog('keeping PVR files')
if bookmarks:
    dbglog('Keeping bookmarks')
if autoclean:
    dbglog('autocleaning afterwards')
if autoclean_multiple_times:
    dbglog('autocleaning multiple times')
if promptdelete:
    dbglog('Prompting before deletion')
if no_sources:
    dbglog('Not using sources.xml')

if source_file_path != '':
    sources_file = source_file_path
    remote_file = True
    dbglog('Remote sources.xml file path identified')
if xbmcvfs.exists(sources_file) and not remote_file:
    try:
        source_file = sources_file
        tree = ET.parse(source_file)
        root = tree.getroot()
        dbglog('Got local sources.xml file')
    except:
        dbglog('Error parsing local sources.xml file')
        xbmcgui.Dialog().ok(addonname,
                            'Error parsing local sources.xml file - script aborted'
                            )
        exit_on_error()
elif xbmcvfs.exists(sources_file):
    try:
        f = xbmcvfs.File(sources_file)
        source_file = f.read()
        f.close()
        root = ET.fromstring(source_file)
        dbglog('Got remote sources.xml')
    except:
        dbglog('Error parsing remote sources.xml')
        xbmcgui.Dialog().ok(addonname,
                            'Error parsing remote sources.xml file - script aborted'
                            )
        exit_on_error()
else:
    xbmcgui.Dialog().notification(addonname,
                                  'Warning - no sources.xml file found'
                                  , xbmcgui.NOTIFICATION_INFO, 3000)
    dbglog('No local sources.xml, no remote sources file set in settings'
           )
    xbmc.sleep(3000)
    no_sources = True
my_command = ''
my_command_list = []
first_time = True
if forcedbname:
    log('Forcing video db version to %s' % forcedname)

# Open database connection

if is_mysql and not forcedbname:
    if our_dbname == '':  # no db name in advancedsettings
        our_dbname = 'MyVideos'
        for num in range(MAX_VIDEODB_VERSION, MIN_VIDEODB_VERSION, -1):
            testname = our_dbname + str(num)
            try:
                dbglog('Attempting MySQL connection to %s' % testname)
                db = mysql.connector.connect(user=our_username,
                        database=testname, password=our_password,
                        host=our_host)
                if db.is_connected():
                    our_dbname = testname
                    dbglog('Connected to MySQL database %s'
                           % our_dbname)
                    break
            except:
                pass
    else:

                # already got db name from ad settings

        for num in range(MAX_VIDEODB_VERSION, MIN_VIDEODB_VERSION, -1):
            testname = our_dbname + str(num)
            try:
                dbglog('Attempting MySQL connection to %s' % testname)
                db = mysql.connector.connect(user=our_username,
                        database=testname, password=our_password,
                        host=our_host, port=our_port)
                if db.is_connected():
                    our_dbname = testname
                    dbglog('Connected to MySQL database %s'
                           % our_dbname)
                    break
            except:
                pass
    if not db.is_connected():
        xbmcgui.Dialog().ok(addonname,
                            "Couldn't connect to MySQL database", s)
        log("Error - couldn't connect to MySQL database - %s " % s)
        exit_on_error()
elif is_mysql and forcedbname:
    try:
        db = mysql.connector.connect(user=our_username,
                database=forcedname, password=our_password,
                host=our_host, port=our_port)
        if db.is_connected():
            our_dbname = forcedname
            dbglog('Connected to forced MySQL database %s' % forcedname)
    except:
        log('Error connecting to forced database - %s' % forcedname)
        exit_on_error()
elif not is_mysql and not forcedbname:
    try:
        my_db_connector = db_path + our_dbname + '.db'
        db = sqlite3.connect(my_db_connector)
    except Exception as e:
        s = str(e)
        xbmcgui.Dialog().ok(addonname,
                            'Error connecting to SQLite database', s)
        log('Error connecting to SQLite database - %s' % s)
        exit_on_error()
else:
    testpath = db_path + forcedname + '.db'
    if not xbmcvfs.exists(testpath):
        log('Forced version of database does not exist')
        xbmcgui.Dialog().ok(addonname,
                            'Error - Forced version of database ( %s ) not found.'
                             % forcedname)
        exit_on_error()
    try:
        my_db_connector = db_path + forcedname + '.db'
        db = sqlite3.connect(my_db_connector)
        dbglog('Connected to forced video database')
    except:
        xbmcgui.Dialog().ok(addonname,
                            'Error - Unable to connect to forced database %s.'
                             % forcedname)
        log('Unable to connect to forced database s%' % forcedname)
        exit_on_error()

cursor = db.cursor()
replstr = '?' if not is_mysql else '%s'

if xbmcvfs.exists(excludes_file):
    excludes_list = []
    excluding = True
    exclude_command = ''
    try:
        tree = ET.parse(excludes_file)
        er = tree.getroot()
        for excludes in er.findall('exclude'):
            to_exclude = excludes.text
            excludes_list.append(to_exclude)
            dbglog('Excluding plugin path - %s' % to_exclude)
            exclude_command = exclude_command + " AND strPath NOT LIKE %s" % (replstr)
        log('Parsed excludes.xml')
    except:
        log('Error parsing excludes.xml')
        xbmcgui.Dialog().ok(addonname,
                            'Error parsing excludes.xml file - script aborted'
                            )
        exit_on_error()

if not no_sources:

    # start reading sources.xml and build SQL statements to exclude these sources from any cleaning

    try:
        display_list = []
        for video in root.findall('video'):
            dbglog('Contents of sources.xml file')

            for sources in video.findall('source'):
                for path_name in sources.findall('name'):
                    the_path_name = path_name.text
                    for paths in sources.findall('path'):
                        the_path = paths.text.replace("'", "''")
                        display_list.append(the_path)
                        dbglog('%s - %s' % (the_path_name, the_path))
                        if first_time:
                            first_time = False
                            my_command = "strPath NOT LIKE %s" % (replstr)
                            my_command_list.append(the_path + '%')
                            global_source_list.append(the_path)
                            our_source_list = 'Keeping files in ' \
                                + the_path
                        else:
                            my_command = my_command \
                                + " AND strPath NOT LIKE %s" % (replstr)
                            my_command_list.append(the_path + '%')
                            global_source_list.append(the_path)
                            our_source_list = our_source_list + ', ' \
                                + the_path
            if path_name == '':
                no_sources = True
                dbglog('******* WARNING *******')
                dbglog('local sources.xml specified in settings')
                dbglog('But no sources found in sources.xml file')
                dbglog('Defaulting to alternate method for cleaning')
    except:
        log('Error parsing sources.xml file')
        xbmcgui.Dialog().ok(addonname,
                            'Error parsing sources.xml file - script aborted'
                            )
        exit_on_error()

    if is_pvr:
        my_command = my_command + " AND strPath NOT LIKE 'pvr://%'"
        our_source_list = our_source_list + 'Keeping PVR info '
    if excluding:
        my_command = my_command + exclude_command
        my_command_list.extend([e + '%' for e in excludes_list])
        our_source_list = our_source_list \
            + 'Keeping items from excludes.xml '
    if bookmarks:
        my_command = my_command \
            + ' AND idPath NOT IN (SELECT DISTINCT idPath FROM files INNER JOIN bookmark ON bookmark.idFile = files.idFile UNION SELECT DISTINCT idParentPath FROM path INNER JOIN files ON files.idPath = path.idPath INNER JOIN bookmark ON bookmark.idFile = files.idFile INNER JOIN episode ON episode.idFile = bookmark.idFile)'
        our_source_list = our_source_list + 'Keeping bookmarked files '

        # construct the full SQL query

    sql = \
        """DELETE FROM path WHERE ((""" \
        + my_command + """));"""
if no_sources:
    my_command = ''
    my_command_list = []
    our_source_list = \
        'NO SOURCES FOUND - REMOVING rtmp(e), plugin and http info '
    dbglog('Not using sources.xml')
    if is_pvr:
        my_command = my_command + "strPath NOT LIKE 'pvr://%'"
        our_source_list = our_source_list + 'Keeping PVR info '
    if bookmarks:
        if my_command:
            my_command = my_command \
                + ' AND idPath NOT IN (SELECT DISTINCT idPath FROM files INNER JOIN bookmark ON bookmark.idFile = files.idFile UNION SELECT DISTINCT idParentPath FROM path INNER JOIN files ON files.idPath = path.idPath INNER JOIN bookmark ON bookmark.idFile = files.idFile INNER JOIN episode ON episode.idFile = bookmark.idFile)'
        else:
            my_command = my_command \
                + ' idPath NOT IN (SELECT DISTINCT idPath FROM files INNER JOIN bookmark ON bookmark.idFile = files.idFile UNION SELECT DISTINCT idParentPath FROM path INNER JOIN files ON files.idPath = path.idPath INNER JOIN bookmark ON bookmark.idFile = files.idFile INNER JOIN episode ON episode.idFile = bookmark.idFile)'
        our_source_list = our_source_list + 'Keeping bookmarked files '
    if excluding:
        if my_command:
            my_command = my_command + exclude_command
        else:
            my_command = my_command + exclude_command.replace('AND', ''
                    , 1)
        my_command_list.extend([e + '%' for e in excludes_list])
        our_source_list = our_source_list \
            + 'Keeping items from excludes.xml '

# Build SQL query

if not no_sources:  # this is SQL for no sources
    sql = \
        """DELETE FROM path WHERE (((""" \
        + my_command + """)));"""
else:
    sql = \
        """DELETE FROM path WHERE ((strPath LIKE 'rtmp://%' OR strPath LIKE 'rtmpe:%' OR strPath LIKE 'plugin:%' OR strPath LIKE 'http://%' OR strPath LIKE 'https://%') AND (""" \
        + my_command + """));"""

if my_command == '':
    sql = sql.replace('((strPath', '(strPath').replace(' AND ())', ')')
    dbglog('SQL command is %s' % sql)

if not specificpath and not replacepath:
    dbglog(our_source_list)
    our_select = sql.replace('DELETE FROM path',
                             'SELECT strPath FROM path', 1)

    if bookmarks:
        dbglog(sql)
        our_select = sql.replace('DELETE FROM path',
                                 'SELECT strPath FROM path', 1)
        dbglog(our_select)
        dbglog('Select Command is %s' % our_select)
elif not replacepath and specificpath:

                                       # cleaning a specific path

    if specific_path_to_remove != '':
        sql = \
            """DELETE FROM path WHERE strPath LIKE %s""" % (replstr)
        my_command_list = [specific_path_to_remove + '%']
        our_select = \
            "SELECT strPath FROM path WHERE strPath LIKE %s" % (replstr)
        my_command_list = [specific_path_to_remove + '%']
        dbglog('Select Command is %s' % our_select)
    else:
        xbmcgui.Dialog().ok(addonname,
                            'Error - Specific path selected but no path defined. Script aborted'
                            )
        dbglog('Error - Specific path selected with no path defined')
        exit_on_error()
else:

      # must be replacing a path at this point

    if old_path != '' and new_path != '':
        our_select = \
            "SELECT strPath FROM path WHERE strPath LIKE %s" % (replstr)
        my_command_list = [old_path + '%']
    else:
        xbmcgui.Dialog().ok(addonname,
                            'Error - Replace path selected but one or more paths are not defined. Script aborted'
                            )
        dbglog('Error - Missing path for replacement')
        exit_on_error()
xbmc.sleep(500)

if promptdelete:
    cleaner_log_file(our_select, my_command_list, False)
    mydisplay = MyClass('cleaner-window.xml', addonpath, 'Default',
                        '1080i')
    mydisplay.doModal()
    del mydisplay
    if flag == 1:
        i = True
    else:
        i = False
else:

    i = True
if i:
    if autobackup == 'true' and not is_mysql:
        backup_path = \
            xbmcvfs.translatePath('special://database/backups/')

        if not xbmcvfs.exists(backup_path):
            dbglog('Creating backup path %s' % backup_path)
            xbmcvfs.mkdir(backup_path)
        now = datetime.datetime.now()
        if forcedbname:
            our_dbname = forcedname
        current_db = db_path + our_dbname + '.db'
        if backup_filename == '':
            backup_filename = our_dbname
        backup_db = backup_path + backup_filename + '_' \
            + now.strftime('%Y-%m-%d_%H%M') + '.db'
        backup_filename = backup_filename + '_' \
            + now.strftime('%Y-%m-%d_%H%M')
        success = xbmcvfs.copy(current_db, backup_db)
        if success == 1:
            success = 'successful'
        else:
            success = 'failed'
        dbglog('auto backup database %s.db to %s.db - result was %s'
               % (our_dbname, backup_filename, success))
    cleaner_log_file(our_select, my_command_list, True)
    if not replacepath:
        try:
            path_sql = sql
            temp_total_sql_statements = 13
            temp_ran_sql_statements = -1
            # When cleaning a specific path, the path table must be cleaned last so that we don't lose path-specific information
            # Also, when cleaning a specific path, we don't clean orphaned records not related to the target path
            if specificpath:
                temp_total_sql_statements = 10
                base_sql = "DELETE FROM %s WHERE EXISTS (SELECT 1 FROM files INNER JOIN path ON path.idPath = files.idPath WHERE files.idFile = %s.idFile AND path.strPath LIKE %s)"
                if bookmarks:
                    base_sql = base_sql + " AND NOT EXISTS (SELECT 1 FROM bookmark WHERE bookmark.idFile = %s.idFile)"
                for table in 'bookmark settings stacktimes movie episode musicvideo streamdetails'.split(' '):
                    if bookmarks:
                        sql = base_sql % (table, table, replstr, table)
                    else:
                        sql = base_sql % (table, table, replstr)
                    temp_ran_sql_statements = temp_ran_sql_statements + 1
                    unwrapped_execute(cursor, sql, [specificpath + '%'], progress=int(100*temp_ran_sql_statements/temp_total_sql_statements))
                base_sql = "DELETE FROM files WHERE EXISTS (SELECT 1 FROM files INNER JOIN path ON path.idPath = files.idPath AND path.strPath LIKE %s)"
                if bookmarks:
                    base_sql = base_sql + " AND NOT EXISTS (SELECT 1 FROM bookmark WHERE bookmark.idFile = files.idFile)"
                sql = base_sql % (replstr)
                temp_ran_sql_statements = temp_ran_sql_statements + 1
                unwrapped_execute(cursor, sql, [specificpath + '%'], progress=int(100*temp_ran_sql_statements/temp_total_sql_statements))
                base_sql = "DELETE FROM tvshow WHERE EXISTS (SELECT 1 FROM tvshow INNER JOIN tvshowlinkpath ON tvshow.idShow = tvshowlinkpath.idShow INNER JOIN path ON tvshowlinkpath.idPath = path.idPath WHERE path.strPath LIKE %s"
                if bookmarks:
                    base_sql = base_sql + " AND idPath NOT IN (SELECT DISTINCT idPath FROM files INNER JOIN bookmark ON bookmark.idFile = files.idFile UNION SELECT DISTINCT idParentPath FROM path INNER JOIN files ON files.idPath = path.idPath INNER JOIN episode ON episode.idFile = bookmark.idFile))"
                else:
                    base_sql = base_sql + ")"
                sql = base_sql % (replstr)
                temp_ran_sql_statements = temp_ran_sql_statements + 1
                unwrapped_execute(cursor, sql, [specificpath + '%'], progress=int(100*temp_ran_sql_statements/temp_total_sql_statements))
                base_sql = "DELETE FROM tvshowlinkpath WHERE EXISTS (SELECT 1 FROM tvshowlinkpath INNER JOIN path ON tvshowlinkpath.idPath = path.idPath WHERE path.strPath LIKE %s"
                if bookmarks:
                    base_sql = base_sql + " AND idPath NOT IN (SELECT DISTINCT idPath FROM files INNER JOIN bookmark ON bookmark.idFile = files.idFile UNION SELECT DISTINCT idParentPath FROM path INNER JOIN files ON files.idPath = path.idPath INNER JOIN bookmark ON bookmark.idFile = files.idFile INNER JOIN episode ON episode.idFile = bookmark.idFile))"
                else:
                    base_sql = base_sql + ")"
                sql = base_sql % (replstr)
                temp_ran_sql_statements = temp_ran_sql_statements + 1
                unwrapped_execute(cursor, sql, [specificpath + '%'], progress=int(100*temp_ran_sql_statements/temp_total_sql_statements))
                del base_sql


            # Perform deep clean
            if global_prepared_list is not None and len(global_prepared_list) > 0:
                temp_scale_factor = min(len(global_prepared_list), temp_total_sql_statements)
                temp_total_sql_statements += temp_scale_factor
                temp_deepclean_count = 0
                temp_debugging = debugging
                if len(global_prepared_list) > 100:
                    debugging = False
                running_dialog = xbmcgui.DialogProgressBG()
                running_dialog.create('Please wait while deep clean runs.')
                for temp_s, temp_id in global_prepared_list:
                    temp_deepclean_count += 1
                    if temp_s.endswith('/') or temp_s.endswith('\\'):
                        sql = "DELETE FROM path WHERE idPath = ?"
                    else:
                        sql = "DELETE FROM files WHERE idFile = ?"
                    unwrapped_execute(cursor, sql, [temp_id], suppress_notification=True)
                    if len(global_prepared_list) < 100 or (temp_deepclean_count % 100) == 0:
                        running_dialog.update(min(int(100*(temp_deepclean_count/len(global_prepared_list))*temp_scale_factor/temp_total_sql_statements), 100))
                running_dialog.close()
                debugging = temp_debugging
                temp_ran_sql_statements = temp_ran_sql_statements + temp_scale_factor
                del temp_debugging
                del global_prepared_list
                del temp_scale_factor
                del temp_deepclean_count

        # Perform clean-up of the path table

            sql = path_sql
            temp_ran_sql_statements = temp_ran_sql_statements + 1
            unwrapped_execute(cursor, sql, my_command_list, progress=int(100*temp_ran_sql_statements/temp_total_sql_statements))


            # When not doing a specific path, we clean all orphaned records that are left over after the path table is cleaned
            if not specificpath:
                sql = "DELETE FROM files WHERE NOT EXISTS (SELECT 1 FROM path WHERE path.idPath = files.idPath)"
                if bookmarks:
                    temp_start_string = 'DELETE FROM path '
                    if not path_sql.startswith(temp_start_string):
                        raise Exception('Error: (This error is internal to script and not related to the database): expected SQL statement to start with "%s". Actual statement: %s' % (temp_start_string, path_sql))
                    temp_bookmark_string = 'idPath NOT IN (SELECT DISTINCT idPath FROM files INNER JOIN bookmark ON bookmark.idFile = files.idFile UNION SELECT DISTINCT idParentPath FROM path INNER JOIN files ON files.idPath = path.idPath INNER JOIN bookmark ON bookmark.idFile = files.idFile INNER JOIN episode ON episode.idFile = bookmark.idFile)'
                    if path_sql.find(temp_bookmark_string) == -1:
                        raise Exception('Error: (This error is internal to script and not related to the database): expected SQL statement with bookmarks to have the string "%s". Actual statement: %s' % (temp_bookmark_string, path_sql))
                    sql = sql + path_sql.replace(temp_start_string, ' OR (NOT EXISTS (SELECT 1 FROM bookmark WHERE bookmark.idFile = files.idFile) AND idPath IN (SELECT DISTINCT idPath FROM path ', 1)
                    sql = sql.replace(temp_bookmark_string, 'TRUE', 1)
                    sql = sql[:-1] + '))' + sql[-1:]
                    temp_ran_sql_statements = temp_ran_sql_statements + 1
                    unwrapped_execute(cursor, sql, my_command_list, progress=int(100*temp_ran_sql_statements/temp_total_sql_statements))
                    del temp_start_string
                    del temp_bookmark_string
                else:
                    temp_ran_sql_statements = temp_ran_sql_statements + 1
                    unwrapped_execute(cursor, sql, progress=int(100*temp_ran_sql_statements/temp_total_sql_statements))
                base_sql = "DELETE FROM %s WHERE NOT EXISTS (SELECT 1 FROM files WHERE files.idFile = %s.idFile)"
                for table in 'bookmark settings stacktimes movie episode musicvideo streamdetails'.split(' '):
                    sql = base_sql % (table, table)
                    temp_ran_sql_statements = temp_ran_sql_statements + 1
                    unwrapped_execute(cursor, sql, progress=int(100*temp_ran_sql_statements/temp_total_sql_statements))
                base_sql = "DELETE FROM %s WHERE NOT EXISTS (SELECT 1 FROM %s WHERE %s.%s = %s.%s)"
                for table, source, field in (('tvshowlinkpath', 'path', 'idPath'), ('tvshow', 'tvshowlinkpath', 'idShow'), ('actor', 'actor_link', 'actor_id'), ('studio', 'studio_link', 'studio_id')):
                    sql = base_sql % (table, source, table, field, source, field)
                    if table == 'actor':
                        sql += " AND NOT EXISTS (SELECT 1 FROM director_link WHERE actor.actor_id = director_link.actor_id)  AND NOT EXISTS (SELECT 1 FROM writer_link WHERE actor.actor_id = writer_link.actor_id)"
                    temp_ran_sql_statements = temp_ran_sql_statements + 1
                    unwrapped_execute(cursor, sql, progress=int(100*temp_ran_sql_statements/temp_total_sql_statements))
                base_sql = "DELETE FROM sets WHERE NOT EXISTS (SELECT 1 FROM movie WHERE movie.idSet = sets.idSet GROUP BY idSet HAVING count(idSet) > %s)"
                if deletesetswithlessthantwo:
                    sql = base_sql % ("1")
                else:
                    sql = base_sql % ("0")
                temp_ran_sql_statements = temp_ran_sql_statements + 1
                unwrapped_execute(cursor, sql, progress=int(100*temp_ran_sql_statements/temp_total_sql_statements))
                del base_sql
            del path_sql
            del temp_total_sql_statements
            del temp_ran_sql_statements

#           cursor.execute(sql2)
        # Commit the changes in the database

            db.commit()
        except Exception as e:

        # Rollback in case there is any error

            db.rollback()
            dbglog('Error in db commit. Transaction rolled back')
            dbglog('******************************************************************************'
                   )
            dbglog('**  SQL ERROR  **  SQL ERROR   **  SQL ERROR  **  SQL ERROR  **  SQL ERROR  **'
                   )
            dbglog('**   %s ' % e)
            dbglog('******************************************************************************'
                   )
            xbmcgui.Dialog().ok(addonname,
                        'Error in db commit. Transaction rolled back')
            exit_on_error()
    else:

        dbglog('Changing Paths - generating SQL statements')
        our_select = "SELECT strPath FROM path WHERE strPath LIKE %s" % (replstr)
        wrapped_execute(cursor, our_select, [old_path + '%'])
        tempcount = 0
        listsize = len(cursor.fetchall())
        dialog = xbmcgui.DialogProgressBG()
        dbglog('Creating progress dialog')
        dialog.create('Replacing paths in database.  Please wait')
        dialog.update(1)
        dbglog('Cursor size is %d' % listsize)
        wrapped_execute(cursor, our_select, [old_path + '%'], window=dialog)
        renamepath_list = []
        for strPath in cursor:  # build a list of paths to change
            renamepath_list.append(''.join(strPath))

        for i in range(len(renamepath_list)):
            tempcount += 1
            our_old_path = renamepath_list[i]
            our_new_path = our_old_path.replace(old_path, new_path, 1)
            sql = 'UPDATE path SET strPath = %s WHERE strPath = %s' % (replstr, replstr)
            dialog.update(percent=int(tempcount / float(listsize)
                          * 100))
            dbglog('Percentage done %d' % int(tempcount
                   / float(listsize) * 100))
            dbglog('SQL - %s' % sql)
            wrapped_execute(cursor, sql, [our_new_path, our_old_path], window = dialog)
        try:
            db.commit()
        except Exception as e:
            e = str(e)
            db.rollback()
            dbglog('Error in db commit %s. Transaction rolled back'
                   % e)
            xbmcgui.Dialog().ok(addonname,
                                'Error in db commit %s. Transaction rolled back'
                                % e)
            dialog.close()
            exit_on_error()

    # disconnect from server
#       xbmc.executebuiltin( "Dialog.Close(busydialog)" )

        xbmc.sleep(1000)
        dbglog('Closing progress dialog')
        dialog.close()
    # When calling the Kodi's built-in library cleaning function multiple times, we want the db connection open so we can know when to stop early
    if not (autoclean and autoclean_multiple_times):
        db.close()
        dbglog('Database connection closed')

    # Make sure replacing or changing a path is a one-shot deal

    if replacepath or specificpath:
        addon.setSetting('specificpath', 'false')
        addon.setSetting('replacepath', 'false')

    if autoclean:
        xbmcgui.Dialog().notification(addonname, 'Running cleanup',
                xbmcgui.NOTIFICATION_INFO, 2000)
        xbmc.sleep(2000)

        temp_previous_pathnum = 0
        temp_previous_filenum = 0
        temp_pathnum = -1
        temp_filenum = -1
        temp_sql = ''
        for _ in range(6):
            json_query = \
                xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "VideoLibrary.Clean","id": 1 }'
                                    )
            # json_query = str(json_query)

            json_query = jsoninterface.loads(json_query)
            if 'result' in json_query:
                dbglog('Clean library sucessfully called')
            if not autoclean_multiple_times:
                break
            try:
                temp_sql = "SELECT count(*) FROM path"
                unwrapped_execute(cursor, temp_sql, params=[], suppress_notification=True)
                temp_pathnum = cursor.fetchall()[0][0]
                temp_sql = "SELECT count(*) FROM files"
                unwrapped_execute(cursor, temp_sql, params=[], suppress_notification=True)
                temp_filenum = cursor.fetchall()[0][0]
                if temp_pathnum == temp_previous_pathnum and temp_filenum == temp_previous_filenum:
                    break
                temp_previous_pathnum = temp_pathnum
                temp_previous_filenum = temp_filenum
                xbmc.sleep(1000)
            except Exception as e:
                xbmcgui.Dialog().ok(addonname,
                        'An error occured while trying to run Kodi\'s built-in library cleaning function multiple times. This does not affect the add-on cleaning, which was already saved (commited to the database). Error: %s' % (str(e))
                                    )
                break
        if autoclean_multiple_times:
            db.close()
            dbglog('Database connection closed')
        del temp_previous_pathnum
        del temp_previous_filenum
        del temp_pathnum
        del temp_filenum
        del temp_sql

    else:
        xbmcgui.Dialog().ok(addonname,
                            'Script finished.  You should run clean library for best results'
                            )
    if runtexturecache and not specificpath and not replacepath:
        xbmcgui.Dialog().notification(addonname, 'Running "texturecache.py"',
                 xbmcgui.NOTIFICATION_INFO, 2000)
        running_dialog = xbmcgui.DialogProgressBG()
        running_dialog.create('Running "texturecache.py".')
        try:
            import importlib as imp
        except Exception:
            import imp
        import sys
        import resources.texturecache

        class StubClass(object):
            def is_set():
                return False
        class StubClass2(object):
            def __init__(self, stdout):
                self.stdout = stdout
                self.isduplicates = False
                self.duplicateslogfile = None
                self.stdlogfile = None
            def __getattribute__(self, attr):
                if attr in ('stdout', 'write', 'detach', 'isduplicates', 'duplicateslogfile', 'stdlogfile'):
                    return object.__getattribute__(self, attr)
                else:
                    return object.__getattribute__(self, 'stdout').__getattribute__(attr)
            def write(self, msg):
                if isinstance(msg, bytes):
                    try:
                        msg = msg.decode('utf-8')
                    except Exception:
                        pass
                msg = str(msg).replace('\r', '\n')
                if debugtexturecache and not self.isduplicates:
                    return self.stdlogfile.write(msg)
                elif self.isduplicates:
                    return self.duplicateslogfile.write(msg)
            def detach(self):
                return self
        temp_stdout = sys.stdout
        temp_stderr = sys.stderr
        temp_repl_stdout = StubClass2(sys.stdout)
        cleaner_log = xbmcvfs.translatePath('special://temp/database-cleaner.log')
        with xbmcvfs.File(cleaner_log) as current_log:
            cleaner_log_contents = current_log.read()
        with xbmcvfs.File(cleaner_log, 'w') as logfile:
            if cleaner_log_contents:
                logfile.write(cleaner_log_contents)
            if debugtexturecache:
                temp_repl_stdout.stdlogfile = logfile
            for tc_num, tc_option in enumerate(tc_option_list):
                try:
                    running_dialog.update(int(tc_num / len(tc_option_list) * 100), 'Running "texturecache.py %s". Please wait.' % tc_option)
                    resources.texturecache.stopped = StubClass()
                    if tc_option == 'duplicates':
                        temp_repl_stdout.duplicateslogfile = get_texturecache_duplicates_logfile()
                        temp_repl_stdout.isduplicates = True
                    else:
                        temp_repl_stdout.write('Running "texturecachepy %s"\n' % tc_option)
                    sys.stdout = temp_repl_stdout
                    sys.stderr = sys.stdout
                    resources.texturecache.main([tc_option])
                except BaseException:
                    pass
                finally:
                    sys.stdout = temp_stdout
                    sys.stderr = temp_stderr
                    if tc_option == 'duplicates':
                        try:
                            temp_repl_stdout.duplicateslogfile.close()
                        except Exception:
                            pass
                        temp_repl_stdout.isduplicates = False
                    imp.reload(resources.texturecache)

        running_dialog.close()
        xbmcgui.Dialog().notification(addonname, 'Finished running "texturecache.py',
                 xbmcgui.NOTIFICATION_INFO, 2000)
        xbmc.sleep(3000)
        del temp_stdout
        del temp_stderr
        del temp_repl_stdout

    dbglog('Script finished')
else:

    xbmcgui.Dialog().notification(addonname,
                                  'Exit - No changes made',
                                  xbmcgui.NOTIFICATION_INFO, 3000)
    dbglog('script aborted by user - no changes made')
    WINDOW.setProperty('database-cleaner-running', 'false')
    exit(1)
WINDOW.setProperty('database-cleaner-running', 'false')
