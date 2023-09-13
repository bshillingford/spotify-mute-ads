#!/usr/bin/env python
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
from subprocess import check_output, Popen, DEVNULL
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
    
    def parse_sink_inputs(self, sinks):
        detected_sinks = sinks.split("    index: ")
        app_sinks = []
        for sink in detected_sinks:
            index, pid, binary = None, None, None
            # index
            parts = sink.split('\n')
            try:
                index = int(parts[0])
            except:
                continue
            for part in parts:
                # process id
                if 'application.process.id = ' in part:
                    pid = int(part.split('application.process.id = ')[1].split('"')[1])
                # process binary
                elif 'application.process.binary = ' in part:
                    binary = part.split('application.process.binary = ')[1].split('"')[1]
                # sink latency
                elif 'current latency: ' in part:
                    latency = float(part.split('current latency: ')[1].split(' ms')[0])
                else:
                    continue
            if binary == self.app_name:
                app_sinks.append({'index': index, 'latency': latency, 'pid': pid, 'binary': binary})
        return app_sinks

    def detect_app_sink(self):
        all_sinks = check_output(['pacmd', 'list-sink-inputs'], universal_newlines=True)
        self.sinks = self.parse_sink_inputs(all_sinks)
    
    def wait_latency(self):
        waiting_sinks = []
        for s in self.sinks:
            print(f'[spotifynoads.py] Adding sink {s["index"]} to wait list because of latency {s["latency"]} ms.')
            waiting_sinks.append((s['index'], Popen(['sleep', str(s['latency']/1000)]))) # Warning: sleep accepts only seconds, not milliseconds
        return waiting_sinks
    
    def toggle_mute_after_waiting(self, waiting_sinks, mute):
        action = "Mute" if mute else "Unmute"
        while waiting_sinks:
            for sinkpair in waiting_sinks:
                retcode = sinkpair[1].poll()
                if retcode is not None: # Sleep finished, mute/unmute sink
                    waiting_sinks.remove(sinkpair)
                    print(f'[spotifynoads.py] {action} {self.app_name} sink {sinkpair[0]}.')
                    Popen(['pacmd', 'set-sink-input-mute', str(sinkpair[0]), str(mute)], stdout=DEVNULL, stderr=DEVNULL)

    def mute(self):
        if self.sinks:
            waiting_sinks = self.wait_latency()
            self.toggle_mute_after_waiting(waiting_sinks, 1)
        else:
            print(f'[spotifynoads.py] Mute master.')
            os.system('amixer -q -D pulse sset Master off')
    
    def unmute(self):
        if self.sinks:
            waiting_sinks = self.wait_latency()
            self.toggle_mute_after_waiting(waiting_sinks, 0)
        else:
            print(f'[spotifynoads.py] Unmute master.')
            os.system('amixer -q -D pulse sset Master on')


class SpotifyAdMuter(PlayerAdMuter):

    def __init__(self):
        """initialise."""
        self.player_name = "org.mpris.MediaPlayer2.spotify"
        self.app_name = "spotify"
        super(SpotifyAdMuter, self).__init__()

    def detect_and_handle_ads(self, metadata):
        # Detect sink. This is nessecary at every track change, because sometimes spotify adds new sinks for ads and deletes them afterwards.
        self.detect_app_sink()
        title = metadata.get("xesam:title")
        album = metadata.get("xesam:album")
        artist = ', '.join(metadata.get("xesam:artist"))
        trackid = metadata.get("mpris:trackid")
        is_ad = trackid.startswith("spotify:ad:") or trackid.startswith("/com/spotify/ad/")
        print("[{app_name}] Playing new track.\n    trackid: {trackid}\n    title: {title}\n    artist: {artist}\n    album: {album}\n    is_ad: {is_ad}".format(
            app_name=self.app_name, trackid=trackid, title=title, album=album, artist=artist, is_ad=is_ad))
        if is_ad:
            print('[spotifynoads.py] Ad starting, muting.')
            self.mute()
        elif self.prev_is_ad:
            print('[spotifynoads.py] Previously was ad, now isnt: unmuting.')
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
        self.app_name = "youtubemusic"
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