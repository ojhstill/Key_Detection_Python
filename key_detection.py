# Import external libraries.
import logging
import math
import queue
import threading

import PySimpleGUI as sg
from music21 import *
import pygame.midi as midi

# Initialise global variables.
KEY_THRESHOLD = 0.8


def midi_to_note(number):
    notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    octave = math.floor(number / 12)
    return notes[number % 12] + str(octave)


def midi_listener(midi_device, midi_stream, key_updates, degree_updates, altkey_updates):

    logging.info("Thread 'midi_listener': Starting")

    # Initialise variables.
    logging.info("Initialise variables...")

    poly_array = []
    live_array = []
    current_key = None

    logging.info("Initialisation complete.")

    # Start reading device.
    while True:

        if midi_device.poll():

            if len(midi_stream) == 0:
                current_key = None

            # Read and parse incoming MIDI messages.
            midi_event = midi_device.read(1)[0]
            data = midi_event[0]
            note_number = data[1]
            velocity = data[2]

            # Convert MIDI data to pitch.
            note_pitch = pitch.Pitch(note_number)

            # If note is an onset...
            if velocity != 0:
                # ... add note to polyphonic and live array.
                poly_array.append(note_pitch)
                live_array.append(note_pitch)

            # If note is an offset...
            elif note_pitch in live_array:
                # ... remove from live array only.
                live_array.remove(note_pitch)

            # Once all notes have been released...
            if len(live_array) == 0:
                # ... create 'Chord' class with all notes that were pressed and simplify enharmonics.
                user_input = chord.Chord(pitch.simplifyMultipleEnharmonics(poly_array, keyContext=current_key))

                # Add input to stream.
                midi_stream.append(user_input)
                # Reset polyphonic array.
                poly_array.clear()

                # Analyse stream for the current musical key.
                if len(midi_stream) > 16:
                    # Only analyse previous 16 entries in stream (4 bars of 4 beat measure).
                    analysed_key = midi_stream[len(midi_stream) - 17:len(midi_stream) - 1]\
                        .analyze('key.krumhanslschmuckler')
                else:
                    # Else analyse entire stream.
                    analysed_key = midi_stream.analyze('key.krumhanslschmuckler')

                # Check that key is above the certainty threshold.
                if analysed_key.tonalCertainty() > KEY_THRESHOLD:

                    # Check if current key needs to be updated.
                    if analysed_key != current_key:
                        # Insert new key within stream.
                        midi_stream.append(analysed_key)

                        # Update current key.
                        current_key = analysed_key
                        key_updates.put(str(current_key))
                        print("KEY UPDATED:", current_key, current_key.tonalCertainty())

                # Print the scale figure.
                if current_key is not None:
                    scale_degree = roman.romanNumeralFromChord(user_input, current_key).figure
                    degree_updates.put(str(scale_degree))
                    print("Scale Degree:", scale_degree)

                    # Find alternative keys.
                    altkey1 = str(current_key.alternateInterpretations[0]).replace('-', 'b')
                    altkey2 = str(current_key.alternateInterpretations[1]).replace('-', 'b')
                    altkey3 = str(current_key.alternateInterpretations[2]).replace('-', 'b')
                    altkey_string = altkey1 + " / " + altkey2 + " / " + altkey3
                    altkey_updates.put(altkey_string)


if __name__ == '__main__':

    # Setup.
    logging.basicConfig(format="%(asctime)s: %(message)s", level=logging.INFO, datefmt="%H:%M:%S")
    logging.info("Thread 'main': Starting")

    # Initialise variables.
    logging.info("Initialise variables...")

    s = stream.Stream()
    input_device = None

    # Queues for multithreading.
    key_queue = queue.Queue()
    degree_queue = queue.Queue()
    altkey_queue = queue.Queue()

    logging.info("Initialisation complete.")

    # Initialise user window.
    logging.info("Initialise window...")

    layout = [
        [sg.Text('Current Key: ', size=(15, 1), font=("Helvetica", 25)),
            sg.Text("?", key='-CURRENT KEY-', size=(10, 1), font=("Helvetica", 25))],
        [sg.Text('Scale Degree: ', size=(15, 1), font=("Helvetica", 25)),
            sg.Text("?", key='-SCALE DEGREE-', size=(10, 1), font=("Helvetica", 25))],
        [sg.Text('Alternative Keys: ', size=(15, 1), font=("Helvetica", 25)),
            sg.Text("?", key='-ALT KEYS-', size=(25, 1), font=("Helvetica", 25))],
        [sg.Text(key='-ERROR TEXT-', text_color='red')],
        [sg.Button('Reset'), sg.Button('View Score'), sg.Button('Plot Data'), sg.Quit()]
    ]

    window = sg.Window("Key Detection - Y3857872", layout)
    sg.theme('Dark Black 1')

    logging.info("Initialisation complete.")

    # Initialise packages.
    logging.info("Initialise packages...")
    midi.init()
    logging.info("Initialisation complete.")

    logging.info("Scanning devices...")
    if midi.get_count() > 0:

        # Scan devices for MIDI input.
        for n in range(midi.get_count()):
            device = midi.get_device_info(n)

            # Select first MIDI output device channel.
            if device[2] == 1:
                print("Scan complete - Output channel selected:", str(device[0]))
                input_device = midi.Input(n)
                break

        # Make sure input device has been selected.
        if input_device is not None:

            # Start listener thread for incoming midi messages.
            logging.info("Creating MIDI thread...")
            ml = threading.Thread(target=midi_listener, args=(input_device, s, key_queue, degree_queue, altkey_queue))
            ml.setDaemon(True)
            ml.start()
            logging.info("MIDI thread created.")

            # Start listening for user action.
            while True:
                event, values = window.read(timeout=10)

                if event in (sg.WIN_CLOSED, 'Quit'):
                    break

                elif event == 'Reset':
                    s.clear()
                    window["-CURRENT KEY-"].update('?')
                    window["-SCALE DEGREE-"].update('?')
                    window["-ALT KEYS-"].update('?')

                elif event == 'View Score':
                    s.show()

                elif event == 'Plot Data':
                    s.plot('histogram', 'pitchClass')

                elif event == '__TIMEOUT__':
                    if not key_queue.empty():
                        window["-CURRENT KEY-"].update(key_queue.get())
                    if not degree_queue.empty():
                        window["-SCALE DEGREE-"].update(degree_queue.get())
                    if not altkey_queue.empty():
                        window["-ALT KEYS-"].update(altkey_queue.get())

        else:
            logging.error("Error: No MIDI output channels found.")

    else:
        logging.error("Error: No MIDI devices found.")

    window.close()
    exit(0)
