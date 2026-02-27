import json
import os

def generate_interactive_song_board(song_embeddings, song_files):
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>Interactive Song Board</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://cdn.jsdelivr.net/npm/d3@7"></script>
        <style>
            body { font-family: 'Inter', sans-serif; }
            #song-board { width: 100%; height: 80vh; border: 1px solid #e5e7eb; border-radius: 0.5rem; background: #f9fafb; }
            .song-circle { cursor: pointer; border-radius: 50%; opacity: 0.7; transition: opacity 0.2s ease, stroke-width 0.2s ease; stroke: transparent; stroke-width: 0; }
            .song-circle:hover { opacity: 1; stroke: #60a5fa; stroke-width: 2px; }
            .song-circle.playing { stroke: #f59e0b; stroke-width: 4px; opacity: 1; }
            #tooltip { position: absolute; background: white; padding: 0.5rem; border: 1px solid #e5e7eb; border-radius: 0.25rem; font-size: 0.875rem; box-shadow: 0 1px 3px rgba(0,0,0,0.1); pointer-events: none; opacity: 0; transition: opacity 0.2s ease; }

            /* Styles for the seek bar thumb */
            #seek-bar::-webkit-slider-thumb {
                -webkit-appearance: none; /* Remove default webkit thumb appearance */
                appearance: none;
                width: 1rem; /* 16px */
                height: 1rem; /* 16px */
                background-color: #2563eb; /* Tailwind blue-600 for visibility */
                border-radius: 9999px; /* Equivalent to rounded-full */
                cursor: pointer;
                margin-top: -0.25rem; /* Vertically center thumb on track: (track_height (0.5rem) - thumb_height (1rem)) / 2 */
            }

            #seek-bar::-moz-range-thumb {
                width: 1rem; /* 16px */
                height: 1rem; /* 16px */
                background-color: #2563eb; /* Tailwind blue-600 */
                border-radius: 9999px; /* Equivalent to rounded-full */
                cursor: pointer;
                border: none; /* Firefox might add a default border */
            }

            /* Optional: Explicit track styling (though Tailwind classes on input should mostly cover it) */
            /*
            #seek-bar::-webkit-slider-runnable-track {
                height: 0.5rem; // Corresponds to h-2
                background-color: #d1d5db; // Corresponds to bg-gray-300
                border-radius: 0.375rem; // Corresponds to rounded-lg
            }
            #seek-bar::-moz-range-track {
                height: 0.5rem;
                background-color: #d1d5db;
                border-radius: 0.375rem;
                border: none;
            }
            */
        </style>
    </head>
    <body class="bg-gray-100 p-6">
        <div class="container mx-auto">
            <h1 class="text-2xl font-semibold text-gray-800 mb-4">Interactive Song Board</h1>
            <div id="song-board" class="relative mb-6"></div>
            
            <div id="player-controls" class="flex items-center justify-center space-x-4 w-full max-w-3xl mx-auto mb-2">
                <!-- Circular Play/Pause button -->
                <button id="toggle-play" 
                    class="w-10 h-10 bg-black hover:bg-gray-800 text-white rounded-full flex items-center justify-center focus:outline-none">
                <svg id="play-icon" xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M8 5v14l11-7z" />
                </svg>
                <svg id="pause-icon" xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 hidden" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M6 19h4V5H6zm8-14v14h4V5h-4z" />
                </svg>
                </button>

                <!-- Seek bar with current and total time -->
                <div class="flex-1 flex items-center space-x-2">
                    <span id="current-time" class="text-sm text-gray-700 w-10 text-right">0:00</span>
                    <input id="seek-bar" type="range" min="0" value="0" step="0.1" 
                        class="w-full h-2 bg-gray-300 rounded-lg appearance-none cursor-pointer">
                    <span id="total-duration" class="text-sm text-gray-700 w-10">0:00</span>
                </div>
            </div>
            <div class="flex justify-center space-x-4 mb-4">
                <button id="play-all" class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">Play All</button>
                <button id="pause-all" class="bg-gray-300 hover:bg-gray-400 text-gray-800 font-bold py-2 px-4 rounded">Pause All</button>
            </div>
        </div>

        <script>
            function formatTime(seconds) {
                const mins = Math.floor(seconds / 60);
                const secs = Math.floor(seconds % 60);
                return `${mins}:${secs.toString().padStart(2, '0')}`;
            }

            const seekBar = document.getElementById("seek-bar");
            const togglePlayButton = document.getElementById("toggle-play");
            const currentTimeLabel = document.getElementById("current-time");
            const totalDurationLabel = document.getElementById("total-duration");
            
            const playIcon = document.getElementById("play-icon");
            const pauseIcon = document.getElementById("pause-icon");

            togglePlayButton.addEventListener("click", () => {
                if (playingAudio && playingAudio.audio) {
                    if (playingAudio.audio.paused) {
                        playingAudio.audio.play();
                        playIcon.classList.add("hidden");
                        pauseIcon.classList.remove("hidden");
                    } else {
                        playingAudio.audio.pause();
                        playIcon.classList.remove("hidden");
                        pauseIcon.classList.add("hidden");
                    }
                }
            });

            const songBoard = d3.select("#song-board");
            const tooltip = d3.select("body").append("div")
                .attr("id", "tooltip")
                .style("opacity", 0);

            const audioElements = {};
            let playingAudio = null;

            // Ensure song_embeddings and song_files are correctly passed as JSON strings
            const songData = JSON.parse(`""" + json.dumps(json.dumps(song_embeddings))[1:-1] + """`);
            const songFiles = JSON.parse(`""" + json.dumps(json.dumps(song_files))[1:-1] + """`);

            const songLinks = {};
            // Assuming song_files is an array of filenames like ["song1.mp3", "song2.mp3"]
            // And songData is an array of objects like [{song_name: "song1.mp3", x: ..., y:...}, ...]
            // The song_name in songData should match the filenames in song_files.
            songFiles.forEach(f => {
                // Create a mapping from the song name (which should be the file name) to its path
                songLinks[f] = "songs/" + f;
            });


            function createSongBoard() {
                const width = songBoard.node().clientWidth;
                const height = songBoard.node().clientHeight;
                const padding = 40;

                const svg = songBoard.append("svg").attr("width", width).attr("height", height);
                const container = svg.append("g");

                const xExtent = d3.extent(songData, d => d.x);
                const yExtent = d3.extent(songData, d => d.y);

                const xScale = d3.scaleLinear().domain(xExtent).range([padding, width - padding]);
                const yScale = d3.scaleLinear().domain(yExtent).range([padding, height - padding]);

                const circles = container.selectAll("circle")
                    .data(songData).enter().append("circle")
                    .attr("class", "song-circle")
                    .attr("r", 10)
                    .attr("fill", () => `hsl(${Math.random() * 360}, 70%, 50%)`)
                    .on("mouseover", (event, d) => {
                        tooltip.html(d.song_name) // song_name should be the property holding the display name / file name
                            .style("left", (event.pageX + 10) + "px")
                            .style("top", (event.pageY - 28) + "px")
                            .style("opacity", 1);
                    })
                    .on("mouseout", () => tooltip.style("opacity", 0))
                    .on("click", function (event, d) {
                        const url = songLinks[d.song_name]; // Use d.song_name to look up in songLinks
                        if (url) playSong(d.song_name, url, this);
                        else console.error("Song URL not found for:", d.song_name, "Available links:", songLinks);
                    });

                const labels = container.selectAll("text")
                    .data(songData).enter().append("text")
                    .text(d => d.song_name) // Make sure d.song_name is what you want to display
                    .attr("font-size", "10px")
                    .attr("fill", "#444");

                function updatePositions(xS, yS) {
                    circles.attr("cx", d => xS(d.x)).attr("cy", d => yS(d.y));
                    labels.attr("x", d => xS(d.x) + 12).attr("y", d => yS(d.y) + 4);
                }

                updatePositions(xScale, yScale);

                svg.call(d3.zoom().scaleExtent([0.5, 10]).on("zoom", e => {
                    const newX = e.transform.rescaleX(xScale);
                    const newY = e.transform.rescaleY(yScale);
                    updatePositions(newX, newY);
                }));
            }

            function playSong(songName, songUrl, circleElement) {
                if (playingAudio && playingAudio.name !== songName) {
                    playingAudio.audio.pause();
                    d3.select(playingAudio.circle).classed("playing", false);
                    // No need to reset playingAudio to null here yet,
                    // it will be overwritten or handled if a new song starts
                }

                if (!audioElements[songName]) {
                    const audio = new Audio(songUrl);

                    audio.addEventListener('loadedmetadata', () => {
                        if (!isNaN(audio.duration)) {
                           totalDurationLabel.textContent = formatTime(audio.duration);
                           seekBar.max = audio.duration;
                        }
                    });

                    audio.addEventListener("timeupdate", () => {
                        if (!isNaN(audio.duration)) { // Check duration is a number
                            seekBar.value = audio.currentTime;
                            currentTimeLabel.textContent = formatTime(audio.currentTime);
                            // Total duration is set on loadedmetadata, but can be reaffirmed here if needed
                            if (totalDurationLabel.textContent === "0:00" || totalDurationLabel.textContent === "NaN:NaN") {
                                totalDurationLabel.textContent = formatTime(audio.duration);
                                seekBar.max = audio.duration;
                            }
                        }
                    });

                    audio.addEventListener("ended", () => {
                        d3.select(circleElement).classed("playing", false);
                        if (playingAudio && playingAudio.name === songName) {
                            playingAudio = null; // Clear only if the ended song is the one currently marked as playing
                        }
                        playIcon.classList.remove("hidden");
                        pauseIcon.classList.add("hidden");

                        // Don't reset seekbar and labels here if you plan to implement a playlist/queue
                        // For now, resetting is fine for single play.
                        // seekBar.value = 0;
                        // currentTimeLabel.textContent = "0:00";
                    });

                    audio.addEventListener("play", () => {
                        d3.select(circleElement).classed("playing", true);
                         if (!isNaN(audio.duration)) { // Ensure duration is available
                            totalDurationLabel.textContent = formatTime(audio.duration);
                            seekBar.max = audio.duration;
                        }
                    });

                    audio.addEventListener("pause", () => {
                        d3.select(circleElement).classed("playing", false);
                    });


                    audioElements[songName] = { audio, name: songName, circle: circleElement };
                    playingAudio = audioElements[songName]; // Set current playing audio

                    audio.play()
                        .then(() => {
                            playIcon.classList.add("hidden");
                            pauseIcon.classList.remove("hidden");
                        })
                        .catch(e => console.error("Playback failed for " + songName + ":", e));

                } else { // Audio element already exists
                    const existingAudioData = audioElements[songName];
                    const a = existingAudioData.audio;

                    if (a.paused) {
                        // If this song was paused, and it's different from the one that was globally "playingAudio"
                        // (e.g. another song was clicked and paused), make sure to stop the other one.
                        if (playingAudio && playingAudio.name !== songName) {
                             playingAudio.audio.pause();
                             d3.select(playingAudio.circle).classed("playing", false);
                        }
                        a.play().catch(e => console.error("Playback failed for "+songName+":", e));
                        playingAudio = existingAudioData; // Set this as the current playing audio
                    } else {
                        a.pause();
                        // If this song (which was playing) is paused, clear it from being the "playingAudio"
                        if (playingAudio && playingAudio.name === songName) {
                            playingAudio = null;
                        }
                    }
                }
            }

            seekBar.addEventListener("input", () => {
                if (playingAudio && playingAudio.audio && !isNaN(playingAudio.audio.duration)) {
                    playingAudio.audio.currentTime = seekBar.value;
                }
            });

            document.getElementById("play-all").addEventListener("click", () => {
                // Basic play all - plays one after another, interrupting previous.
                // A more robust queue system would be needed for sequential play.
                let currentSongIndex = 0;
                const songsToPlay = Object.keys(songLinks);

                function playNextSong() {
                    if (currentSongIndex < songsToPlay.length) {
                        const songName = songsToPlay[currentSongIndex];
                        const songUrl = songLinks[songName];
                        const circleElement = d3.selectAll(".song-circle").filter(d => d.song_name === songName).node();

                        if (circleElement) {
                            playSong(songName, songUrl, circleElement);
                            // Listen for 'ended' to play the next song
                            if (audioElements[songName] && audioElements[songName].audio) {
                                const currentAudio = audioElements[songName].audio;
                                const onEndedListener = () => {
                                    currentAudio.removeEventListener('ended', onEndedListener); // Clean up listener
                                    currentSongIndex++;
                                    playNextSong();
                                };
                                currentAudio.addEventListener('ended', onEndedListener);
                            } else { // If song couldn't be set up, try next
                                currentSongIndex++;
                                playNextSong();
                            }
                        } else { // If circle element not found, skip to next
                             currentSongIndex++;
                             playNextSong();
                        }
                    }
                }
                playNextSong();
            });

            document.getElementById("pause-all").addEventListener("click", () => {
                if (playingAudio && playingAudio.audio) {
                    playingAudio.audio.pause();
                    // d3.select(playingAudio.circle).classed("playing", false); // Pause event listener should handle this
                    // playingAudio = null; // Let pause event listener handle this if needed
                }
                // To pause all audio elements regardless of 'playingAudio' state:
                Object.values(audioElements).forEach(data => {
                    if (data.audio && !data.audio.paused) {
                        data.audio.pause();
                    }
                });
            });

            // Defensive check for songData
            if (songData && songData.length > 0) {
                createSongBoard();
            } else {
                console.error("Song data is empty or not loaded correctly. Board not created.");
                songBoard.html("<p class='text-red-500 p-4'>Error: No song data found to display.</p>");
            }

        </script>
    </body>
    </html>
    """
    return html_content

if __name__ == "__main__":
    input_json_path = 'song_embeddings.json' # Make sure this file exists and is correct

    try:
        with open(input_json_path, 'r') as f:
            song_embeddings_data = json.load(f)
        # Ensure song_embeddings_data is a list of objects as expected by D3
        if not isinstance(song_embeddings_data, list):
            print(f"Error: {input_json_path} should contain a JSON list of song objects.")
            # Provide a default empty list or sample structure if needed for testing
            song_embeddings_data = []
            # Example: song_embeddings_data = [{"song_name": "example.mp3", "x": 0.5, "y": 0.5}]
        print(f"Loaded embeddings from {input_json_path}")
    except FileNotFoundError:
        print(f"Error: Embeddings file '{input_json_path}' not found. Using empty data.")
        song_embeddings_data = []
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{input_json_path}'. Using empty data.")
        song_embeddings_data = []
    except Exception as e:
        print(f"Failed to load embeddings: {e}. Using empty data.")
        song_embeddings_data = []


    song_files_list = []
    songs_directory = "songs" # Make sure this directory exists
    if os.path.exists(songs_directory) and os.path.isdir(songs_directory):
        for root, _, files in os.walk(songs_directory):
            for file in files:
                if file.endswith((".mp3", ".wav", ".ogg")):
                    song_files_list.append(file)
        if not song_files_list:
            print(f"No audio files found in '{songs_directory}' directory.")
            # song_files_list.append("example.mp3") # For testing if dir is empty
    else:
        print(f"Warning: '{songs_directory}' directory not found. No song files will be loaded.")
        # Create a dummy song_files_list if song_embeddings_data has items, for consistency
        # if song_embeddings_data:
        #    song_files_list = [item['song_name'] for item in song_embeddings_data if 'song_name' in item]


    # Generate HTML using the loaded (or default empty) data
    html = generate_interactive_song_board(song_embeddings_data, song_files_list)

    output_html_path = "interactive_song_board.html"
    try:
        with open(output_html_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"Generated {output_html_path}")
    except Exception as e:
        print(f"Error writing HTML file: {e}")