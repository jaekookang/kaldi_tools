# make\_prep\_files

* **make\_prep\_data.sh** generates following files
  * text: <utterance ID> <text>
  * textraw: <text>
  * wav.scp: <utterance ID> <wav dir>
  * utt2spk: <utterance ID> <speaker ID>
	* NOTE: 
	  * <utterance ID> is set to be a file id
		e.g. spkr\_01.wav --> spkr\_01
	  * <speaker ID> is set as SPEAKER (edit if necessary)
	  
* Prepare following files
  * .wav: wav file
	e.g. spkr\_01.wav
  * .txt: transcription file per .wav
	e.g. This is a test recording
	
* Run make\_prep\_data.sh
  ```bash
  $ . ./make_prep_data.sh data_in data_out
  ```
	  
