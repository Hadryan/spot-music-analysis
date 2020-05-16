from multiprocessing import Process, Queue
from src.StupidArtnet import StupidArtnet
import time
import tekore as tk 
import numpy as np 



def _load_config(filename):
    try:
        return tk.config_from_file(filename,return_refresh=True)
    except:
        print("invallid config.ini file")


def validate_credentials(filename='config.ini'):
    """
    Check the config file for valid credentials, or prompt login window to obtain token
    """

    config = _load_config(filename)
    client_id,client_secret,redirect_uri,refresh_token = config

    if refresh_token:
        token = tk.refresh_user_token(*config[:2], refresh_token)
    else:
        scope = tk.scope.every
        token = tk.prompt_for_user_token(client_id,client_secret,redirect_uri,scope)
    refresh_token = token.refresh_token
    tk.config_to_file(filename, (client_id,client_secret,redirect_uri,refresh_token))
    return token


def find_previous_section(time_stamp, start_times):
    """
    Returns the index fo the previous beat/section/....  in the list
    """
    # Kan nog versneld worden door items te poppen die al voorbij zijn, 
    # maar als je terugspoelt moeten die weer terug gehaald worden...
    return np.argmin(np.abs(np.array([i for i in start_times if i < time_stamp])-time_stamp))


def _analyse_track():
    """
    Returns a loudness treshold to define differences in sections
    Very basic for now but can become more advanced in future
    """

    global audio

    loudness = [s.loudness for s in audio.sections]
    treshold = np.mean(loudness)

    return treshold

def _section_type():
    pass


def _set_audio_data():
    global beats
    global sections
    global audio
    
    # create list of start times for fast loops
    beats = [float(beat.start) for beat in audio.beats]
    sections = [float(section.start) for section in audio.sections]
    print(f"beats {len(beats)}, sections {len(sections)}")



def beat_detection(progressed_time, treshold):
    """
    progressed_time (s) and finds next beat using find_previous_section()
    """
    global audio
    global beats
    global sections

    start = time.time()
    next_beat = find_previous_section(progressed_time,beats) + 1
    current_section = find_previous_section(progressed_time,sections)

    if audio.sections[current_section].loudness > treshold:
        section_type = "BEATS"
    else:
        section_type = "BREAKS"


    if next_beat >= len(audio.beats):
        pass

    else:
        time_to_beat = audio.beats[next_beat].start - progressed_time                   #check if time is more than bpm interval
        end = time.time()
        diff = end - start
        time.sleep(time_to_beat - diff)

        print(f"SECTION: {section_type} : {current_section}/{len(sections)} | BEAT {next_beat}/{len(beats)}", end="\r")

        # not final return just testing

        return section_type

    # return time.sleep(1)



def spotify_analysis(spotify, queue):
    """
    Main loop for the program, finds beats and sections
    and sends items to the queue 
    """

    global audio
    previous = None

    while spotify.playback():
        if spotify.playback().is_playing:
            current = spotify.playback_currently_playing() #deze wordt te vaak opgevraagd passed time moet dat voorkomen lijkt te werken

            if current.item.id != previous:
                audio = spotify.track_audio_analysis(current.item.id)

                #set the track data
                _set_audio_data()
                section_treshold = _analyse_track()

                print(f"Song:{current.item.name} - Artist(s):{[a.name for a in current.item.artists]} - Song treshold = {section_treshold}" , end='\n')
                previous = current.item.id
                
            else:
                passed_time = 0
                progress = current.progress_ms
                # print("Update real progress time")
                
                while passed_time < 2:
                    # Start timing of process
                    interval_start = time.time()

                    # feedback going to be adjusted
                    # print(f"Progress: ({progress+passed_time*1000}/{audio.track['duration']*1000}) passed time {passed_time}", end='\r')
                    
                    # Beat detections --> artnet connection
                    section_type = beat_detection(progress/1000+passed_time, section_treshold) 

                    if section_type:
                        if queue.empty():
                            queue.put(section_type)
                        else:
                            pass
                    else:
                        pass

 
                    # Time the duration and adjust progress
                    interval_end = time.time()
                    passed_time += interval_end-interval_start
            
        else:
            # If no spotify playback sleep 1s and try again
            time.sleep(1)

def _init_artnet():
    target_ip = '192.168.2.2'
    universe = 0
    packet_size = 100
    u = StupidArtnet(target_ip, universe, packet_size)
    u.clear()
    u.start()
    return u

def _fade(u):
    """Deze unit is voor tests, moet meer input krijgen ect..."""
    steps = 100  # fades steps
    duration = 2 #secondes

    fades_values = np.linspace(255,0,steps)
    inv_fade = np.flip(fades_values,0)
    interval =  duration/steps
    

    for fade,inv in zip(fades_values,inv_fade):
        u.set_rgb(1,0,int(inv),int(fade))
        u.set_rgb(7,0,int(inv),int(fade))
        u.show()
        time.sleep(interval)

    u.blackout()



def _beat(u):
    r = np.random.randint(0,255)
    g = np.random.randint(0,255)
    b = np.random.randint(0,255)

    u.clear()
    # r,g,b=255,0,0
    u.set_rgb(1,r,g,b)
    u.set_rgb(7,r,g,b)
    # time.sleep(0.2)
    # u.blackout



def artnet_control(queue):
    """
    Fetches items from queue and sends the data to artnet
    """

    #start artnet connection
    try:
        universe = _init_artnet()
    except:
        AssertionError("Could not start artnet!")

    while True:
        if queue.empty():
            time.sleep(0.1)
            pass
        else:
            print("ik krijg nu", queue.get())
            if queue.get() == "BEATS":
                _beat(universe)
                print("beaats!")
            elif queue.get() == "BREAKS":
                _fade(universe)
                print("FAdddeess")
            else:
                print('Geen idee')

    return



if __name__ == "__main__":

    # Try to initialise spotify
    try:
        token  = validate_credentials()
        spotify = tk.Spotify(token)
    except:
        AssertionError("Failed to initialise spotify")

    # setup a queue for process communication
    queue = Queue()

    # set global var where current audio data is stored
    # this is global because needs to be used in multiple processes
    audio,beats,sections = None,None,None

    # Define the 2 processes
    main_process = Process(target=spotify_analysis, args=[spotify, queue])
    helper_process = Process(target=artnet_control, args=[queue])

    # Start the processes
    main_process.start()
    helper_process.start()

        