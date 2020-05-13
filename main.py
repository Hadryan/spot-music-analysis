import tekore as tk 
import numpy as np 
from multiprocessing import Process, Queue


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







def spotify_analysis(spotify_object):
    """
    Main loop for the program, finds beats and sections
    and sends items to the queue 
    """

    print("Starting Main loop")

    return




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

    # setup a queue 
    queque = Queue()

    # Define the 2 processes
    main_process = Process(target=spotify_analysis, args=[spotify])
    helper_process = Process(target=artnet_control)

    # Start the processes
    main_process.start()
    helper_process.start()

        