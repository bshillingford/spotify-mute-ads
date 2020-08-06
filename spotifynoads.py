#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Spotify ad muter, assumes you use pulseaudio.

DBus listening code based on:
<https://muffinresearch.co.uk/linux-spotify-track-notifier-with-added-d-bus-love/>
"""


# requirements: PyGObject dbus-python
import argparse
import os
import dbus
from gi.repository import GLib
from dbus.mainloop.glib import DBusGMainLoop
from dbus.exceptions import DBusException


class PlayerAdMuter(object):
    
    def __init__(self):
        self.prev_is_ad = None
        bus_loop = DBusGMainLoop(set_as_default=True)
        self.bus = dbus.SessionBus(mainloop=bus_loop)
        loop = GLib.MainLoop()
        self.notify_id = None
        try: 
            self.props_changed_listener()
        except DBusException as e:
            if not (self.player_name + " was not provided") in e.get_dbus_message():
                raise
        self.session_bus = self.bus.get_object("org.freedesktop.DBus", 
                                 "/org/freedesktop/DBus")
        self.session_bus.connect_to_signal("NameOwnerChanged", 
                                        self.handle_name_owner_changed,
                                        arg0=self.player_name)
        loop.run()
        
    def props_changed_listener(self):
        """Hook up callback to PropertiesChanged event."""
        self.player_bus = self.bus.get_object(self.player_name, 
                                           "/org/mpris/MediaPlayer2")
        self.player_bus.connect_to_signal("PropertiesChanged", 
                                        self.handle_properties_changed)

    def handle_name_owner_changed(self, name, older_owner, new_owner):
        """Introspect the NameOwnerChanged signal to work out if spotify has started."""
        if name == self.player_name:
            if new_owner:
                # spotify has been launched - hook it up.
                self.props_changed_listener()
            else:
                self.player_bus = None

    def handle_properties_changed(self, interface, changed_props, invalidated_props):
        """Handle track changes."""
        metadata = changed_props.get("Metadata", {})
        if metadata:
            self.detect_and_handle_ads(metadata)
        
    def detect_and_handle_ads(self):
        pass
    
    def mute(self):
        print('Mute!')
        os.system('amixer -q -D pulse sset Master off')
    
    def unmute(self):
        print('Unmute!')
        os.system('amixer -q -D pulse sset Master on')


class SpotifyAdMuter(PlayerAdMuter):

    def __init__(self):
        """initialise."""
        self.player_name = "org.mpris.MediaPlayer2.spotify"
        super(SpotifyAdMuter, self).__init__()

    def detect_and_handle_ads(self, metadata):
        #title = unicode(metadata.get("xesam:title"))
        #album = unicode(metadata.get("xesam:album"))
        #artist = unicode(', '.join(metadata.get("xesam:artist")))
        #is_ad = metadata.get("mpris:trackid").startswith("spotify:ad:")
        #print(u"title: {title}, artist: {artist}, is_ad: {is_ad}".format(
        #    title=title, album=album, artist=artist, is_ad=is_ad).encode('utf8'))
        is_ad = metadata.get("mpris:trackid").startswith("spotify:ad:")
        if is_ad:
            print('Ad starting, muting.')
            self.mute()
        elif self.prev_is_ad:
            print('Previously was ad, now isnt: unmuting.')
            self.unmute()
        self.prev_is_ad = is_ad


class YoutubeMusicAdMuter(PlayerAdMuter):
    # you can add your language from the value "video_after_ad_mulitline" on the file "strings.xml" on the Youtube.apk app, for example: 
    # https://github.com/ingbrzy/Android-9.0-Pie-XMLs/blob/master/YouTube.apk/res/values-si/strings.xml
    lst_lang_ads = [
        "Video sal ná advertensie speel", #af
        "ቪዲዮው ከማስታወቂያው በኋላ ይጫወታል", #am
        "Відэа будзе прайгравацца праз пасля рэкламы", #be
        "বিজ্ঞাপনের পরে ভিডিও প্লে হবে", #bn
        "Video will play after ad", #en
        "El vídeo se reproducirá después del anuncio", #es
        "Videozapis će se reproducirati nakon oglasa", #hr
        "Vídeó spilast eftir auglýsingu", #is
        "Il video verrà riprodotto dopo l'annuncio", #it
        "ვიდეო დაუკრავს რეკლამის შემდეგ", #ka
        "ວິດີໂອຈະຫຼິ້ນຫຼັງຈາກໂຄສະນາ", #lo
        "Video begint na advertentie", #nl
        "Воспроизведение начнется после рекламы", #ru
        "වීඩියෝව දැන්වීමෙන් පසුව වාදනය වේ", #si
        "Ividiyo izodlala ngemva kwesikhangiso", #zu
    ]

    def __init__(self):
        """initialise."""
        self.player_name = "org.mpris.MediaPlayer2.youtubemusic"
        super(YoutubeMusicAdMuter, self).__init__()


    def detect_and_handle_ads(self, metadata):
        is_ad = metadata.get('xesam:artist')[0] in self.lst_lang_ads
        
        if is_ad:
            print('Ad starting, muting.')
            self.mute()
        elif self.prev_is_ad:
            print('Previously was ad, now isnt: unmuting.')
            self.unmute()
            
        self.prev_is_ad = is_ad

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--player', dest='player', choices=['spotify', 'youtubemusic'])
    args = parser.parse_args()
    
    if args.player == 'youtubemusic':
        YoutubeMusicAdMuter()
    else:
        SpotifyAdMuter()
    

if __name__ == "__main__":
    main()
