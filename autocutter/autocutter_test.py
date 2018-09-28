import essentia.standard as es
import acoustid

cp = es.Chromaprinter()

test_audio = es.MonoLoader(filename = "ep27_shortened.mp3")()
test_audio_print = acoustid.chromaprint.decode_fingerprint(cp(test_audio))[0]
