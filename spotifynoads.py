#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Spotify ad muter, assumes you use pulseaudio.

DBus listening code based on:
<https://muffinresearch.co.uk/linux-spotify-track-notifier-with-added-d-bus-love/>
"""

import os
import dbus
import gobject
from dbus.mainloop.glib import DBusGMainLoop
from dbus.exceptions import DBusException


class SpotifyAdMuter(object):

    def __init__(self):
        """initialise."""
        bus_loop = DBusGMainLoop(set_as_default=True)
        self.bus = dbus.SessionBus(mainloop=bus_loop)
        loop = gobject.MainLoop()
        self.notify_id = None
        self.props_changed_listener()
        try: 
            self.props_changed_listener()
        except DBusException, e:
            if not ("org.mpris.MediaPlayer2.spotify "
                    "was not provided") in e.get_dbus_message():
                raise
        self.session_bus = self.bus.get_object("org.freedesktop.DBus", 
                                 "/org/freedesktop/DBus")
        self.session_bus.connect_to_signal("NameOwnerChanged", 
                                        self.handle_name_owner_changed,
                                        arg0="org.mpris.MediaPlayer2.spotify")
        loop.run()

    def props_changed_listener(self):
        """Hook up callback to PropertiesChanged event."""
        self.spotify = self.bus.get_object("org.mpris.MediaPlayer2.spotify", 
                                           "/org/mpris/MediaPlayer2")
        self.spotify.connect_to_signal("PropertiesChanged", 
                                        self.handle_properties_changed)

    def handle_name_owner_changed(self, name, older_owner, new_owner):
        """Introspect the NameOwnerChanged signal to work out if spotify has started."""
        if name == "org.mpris.MediaPlayer2.spotify":
            if new_owner:
                # spotify has been launched - hook it up.
                self.props_changed_listener()
            else:
                self.spotify = None

    def handle_properties_changed(self, interface, changed_props, invalidated_props):
        """Handle track changes."""
        metadata = changed_props.get("Metadata", {})
        if metadata:
            #title = unicode(metadata.get("xesam:title"))
            #album = unicode(metadata.get("xesam:album"))
            #artist = unicode(', '.join(metadata.get("xesam:artist")))
            #is_ad = metadata.get("mpris:trackid").startswith("spotify:ad:")
            #print(u"title: {title}, artist: {artist}, is_ad: {is_ad}".format(
            #    title=title, album=album, artist=artist, is_ad=is_ad).encode('utf8'))
            is_ad = metadata.get("mpris:trackid").startswith("spotify:ad:")
            if is_ad:
                print('Ad starting, muting.')
                os.system('amixer -D pulse sset Master off')
            elif self.prev_is_ad:
                print('Previously was ad, now isnt: unmuting.')
                os.system('amixer -D pulse sset Master on')
            self.prev_is_ad = is_ad

if __name__ == "__main__":
    SpotifyAdMuter()

