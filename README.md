## Linux Spotify ad muter
Listens to track changes with dbus. Assumes pulseaudio, and mutes master during ads (i.e. not just spotify's stream! [1]).

License: BSD. Based on <https://muffinresearch.co.uk/linux-spotify-track-notifier-with-added-d-bus-love/>.

[1] TODO: only mute spotify stream, read pavucontrol source code to figure out how. Currently mutes pulseaudio using `amixer -D pulse sset Master {off|on}`.
