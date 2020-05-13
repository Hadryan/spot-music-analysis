from multiprocessing import Process, Queue
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


def _set_audio_data():
    global beats
    global sections
    global audio
    
    # create list of start times for fast loops
    beats = [float(beat.start) for beat in audio.beats]
    sections = [float(section.start) for section in audio.sections]
    print(f"beats {len(beats)}, sections {len(sections)}")



def beat_detection(progressed_time):
    """
    progressed_time (s) and finds next beat using find_previous_section()
    """
    global audio
    global beats


    start = time.time()
    next_beat = find_previous_section(progressed_time,beats) + 1
    time_to_beat = audio.beats[next_beat].start - progressed_time
    end = time.time()
    diff = end - start
    time.sleep(time_to_beat - diff)
    print(f"next beat {next_beat}/{len(beats)}, time to next beat = {time_to_beat}, diff {diff}", end="\r")

    # return time.sleep(1)



def spotify_analysis(spotify):
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
                _set_audio_data()
                print(f"Song:{current.item.name} - Artist(s):{[a.name for a in current.item.artists]}", end='\n')
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
                    beat_detection(progress/1000+passed_time) 
 
                    # Time the duration and adjust progress
                    interval_end = time.time()
                    passed_time += interval_end-interval_start
            
        else:
            # If no spotify playback sleep 1s and try again
            time.sleep(1)



def artnet_control():
    """
    Fetches items from queue and sends the data to artnet
    """

    print("Lampjes")
    return



if __name__ == "__main__":

    # Try to initialise spotify
    try:
        token  = validate_credentials()
        spotify = tk.Spotify(token)
    except:
        AssertionError("Failed to initialise spotify")

    # setup a queue for process communication
    queque = Queue()

    # set global var where current audio data is stored
    # this is global because needs to be used in multiple processes
    audio,beats,sections = None,None,None

    # Define the 2 processes
    main_process = Process(target=spotify_analysis, args=[spotify])
    helper_process = Process(target=artnet_control)

    # Start the processes
    main_process.start()
    helper_process.start()

        