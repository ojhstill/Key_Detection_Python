# Import external libraries.
import math
from music21 import *
import pygame.midi as midi


KEY_THRESHOLD = 0.9


def midi_to_note(number):
    notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    octave = math.floor(number / 12)
    return notes[number % 12] + str(octave)


def read_input(input_device):
    print("Ready.")
    while True:
        if input_device.poll():
            event = input_device.read(1)[0]
            data = event[0]
            # timestamp = event[1]
            parse_midi_data(data)


def parse_midi_data(data):
    note_number = data[1]
    velocity = data[2]

    # Ignore 'note off' messages.
    if velocity != 0:
        # Convert MIDI data to 'Note' class.
        note_input = note.Note(midi_to_note(note_number))

        # Add note to stream.
        s.append(note_input)
        analyse_key(s)


def analyse_key(stream_input):
    analysed_key = stream_input.analyze('key')
    if analysed_key.tonalCertainty() > KEY_THRESHOLD:
        print(analysed_key, analysed_key.tonalCertainty())


# for c in displayPart.recurse().getElementsByClass('Chord'):
#     rn = roman.romanNumeralFromChord(c, keyA)
#     c.addLyric(str(rn.figure))


if __name__ == '__main__':
    # Initialise packages.
    print("Initialise packages...")
    midi.init()
    print("Complete.")

    # Initialise variables.
    print("Initialise variables...")
    s = stream.Stream()
    print("Complete.")

    # Scan devices for MIDI input.
    print("Scanning devices...")
    if midi.get_count() > 0:
        for n in range(midi.get_count()):
            device = midi.get_device_info(n)

            # Select first input device.
            if device[2] == 1:
                print("Input device " + str(device[0]) + " selected.")
                break

        # Start reading device.
        print("Reading device...")
        read_input(midi.Input(n))

    else:
        print("No MIDI input devices found.")
